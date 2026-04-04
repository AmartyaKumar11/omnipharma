"""Set PostgreSQL DEFAULT now() on users.created_at (matches SQLAlchemy server_default).

Revision ID: 003_created_at_default
Revises: 002_users_omni
Create Date: 2026-04-04

001_initial created created_at NOT NULL without a DB default; inserts then failed with
NotNullViolation because ORM omits the column and relies on the server default.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_created_at_default"
down_revision: Union[str, None] = "002_users_omni"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
