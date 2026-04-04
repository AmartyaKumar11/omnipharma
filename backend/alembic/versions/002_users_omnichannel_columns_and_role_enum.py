"""Align users table with omnichannel app model (columns + user_role enum).

Revision ID: 002_users_omni
Revises: 001_initial
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "002_users_omni"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = inspect(bind)
    try:
        cols = {c["name"] for c in insp.get_columns(table)}
    except Exception:
        return False
    return column in cols


def _enum_labels(bind) -> list[str]:
    """Return labels for PostgreSQL enum type user_role, or empty if missing."""
    rows = bind.execute(
        text(
            """
            SELECT e.enumlabel::text
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'user_role'
            ORDER BY e.enumsortorder
            """
        )
    ).fetchall()
    return [r[0] for r in rows]


def upgrade() -> None:
    bind = op.get_bind()

    # --- Add missing columns (legacy 001_initial only had id, email, password_hash, role, created_at)
    if not _has_column(bind, "users", "full_name"):
        op.add_column("users", sa.Column("full_name", sa.Text(), nullable=True))
    if not _has_column(bind, "users", "is_active"):
        op.add_column(
            "users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
    if not _has_column(bind, "users", "last_login_at"):
        op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column(bind, "users", "updated_at"):
        op.add_column(
            "users",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    labels = _enum_labels(bind)
    if not labels:
        return

    # Already migrated (omnichannel SQL or previous run)
    if "ADMIN" in labels and "admin" not in labels:
        return

    # Migrate lowercase legacy enum -> uppercase omnichannel enum
    if "admin" in labels:
        op.execute(text("CREATE TYPE user_role_new AS ENUM ('ADMIN', 'BRANCH_MANAGER', 'INVENTORY_CONTROLLER', 'STAFF')"))
        op.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role_new user_role_new"))
        op.execute(
            text(
                """
                UPDATE users SET role_new = CASE role::text
                    WHEN 'admin' THEN 'ADMIN'::user_role_new
                    WHEN 'manager' THEN 'BRANCH_MANAGER'::user_role_new
                    WHEN 'staff' THEN 'STAFF'::user_role_new
                    ELSE 'STAFF'::user_role_new
                END
                """
            )
        )
        op.execute(text("ALTER TABLE users DROP COLUMN role"))
        op.execute(text("DROP TYPE user_role"))
        op.execute(text("ALTER TYPE user_role_new RENAME TO user_role"))
        op.execute(text("ALTER TABLE users RENAME COLUMN role_new TO role"))
        op.execute(text("ALTER TABLE users ALTER COLUMN role SET NOT NULL"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for enum migration")
