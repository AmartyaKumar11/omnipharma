"""Create omnichannel core tables: stores, products, batches, inventory, orders, order_items.

Revision ID: 004_omni_core
Revises: 003_created_at_default
Create Date: 2026-04-04

Dashboard and inventory APIs expect these tables; without them, queries raise ProgrammingError (500).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_omni_core"
down_revision: Union[str, None] = "003_created_at_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_enums() -> None:
    for stmt in (
        """
        DO $$ BEGIN
            CREATE TYPE order_type AS ENUM ('OTC', 'PRESCRIPTION');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """,
        """
        DO $$ BEGIN
            CREATE TYPE order_status AS ENUM ('COMPLETED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """,
        """
        DO $$ BEGIN
            CREATE TYPE payment_method AS ENUM ('CASH', 'CARD', 'UPI');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """,
    ):
        op.execute(sa.text(stmt))


def upgrade() -> None:
    _create_enums()

    order_type_e = postgresql.ENUM("OTC", "PRESCRIPTION", name="order_type", create_type=False)
    order_status_e = postgresql.ENUM("COMPLETED", "CANCELLED", name="order_status", create_type=False)
    payment_method_e = postgresql.ENUM("CASH", "CARD", "UPI", name="payment_method", create_type=False)

    op.create_table(
        "stores",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("contact_number", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("generic_name", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("manufacturer", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_prescription_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "batches",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("batch_number", sa.Text(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("manufacture_date", sa.Date(), nullable=True),
        sa.Column("purchase_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("selling_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("product_id", "batch_number", name="uq_batches_product_batch_number"),
    )
    op.create_index("ix_batches_product_id", "batches", ["product_id"])
    op.create_index("ix_batches_expiry_date", "batches", ["expiry_date"])

    op.create_table(
        "inventory",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("store_id", sa.Uuid(), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reorder_threshold", sa.Integer(), nullable=True),
        sa.Column("last_restocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("store_id", "batch_id", name="uq_inventory_store_batch"),
    )
    op.create_index("ix_inventory_store_id", "inventory", ["store_id"])
    op.create_index("ix_inventory_product_id", "inventory", ["product_id"])
    op.create_index("ix_inventory_batch_id", "inventory", ["batch_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_number", sa.Text(), nullable=False),
        sa.Column("store_id", sa.Uuid(), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_type", order_type_e, nullable=False),
        sa.Column("status", order_status_e, nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("payment_method", payment_method_e, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("uq_orders_order_number", "orders", ["order_number"], unique=True)
    op.create_index("ix_orders_store_id", "orders", ["store_id"])
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_at_sale", sa.Numeric(14, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])
    op.create_index("ix_order_items_batch_id", "order_items", ["batch_id"])


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("inventory")
    op.drop_table("batches")
    op.drop_table("products")
    op.drop_table("stores")
    op.execute(sa.text("DROP TYPE IF EXISTS payment_method CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS order_status CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS order_type CASCADE"))
