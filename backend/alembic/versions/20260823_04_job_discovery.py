"""Add source identity and job import sessions.

Revision ID: 20260823_04
Revises: 20260822_03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260823_04"
down_revision: str | None = "20260822_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("source", sa.String(length=32), nullable=True))
    op.add_column("jobs", sa.Column("external_job_id", sa.String(length=128), nullable=True))
    op.add_column("jobs", sa.Column("external_job_code", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("source_metadata", sa.JSON(), nullable=True))
    op.add_column("jobs", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_unique_constraint(
        "uq_jobs_profile_source_external_id",
        "jobs",
        ["user_profile_id", "source", "external_job_id"],
    )

    op.create_table(
        "job_import_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_profile_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("search_url", sa.Text(), nullable=False),
        sa.Column("search_url_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=20), nullable=False),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("result_job_ids", sa.JSON(), nullable=False),
        sa.Column("failure_details", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('Queued', 'Running', 'Completed', 'Partial', 'Failed')",
            name="ck_job_import_sessions_status",
        ),
        sa.CheckConstraint(
            "stage IN ('Discovering', 'Importing', 'Completed')",
            name="ck_job_import_sessions_stage",
        ),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_job_import_sessions_user_profile_id",
        "job_import_sessions",
        ["user_profile_id"],
    )
    op.create_index("ix_job_import_sessions_source", "job_import_sessions", ["source"])
    op.create_index("ix_job_import_sessions_status", "job_import_sessions", ["status"])
    op.create_index(
        "ix_job_import_sessions_search_url_hash",
        "job_import_sessions",
        ["search_url_hash"],
    )


def downgrade() -> None:
    op.drop_table("job_import_sessions")
    op.drop_constraint("uq_jobs_profile_source_external_id", "jobs", type_="unique")
    op.drop_index("ix_jobs_source", table_name="jobs")
    op.drop_column("jobs", "last_seen_at")
    op.drop_column("jobs", "source_metadata")
    op.drop_column("jobs", "external_job_code")
    op.drop_column("jobs", "external_job_id")
    op.drop_column("jobs", "source")
