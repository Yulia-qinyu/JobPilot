"""remove automatic application tracking infrastructure

Revision ID: 20261020_16
Revises: 20260910_15

This forward-only product simplification deliberately preserves the manual
application fields added by earlier migrations. Retired tracking data is
destructively removed and cannot be reconstructed by a downgrade.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261020_16"
down_revision: str | None = "20260910_15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop dependent tables before their referenced application/source tables.
    op.drop_table("application_tracking_bindings")
    op.drop_table("application_sync_runs")
    op.drop_table("application_platform_connections")
    op.drop_table("external_applications")
    op.drop_table("recruiting_source_extraction_profiles")
    op.drop_table("recruiting_sources")


def downgrade() -> None:
    raise RuntimeError(
        "20261020_16 permanently removes retired automatic-tracking data; "
        "restore a pre-migration database backup instead of downgrading."
    )
