"""application tracking foundation

Revision ID: 20260908_12
Revises: 20260831_11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_12"
down_revision: str | None = "20260831_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("application_status_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE jobs
        SET application_status_changed_at = latest.changed_at
        FROM (
            SELECT job_id, MAX(created_at) AS changed_at
            FROM activity_events
            WHERE event_type = 'application_status_changed' AND job_id IS NOT NULL
            GROUP BY job_id
        ) AS latest
        WHERE jobs.id = latest.job_id
        """
    )

    op.create_table(
        "application_platform_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_profile_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("connection_status", sa.String(length=20), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "connection_status IN ('Disconnected','Connecting','Connected','AuthRequired','Error')",
            name="ck_application_platform_connections_status",
        ),
        sa.UniqueConstraint(
            "user_profile_id", "platform", name="uq_application_platform_connection"
        ),
    )
    op.create_index(
        "ix_application_platform_connections_user_profile_id",
        "application_platform_connections",
        ["user_profile_id"],
    )
    op.create_index(
        "ix_application_platform_connections_platform",
        "application_platform_connections",
        ["platform"],
    )

    op.create_table(
        "external_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_profile_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("identity_key", sa.String(length=64), nullable=False),
        sa.Column("external_application_id", sa.String(length=128), nullable=True),
        sa.Column("external_job_id", sa.String(length=128), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_status", sa.String(length=255), nullable=False),
        sa.Column(
            "normalized_status_id",
            sa.Integer(),
            sa.ForeignKey("application_status_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("normalized_status_key", sa.String(length=64), nullable=True),
        sa.Column("mapping_status", sa.String(length=16), nullable=False),
        sa.Column("external_application_date", sa.Date(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_status_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mapping_status IN ('Mapped','Unmapped')",
            name="ck_external_applications_mapping_status",
        ),
        sa.UniqueConstraint(
            "user_profile_id", "platform", "identity_key", name="uq_external_application_identity"
        ),
    )
    for column in ("user_profile_id", "platform", "normalized_status_id"):
        op.create_index(f"ix_external_applications_{column}", "external_applications", [column])

    op.create_table(
        "application_tracking_bindings",
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
        sa.Column(
            "external_application_id",
            sa.Integer(),
            sa.ForeignKey("external_applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("tracking_enabled", sa.Boolean(), nullable=False),
        sa.Column("binding_status", sa.String(length=24), nullable=False),
        sa.Column("binding_method", sa.String(length=32), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "binding_status IN ('active','rebind_required')",
            name="ck_application_tracking_bindings_status",
        ),
        sa.CheckConstraint(
            "binding_method IN ('user_confirmed')",
            name="ck_application_tracking_bindings_method",
        ),
        sa.UniqueConstraint("job_id", name="uq_application_tracking_bindings_job"),
        sa.UniqueConstraint(
            "external_application_id", name="uq_application_tracking_bindings_external"
        ),
    )
    for column in ("user_profile_id", "job_id", "external_application_id", "platform"):
        op.create_index(
            f"ix_application_tracking_bindings_{column}",
            "application_tracking_bindings",
            [column],
        )

    op.create_table(
        "application_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_profile_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("trigger", sa.String(length=24), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column(
            "requested_job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("checked_count", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column("changed_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("unmatched_count", sa.Integer(), nullable=False),
        sa.Column("ambiguous_count", sa.Integer(), nullable=False),
        sa.Column("unknown_status_count", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("errors_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('Running','Completed','Partial','AuthRequired','Failed')",
            name="ck_application_sync_runs_status",
        ),
        sa.CheckConstraint(
            "trigger IN ('manual_global','manual_job','scheduled')",
            name="ck_application_sync_runs_trigger",
        ),
        sa.CheckConstraint(
            "scope IN ('all_enabled','single_job')",
            name="ck_application_sync_runs_scope",
        ),
    )
    for column in ("user_profile_id", "platform", "requested_job_id", "status"):
        op.create_index(f"ix_application_sync_runs_{column}", "application_sync_runs", [column])


def downgrade() -> None:
    op.drop_table("application_sync_runs")
    op.drop_table("application_tracking_bindings")
    op.drop_table("external_applications")
    op.drop_table("application_platform_connections")
    op.drop_column("jobs", "application_status_changed_at")
