-- =============================================================================
-- Refinement migration 002 — Omnichannel Pharmacy Platform
-- =============================================================================
-- Apply on a database that was created from an *older* omnichannel_pharmacy_schema.sql
-- (before Module 7 + inventory traceability columns). Safe to re-run: idempotent.
--
-- If you bootstrap from the current omnichannel_pharmacy_schema.sql (already refined),
-- skip this file — it will no-op where objects already exist.
--
-- Additions:
-- 1) inventory_logs: source_type, reference_id, notes
-- 2) stock_transfers / stock_transfer_items
-- 3) orders: order_number (unique), notes
-- 4) alerts: trigger_value, threshold_value
-- 5) products: is_deleted
-- 6) prescriptions: status enum replaces verified boolean
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- New ENUM types (skip if already created, e.g. from merged base schema)
-- -----------------------------------------------------------------------------
DO $$ BEGIN
  CREATE TYPE inventory_log_source_type AS ENUM ('SALE', 'RESTOCK', 'TRANSFER', 'ADJUSTMENT');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE stock_transfer_status AS ENUM ('PENDING', 'COMPLETED', 'CANCELLED');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE prescription_status AS ENUM ('UPLOADED', 'VERIFIED', 'REJECTED');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 5) products — soft delete
-- -----------------------------------------------------------------------------

ALTER TABLE products
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN products.is_deleted IS
  'Soft-delete flag; keep row for audit and historical batch/order references.';

-- -----------------------------------------------------------------------------
-- 3) orders — human-readable number + notes
-- -----------------------------------------------------------------------------

ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS order_number VARCHAR(32),
  ADD COLUMN IF NOT EXISTS notes TEXT;

COMMENT ON COLUMN orders.order_number IS
  'Stable external identifier, e.g. ORD-2026-0001 (globally unique).';
COMMENT ON COLUMN orders.notes IS
  'Optional cashier or compliance notes.';

WITH numbered AS (
  SELECT
    id,
    'ORD-'
      || EXTRACT(YEAR FROM created_at AT TIME ZONE 'UTC')::INT
      || '-'
      || LPAD(
        ROW_NUMBER() OVER (
          PARTITION BY EXTRACT(YEAR FROM created_at AT TIME ZONE 'UTC')
          ORDER BY created_at ASC, id ASC
        )::TEXT,
        4,
        '0'
      ) AS computed_number
  FROM orders
  WHERE order_number IS NULL
)
UPDATE orders o
SET order_number = n.computed_number
FROM numbered n
WHERE o.id = n.id;

-- Only enforce NOT NULL when every row has a value (or table is empty)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM orders WHERE order_number IS NULL) THEN
    ALTER TABLE orders ALTER COLUMN order_number SET NOT NULL;
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_order_number ON orders (order_number);

-- -----------------------------------------------------------------------------
-- 1) inventory_logs — traceability
-- -----------------------------------------------------------------------------

ALTER TABLE inventory_logs
  ADD COLUMN IF NOT EXISTS source_type inventory_log_source_type,
  ADD COLUMN IF NOT EXISTS reference_id UUID,
  ADD COLUMN IF NOT EXISTS notes TEXT;

COMMENT ON COLUMN inventory_logs.source_type IS
  'Business context: sale, restock, transfer, adjustment.';
COMMENT ON COLUMN inventory_logs.reference_id IS
  'Polymorphic: orders.id (SALE) or stock_transfers.id (TRANSFER); nullable otherwise.';
COMMENT ON COLUMN inventory_logs.notes IS
  'Auditor-facing free text.';

UPDATE inventory_logs
SET source_type = 'ADJUSTMENT'
WHERE source_type IS NULL;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'inventory_logs' AND column_name = 'source_type'
  ) AND NOT EXISTS (SELECT 1 FROM inventory_logs WHERE source_type IS NULL) THEN
    ALTER TABLE inventory_logs ALTER COLUMN source_type SET NOT NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_inventory_logs_source_reference
  ON inventory_logs (source_type, reference_id);

-- -----------------------------------------------------------------------------
-- 4) alerts — numeric context
-- -----------------------------------------------------------------------------

ALTER TABLE alerts
  ADD COLUMN IF NOT EXISTS trigger_value NUMERIC(18, 6),
  ADD COLUMN IF NOT EXISTS threshold_value NUMERIC(18, 6);

COMMENT ON COLUMN alerts.trigger_value IS 'Observed value when the alert fired.';
COMMENT ON COLUMN alerts.threshold_value IS 'Configured threshold crossed.';

CREATE INDEX IF NOT EXISTS idx_alerts_type_severity_unresolved
  ON alerts (alert_type, severity, is_resolved)
  WHERE is_resolved = FALSE;

-- -----------------------------------------------------------------------------
-- 6) prescriptions — status replaces verified (legacy column only)
-- -----------------------------------------------------------------------------

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'prescriptions' AND column_name = 'verified'
  ) THEN
    ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS status prescription_status;
    UPDATE prescriptions
    SET status = CASE
      WHEN verified IS TRUE THEN 'VERIFIED'::prescription_status
      ELSE 'UPLOADED'::prescription_status
    END
    WHERE status IS NULL;
    ALTER TABLE prescriptions ALTER COLUMN status SET NOT NULL;
    ALTER TABLE prescriptions ALTER COLUMN status SET DEFAULT 'UPLOADED'::prescription_status;
    ALTER TABLE prescriptions DROP COLUMN verified;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2) Stock transfer module (skip if tables already exist)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS stock_transfers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_store_id UUID NOT NULL REFERENCES stores (id) ON DELETE RESTRICT,
  to_store_id UUID NOT NULL REFERENCES stores (id) ON DELETE RESTRICT,
  status stock_transfer_status NOT NULL DEFAULT 'PENDING',
  created_by UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT stock_transfers_different_stores CHECK (from_store_id <> to_store_id)
);

CREATE INDEX IF NOT EXISTS idx_stock_transfers_from_store ON stock_transfers (from_store_id);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_to_store ON stock_transfers (to_store_id);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_status ON stock_transfers (status);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_created_by ON stock_transfers (created_by);
CREATE INDEX IF NOT EXISTS idx_stock_transfers_created_at ON stock_transfers (created_at);

DROP TRIGGER IF EXISTS stock_transfers_set_updated_at ON stock_transfers;
CREATE TRIGGER stock_transfers_set_updated_at
BEFORE UPDATE ON stock_transfers
FOR EACH ROW EXECUTE PROCEDURE trg_set_updated_at();

COMMENT ON TABLE stock_transfers IS
  'Inter-store stock movement header; inventory_logs.reference_id may point here when source_type=TRANSFER.';

CREATE TABLE IF NOT EXISTS stock_transfer_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id UUID NOT NULL REFERENCES stock_transfers (id) ON DELETE CASCADE,
  batch_id UUID NOT NULL REFERENCES batches (id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT stock_transfer_items_qty_positive CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS idx_stock_transfer_items_transfer_id ON stock_transfer_items (transfer_id);
CREATE INDEX IF NOT EXISTS idx_stock_transfer_items_batch_id ON stock_transfer_items (batch_id);

COMMENT ON TABLE stock_transfer_items IS 'Per-batch lines for a stock transfer.';

COMMIT;
