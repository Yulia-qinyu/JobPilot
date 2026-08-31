"""requirement taxonomy v2 score availability

Revision ID: 20260831_11
Revises: 20260827_10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_11"
down_revision: str | None = "20260827_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "job_analyses",
        "match_score",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "job_analyses",
        "recommendation",
        existing_type=sa.String(length=32),
        nullable=True,
    )


def downgrade() -> None:
    # V1 cannot represent an analysis with no evidence-matchable requirements.
    op.execute(
        sa.text(
            "UPDATE job_analyses SET match_score = 0, recommendation = 'Skip' "
            "WHERE match_score IS NULL OR recommendation IS NULL"
        )
    )
    op.alter_column(
        "job_analyses",
        "recommendation",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.alter_column(
        "job_analyses",
        "match_score",
        existing_type=sa.Integer(),
        nullable=False,
    )
