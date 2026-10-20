"""add external application ignore state

Revision ID: 20260910_15
Revises: 20260909_14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_15"
down_revision: str | None = "20260909_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "external_applications",
        sa.Column("ignored_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("external_applications", "ignored_at")
