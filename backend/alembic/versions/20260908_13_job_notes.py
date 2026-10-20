"""add canonical job notes and application deadline

Revision ID: 20260908_13
Revises: 20260908_12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_13"
down_revision: str | None = "20260908_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "job_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_profile_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_type", sa.String(length=16), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "author_type IN ('human','agent')", name="ck_job_notes_author_type"
        ),
        sa.UniqueConstraint("job_id", "dedupe_key", name="uq_job_notes_job_dedupe_key"),
    )
    op.create_index("ix_job_notes_user_profile_id", "job_notes", ["user_profile_id"])
    op.create_index("ix_job_notes_job_id", "job_notes", ["job_id"])
    op.create_index("ix_job_notes_author_type", "job_notes", ["author_type"])

    # Preserve legacy notes as the first human-authored timeline entry. The old
    # column remains unchanged for backward compatibility and safe downgrade;
    # all new Phase B writes use job_notes exclusively.
    op.execute(
        """
        INSERT INTO job_notes (
            user_profile_id, job_id, content, author_type, metadata_json,
            dedupe_key, created_at, updated_at
        )
        SELECT
            user_profile_id,
            id,
            notes,
            'human',
            '{"source":"legacy_job_notes_migration"}',
            'legacy-job-notes-backfill',
            updated_at,
            updated_at
        FROM jobs
        WHERE notes IS NOT NULL AND BTRIM(notes) <> ''
        """
    )


def downgrade() -> None:
    op.drop_index("ix_job_notes_author_type", table_name="job_notes")
    op.drop_index("ix_job_notes_job_id", table_name="job_notes")
    op.drop_index("ix_job_notes_user_profile_id", table_name="job_notes")
    op.drop_table("job_notes")
    op.drop_column("jobs", "deadline_at")
