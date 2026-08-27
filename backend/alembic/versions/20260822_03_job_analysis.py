"""Add persisted evidence-grounded Job Fit Analysis.

Revision ID: 20260822_03
Revises: 20260821_02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260822_03"
down_revision: str | None = "20260821_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("resume_hash", sa.String(length=64), nullable=False),
        sa.Column("experience_bank_hash", sa.String(length=64), nullable=False),
        sa.Column("structured_jd_hash", sa.String(length=64), nullable=False),
        sa.Column("matcher_model", sa.String(length=120), nullable=False),
        sa.Column("matcher_prompt_version", sa.String(length=40), nullable=False),
        sa.Column("matcher_schema_version", sa.String(length=40), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("requirement_matches", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("suggested_preparation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "match_score >= 0 AND match_score <= 100",
            name="ck_job_analyses_match_score",
        ),
        sa.CheckConstraint(
            "recommendation IN ('Strong Apply', 'Apply', 'Stretch', 'Skip')",
            name="ck_job_analyses_recommendation",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_job_analyses_job_id", "job_analyses", ["job_id"])


def downgrade() -> None:
    op.drop_table("job_analyses")
