"""initial users table

Revision ID: 001_initial
Revises:
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    user_role = postgresql.ENUM(
        "admin", "manager", "staff", name="user_role", create_type=True
    )
    user_role.create(bind, checkfirst=True)
    # sa.Enum ignores create_type=False for PG; dialect ENUM does not re-emit CREATE TYPE
    user_role_column = postgresql.ENUM(
        "admin", "manager", "staff", name="user_role", create_type=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_column, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_table("users")
    op.execute(sa.text("DROP TYPE IF EXISTS user_role"))
