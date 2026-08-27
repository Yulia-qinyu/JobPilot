"""Add the Phase 2 Job Pool.

Revision ID: 20260821_02
Revises: 20260821_01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260821_02"
down_revision: str | None = "20260821_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_profile_id", sa.Integer(), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("recruitment_type", sa.String(length=120), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("original_jd", sa.Text(), nullable=False),
        sa.Column("structured_jd", sa.JSON(), nullable=False),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("recommendation", sa.String(length=32), nullable=True),
        sa.Column("application_date", sa.Date(), nullable=True),
        sa.Column("next_stage", sa.String(length=255), nullable=True),
        sa.Column("interview_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("parser_model", sa.String(length=120), nullable=True),
        sa.Column("parser_prompt_version", sa.String(length=40), nullable=True),
        sa.Column("parser_schema_version", sa.String(length=40), nullable=True),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('Interested', 'Preparing', 'Applied', 'OA', 'Interview', "
            "'Final Interview', 'Offer', 'Rejected', 'Withdrawn')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint(
            "match_score IS NULL OR (match_score >= 0 AND match_score <= 100)",
            name="ck_jobs_match_score",
        ),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_jobs_user_profile_id", "jobs", ["user_profile_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_source_content_hash", "jobs", ["source_content_hash"])


def downgrade() -> None:
    op.drop_table("jobs")
