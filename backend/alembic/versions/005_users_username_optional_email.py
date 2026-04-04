"""Add username (unique login id); email becomes optional.

Revision ID: 005_username
Revises: 004_omni_core
Create Date: 2026-04-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_username"
down_revision: Union[str, None] = "004_omni_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE users
            SET username = lower(split_part(email::text, '@', 1))
                 || '_' || substring(replace(id::text, '-', ''), 1, 12)
            WHERE username IS NULL
            """
        )
    )
    op.alter_column("users", "username", existing_type=sa.String(length=64), nullable=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.alter_column("users", "email", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute(sa.text("UPDATE users SET email = COALESCE(email, username || '@local.invalid') WHERE email IS NULL"))
    op.alter_column("users", "email", existing_type=sa.Text(), nullable=False)
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
