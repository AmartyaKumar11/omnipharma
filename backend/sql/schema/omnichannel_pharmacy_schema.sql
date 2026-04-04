-- =============================================================================
-- Omnichannel Pharmacy Operations Platform — PostgreSQL DDL (production-oriented)
-- =============================================================================
-- Design notes (critical):
-- 1) UUID PKs everywhere for safe merges, replication, and future service splits.
-- 2) Batch + expiry live on `batches`; stock is always per (store, batch) in `inventory`.
--    `inventory.product_id` is denormalized for fast filtering; a trigger keeps it
--    aligned with `batches.product_id` (avoids silent drift).
-- 3) `inventory_logs` append-only style audit for stock movements (regulated workflows).
-- 4) `order_items.batch_id` preserves dispensary traceability (which batch was sold).
-- 5) Cascades: prefer RESTRICT on master data when facts exist; use SET NULL on
--    audit actor FKs so deleting a user does not delete immutable logs.
-- 6) `daily_sales_summary` is idempotent per (store_id, date) for rollup jobs / AI features.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- Extensions
-- -----------------------------------------------------------------------------
-- gen_random_uuid() is built into PostgreSQL 13+ (no extension required).

-- -----------------------------------------------------------------------------
-- ENUM types
-- -----------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM (
  'ADMIN',
  'BRANCH_MANAGER',
  'INVENTORY_CONTROLLER',
  'STAFF'
);

CREATE TYPE inventory_change_type AS ENUM (
  'ADD',
  'REMOVE',
  'ADJUST'
);

CREATE TYPE order_type AS ENUM (
  'OTC',
  'PRESCRIPTION'
);

CREATE TYPE order_status AS ENUM (
  'COMPLETED',
  'CANCELLED'
);

CREATE TYPE payment_method AS ENUM (
  'CASH',
  'CARD',
  'UPI'
);

CREATE TYPE alert_type AS ENUM (
  'LOW_STOCK',
  'EXPIRY'
);

CREATE TYPE alert_severity AS ENUM (
  'LOW',
  'MEDIUM',
  'HIGH'
);

CREATE TYPE inventory_log_source_type AS ENUM (
  'SALE',
  'RESTOCK',
  'TRANSFER',
  'ADJUSTMENT'
);

CREATE TYPE stock_transfer_status AS ENUM (
  'PENDING',
  'COMPLETED',
  'CANCELLED'
);

CREATE TYPE prescription_status AS ENUM (
  'UPLOADED',
  'VERIFIED',
  'REJECTED'
);

-- -----------------------------------------------------------------------------
-- Reusable trigger: maintain updated_at
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$;

-- -----------------------------------------------------------------------------
-- MODULE 1 — Auth & users / stores / mapping
-- -----------------------------------------------------------------------------

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT,
  role user_role NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT users_email_lowercase CHECK (email = LOWER(email)),
  -- DB-level sanity only; app layer should still validate RFC-like emails.
  CONSTRAINT users_email_reasonable CHECK (char_length(email) <= 320 AND position('@'::text IN email) > 1)
);

CREATE UNIQUE INDEX uq_users_email ON users (email);

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

CREATE TABLE stores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  location TEXT,
  contact_number TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT stores_name_not_blank CHECK (LENGTH(TRIM(name)) > 0)
);

CREATE TRIGGER stores_set_updated_at
BEFORE UPDATE ON stores
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

CREATE TABLE user_store_mapping (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  store_id UUID NOT NULL REFERENCES stores (id) ON DELETE CASCADE,
  assigned_role user_role,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_user_store UNIQUE (user_id, store_id)
);

CREATE INDEX idx_user_store_mapping_store_id ON user_store_mapping (store_id);

CREATE TRIGGER user_store_mapping_set_updated_at
BEFORE UPDATE ON user_store_mapping
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

-- -----------------------------------------------------------------------------
-- MODULE 2 — Products, batches, inventory, audit logs
-- -----------------------------------------------------------------------------

CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  generic_name TEXT,
  category TEXT,
  manufacturer TEXT,
  description TEXT,
  is_prescription_required BOOLEAN NOT NULL DEFAULT FALSE,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT products_name_not_blank CHECK (LENGTH(TRIM(name)) > 0)
);

CREATE TRIGGER products_set_updated_at
BEFORE UPDATE ON products
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

CREATE TABLE batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products (id) ON DELETE RESTRICT,
  batch_number TEXT NOT NULL,
  expiry_date DATE NOT NULL,
  manufacture_date DATE,
  purchase_price NUMERIC(14, 4),
  selling_price NUMERIC(14, 4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_product_batch_number UNIQUE (product_id, batch_number),
  CONSTRAINT batches_expiry_after_manufacture CHECK (
    manufacture_date IS NULL OR expiry_date >= manufacture_date
  ),
  CONSTRAINT batches_prices_non_negative CHECK (
    (purchase_price IS NULL OR purchase_price >= 0)
    AND (selling_price IS NULL OR selling_price >= 0)
  )
);

CREATE INDEX idx_batches_product_id ON batches (product_id);
CREATE INDEX idx_batches_expiry_date ON batches (expiry_date);

CREATE TRIGGER batches_set_updated_at
BEFORE UPDATE ON batches
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

CREATE TABLE inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id UUID NOT NULL REFERENCES stores (id) ON DELETE RESTRICT,
  product_id UUID NOT NULL REFERENCES products (id) ON DELETE RESTRICT,
  batch_id UUID NOT NULL REFERENCES batches (id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL,
  reserved_quantity INTEGER NOT NULL DEFAULT 0,
  reorder_threshold INTEGER,
  last_restocked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_inventory_store_batch UNIQUE (store_id, batch_id),
  CONSTRAINT inventory_quantity_non_negative CHECK (quantity >= 0),
  CONSTRAINT inventory_reserved_non_negative CHECK (reserved_quantity >= 0),
  CONSTRAINT inventory_reserved_lte_on_hand CHECK (reserved_quantity <= quantity),
  CONSTRAINT inventory_reorder_sensible CHECK (reorder_threshold IS NULL OR reorder_threshold >= 0)
);

CREATE INDEX idx_inventory_store_id ON inventory (store_id);
CREATE INDEX idx_inventory_product_id ON inventory (product_id);
CREATE INDEX idx_inventory_batch_id ON inventory (batch_id);

-- Keep denormalized product_id aligned with batches.product_id (prevents cross-product joins).
CREATE OR REPLACE FUNCTION trg_inventory_sync_product_from_batch()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_pid UUID;
BEGIN
  SELECT b.product_id INTO v_pid FROM batches b WHERE b.id = NEW.batch_id;
  IF v_pid IS NULL THEN
    RAISE EXCEPTION 'batch % not found', NEW.batch_id;
  END IF;
  IF NEW.product_id IS DISTINCT FROM v_pid THEN
    NEW.product_id := v_pid;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER inventory_sync_product_from_batch
BEFORE INSERT OR UPDATE OF batch_id, product_id ON inventory
FOR EACH ROW EXECUTE PROCEDURE trg_inventory_sync_product_from_batch();

CREATE TRIGGER inventory_set_updated_at
BEFORE UPDATE ON inventory
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

CREATE TABLE inventory_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  inventory_id UUID NOT NULL REFERENCES inventory (id) ON DELETE RESTRICT,
  change_type inventory_change_type NOT NULL,
  source_type inventory_log_source_type NOT NULL DEFAULT 'ADJUSTMENT',
  reference_id UUID,
  quantity_changed INTEGER NOT NULL,
  reason TEXT,
  notes TEXT,
  performed_by UUID REFERENCES users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT inventory_logs_quantity_changed_not_zero CHECK (quantity_changed <> 0)
);

CREATE INDEX idx_inventory_logs_inventory_id ON inventory_logs (inventory_id);
CREATE INDEX idx_inventory_logs_performed_by ON inventory_logs (performed_by);
CREATE INDEX idx_inventory_logs_created_at ON inventory_logs (created_at);
CREATE INDEX idx_inventory_logs_source_reference ON inventory_logs (source_type, reference_id);

CREATE TRIGGER inventory_logs_set_updated_at
BEFORE UPDATE ON inventory_logs
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

-- -----------------------------------------------------------------------------
-- MODULE 3 — Sales & orders
-- -----------------------------------------------------------------------------

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_number VARCHAR(32) NOT NULL,
  store_id UUID NOT NULL REFERENCES stores (id) ON DELETE RESTRICT,
  user_id UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  order_type order_type NOT NULL,
  status order_status NOT NULL,
  total_amount NUMERIC(14, 4) NOT NULL,
  payment_method payment_method NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT orders_total_non_negative CHECK (total_amount >= 0)
);

CREATE UNIQUE INDEX uq_orders_order_number ON orders (order_number);

CREATE INDEX idx_orders_store_id ON orders (store_id);
CREATE INDEX idx_orders_user_id ON orders (user_id);
CREATE INDEX idx_orders_created_at ON orders (created_at);

CREATE TRIGGER orders_set_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products (id) ON DELETE RESTRICT,
  batch_id UUID NOT NULL REFERENCES batches (id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL,
  price_at_sale NUMERIC(14, 4) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT order_items_qty_positive CHECK (quantity > 0),
  CONSTRAINT order_items_price_non_negative CHECK (price_at_sale >= 0)
);

CREATE INDEX idx_order_items_order_id ON order_items (order_id);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);
CREATE INDEX idx_order_items_batch_id ON order_items (batch_id);

CREATE OR REPLACE FUNCTION trg_order_items_sync_product_from_batch()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_pid UUID;
BEGIN
  SELECT b.product_id INTO v_pid FROM batches b WHERE b.id = NEW.batch_id;
  IF v_pid IS NULL THEN
    RAISE EXCEPTION 'batch % not found', NEW.batch_id;
  END IF;
  IF NEW.product_id IS DISTINCT FROM v_pid THEN
    NEW.product_id := v_pid;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER order_items_sync_product_from_batch
BEFORE INSERT OR UPDATE OF batch_id, product_id ON order_items
FOR EACH ROW EXECUTE PROCEDURE trg_order_items_sync_product_from_batch();

CREATE TRIGGER order_items_set_updated_at
BEFORE UPDATE ON order_items
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

-- -----------------------------------------------------------------------------
-- MODULE 4 — Prescriptions
-- -----------------------------------------------------------------------------

CREATE TABLE prescriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  uploaded_by UUID REFERENCES users (id) ON DELETE SET NULL,
  file_url TEXT NOT NULL,
  doctor_name TEXT,
  notes TEXT,
  status prescription_status NOT NULL DEFAULT 'UPLOADED',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prescriptions_order_id ON prescriptions (order_id);

CREATE TRIGGER prescriptions_set_updated_at
BEFORE UPDATE ON prescriptions
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

-- -----------------------------------------------------------------------------
-- MODULE 5 — Alerts (AI-lite / operational)
-- -----------------------------------------------------------------------------

CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id UUID NOT NULL REFERENCES stores (id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products (id) ON DELETE CASCADE,
  batch_id UUID REFERENCES batches (id) ON DELETE SET NULL,
  alert_type alert_type NOT NULL,
  message TEXT NOT NULL,
  severity alert_severity NOT NULL,
  trigger_value NUMERIC(18, 6),
  threshold_value NUMERIC(18, 6),
  is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT alerts_message_not_blank CHECK (LENGTH(TRIM(message)) > 0)
);

CREATE INDEX idx_alerts_store_id ON alerts (store_id);
CREATE INDEX idx_alerts_product_id ON alerts (product_id);
CREATE INDEX idx_alerts_batch_id ON alerts (batch_id);
CREATE INDEX idx_alerts_unresolved ON alerts (store_id, is_resolved) WHERE is_resolved = FALSE;
CREATE INDEX idx_alerts_type_severity_unresolved
  ON alerts (alert_type, severity, is_resolved)
  WHERE is_resolved = FALSE;

CREATE TRIGGER alerts_set_updated_at
BEFORE UPDATE ON alerts
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

-- -----------------------------------------------------------------------------
-- MODULE 6 — Analytics rollups (optional materialized storage)
-- -----------------------------------------------------------------------------

CREATE TABLE daily_sales_summary (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id UUID NOT NULL REFERENCES stores (id) ON DELETE CASCADE,
  summary_date DATE NOT NULL,
  total_sales NUMERIC(16, 4) NOT NULL DEFAULT 0,
  total_orders INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_daily_sales_store_date UNIQUE (store_id, summary_date),
  CONSTRAINT daily_sales_summary_totals_non_negative CHECK (total_sales >= 0 AND total_orders >= 0)
);

CREATE INDEX idx_daily_sales_summary_store_date ON daily_sales_summary (store_id, summary_date);

CREATE TRIGGER daily_sales_summary_set_updated_at
BEFORE UPDATE ON daily_sales_summary
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

-- -----------------------------------------------------------------------------
-- MODULE 7 — Inter-store stock transfers (multi-store realism)
-- -----------------------------------------------------------------------------

CREATE TABLE stock_transfers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_store_id UUID NOT NULL REFERENCES stores (id) ON DELETE RESTRICT,
  to_store_id UUID NOT NULL REFERENCES stores (id) ON DELETE RESTRICT,
  status stock_transfer_status NOT NULL DEFAULT 'PENDING',
  created_by UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT stock_transfers_different_stores CHECK (from_store_id <> to_store_id)
);

CREATE INDEX idx_stock_transfers_from_store ON stock_transfers (from_store_id);
CREATE INDEX idx_stock_transfers_to_store ON stock_transfers (to_store_id);
CREATE INDEX idx_stock_transfers_status ON stock_transfers (status);
CREATE INDEX idx_stock_transfers_created_by ON stock_transfers (created_by);
CREATE INDEX idx_stock_transfers_created_at ON stock_transfers (created_at);

CREATE TRIGGER stock_transfers_set_updated_at
BEFORE UPDATE ON stock_transfers
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

CREATE TABLE stock_transfer_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id UUID NOT NULL REFERENCES stock_transfers (id) ON DELETE CASCADE,
  batch_id UUID NOT NULL REFERENCES batches (id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT stock_transfer_items_qty_positive CHECK (quantity > 0)
);

CREATE INDEX idx_stock_transfer_items_transfer_id ON stock_transfer_items (transfer_id);
CREATE INDEX idx_stock_transfer_items_batch_id ON stock_transfer_items (batch_id);

COMMIT;
