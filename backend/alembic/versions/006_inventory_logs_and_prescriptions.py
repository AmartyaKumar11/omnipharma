"""Create inventory_logs and prescriptions (required for sales audit + Rx orders).

Revision ID: 006_logs_rx
Revises: 005_username
Create Date: 2026-04-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_logs_rx"
down_revision: Union[str, None] = "005_username"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enums() -> None:
    for stmt in (
        """
        DO $$ BEGIN
            CREATE TYPE inventory_change_type AS ENUM ('ADD', 'REMOVE', 'ADJUST');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """,
        """
        DO $$ BEGIN
            CREATE TYPE inventory_log_source_type AS ENUM ('SALE', 'RESTOCK', 'TRANSFER', 'ADJUSTMENT');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """,
        """
        DO $$ BEGIN
            CREATE TYPE prescription_status AS ENUM ('UPLOADED', 'VERIFIED', 'REJECTED');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """,
    ):
        op.execute(sa.text(stmt))


def upgrade() -> None:
    _enums()

    inv_ct = postgresql.ENUM("ADD", "REMOVE", "ADJUST", name="inventory_change_type", create_type=False)
    inv_src = postgresql.ENUM(
        "SALE", "RESTOCK", "TRANSFER", "ADJUSTMENT", name="inventory_log_source_type", create_type=False
    )
    rx_st = postgresql.ENUM("UPLOADED", "VERIFIED", "REJECTED", name="prescription_status", create_type=False)

    op.create_table(
        "inventory_logs",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("inventory_id", sa.Uuid(), sa.ForeignKey("inventory.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("change_type", inv_ct, nullable=False),
        sa.Column("source_type", inv_src, nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("quantity_changed", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("quantity_changed <> 0", name="inventory_logs_quantity_changed_not_zero"),
    )
    op.create_index("ix_inventory_logs_inventory_id", "inventory_logs", ["inventory_id"])
    op.create_index("ix_inventory_logs_performed_by", "inventory_logs", ["performed_by"])
    op.create_index("ix_inventory_logs_created_at", "inventory_logs", ["created_at"])

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("doctor_name", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", rx_st, nullable=False, server_default=sa.text("'UPLOADED'::prescription_status")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_prescriptions_order_id", "prescriptions", ["order_id"])


def downgrade() -> None:
    op.drop_table("prescriptions")
    op.drop_table("inventory_logs")
    op.execute(sa.text("DROP TYPE IF EXISTS prescription_status CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS inventory_log_source_type CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS inventory_change_type CASCADE"))
