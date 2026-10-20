"""add canonical recruiting source identity

Revision ID: 20260909_14
Revises: 20260908_13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260909_14"
down_revision: str | None = "20260908_13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recruiting_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_profile_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("collector_key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("applications_url", sa.Text(), nullable=True),
        sa.Column("normalized_origin", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('built_in','custom')", name="ck_recruiting_sources_type"
        ),
        sa.UniqueConstraint(
            "user_profile_id", "source_key", name="uq_recruiting_sources_profile_key"
        ),
    )
    for column in ("user_profile_id", "source_key", "source_type", "collector_key", "is_active"):
        op.create_index(f"ix_recruiting_sources_{column}", "recruiting_sources", [column])

    op.create_table(
        "recruiting_source_extraction_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "recruiting_source_id",
            sa.Integer(),
            sa.ForeignKey("recruiting_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("identity_quality", sa.String(length=16), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft','confirmed','retired')",
            name="ck_recruiting_source_extraction_profiles_status",
        ),
        sa.CheckConstraint(
            "identity_quality IN ('strong','partial','weak')",
            name="ck_recruiting_source_extraction_profiles_identity_quality",
        ),
        sa.UniqueConstraint(
            "recruiting_source_id",
            "version",
            name="uq_recruiting_source_extraction_profile_version",
        ),
        sa.UniqueConstraint(
            "recruiting_source_id",
            "profile_hash",
            name="uq_recruiting_source_extraction_profile_hash",
        ),
    )
    op.create_index(
        "ix_recruiting_source_extraction_profiles_recruiting_source_id",
        "recruiting_source_extraction_profiles",
        ["recruiting_source_id"],
    )
    op.create_index(
        "ix_recruiting_source_extraction_profiles_status",
        "recruiting_source_extraction_profiles",
        ["status"],
    )

    for table in (
        "application_platform_connections",
        "external_applications",
        "application_tracking_bindings",
        "application_sync_runs",
    ):
        op.add_column(table, sa.Column("recruiting_source_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_recruiting_source_id",
            table,
            "recruiting_sources",
            ["recruiting_source_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_recruiting_source_id", table, ["recruiting_source_id"])

    op.add_column(
        "external_applications",
        sa.Column("identity_strategy", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "external_applications",
        sa.Column("identity_quality", sa.String(length=16), nullable=True),
    )

    # Every existing profile receives the code-owned JD Campus source. This is
    # metadata-only: no connection, application, binding, or sync row is rebuilt.
    op.execute(
        """
        INSERT INTO recruiting_sources (
            user_profile_id, source_key, source_type, collector_key, display_name,
            company_name, applications_url, normalized_origin, is_active,
            created_at, updated_at
        )
        SELECT
            id, 'jd_campus', 'built_in', 'jd', '京东校园招聘', '京东',
            'https://campus.jd.com/#/myDeliver', 'https://campus.jd.com', TRUE,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM user_profiles
        """
    )

    for table in (
        "application_platform_connections",
        "external_applications",
        "application_tracking_bindings",
        "application_sync_runs",
    ):
        op.execute(
            f"""
            UPDATE {table} AS target
            SET recruiting_source_id = source.id
            FROM recruiting_sources AS source
            WHERE target.user_profile_id = source.user_profile_id
              AND target.platform = 'jd'
              AND source.source_key = 'jd_campus'
            """
        )

    op.execute(
        """
        UPDATE external_applications
        SET identity_strategy = CASE
                WHEN external_application_id IS NOT NULL THEN 'external_application_id'
                WHEN external_job_id IS NOT NULL THEN 'external_job_id'
                WHEN source_url IS NOT NULL THEN 'canonical_source_url'
                ELSE 'company_title_location'
            END,
            identity_quality = CASE
                WHEN external_application_id IS NOT NULL THEN 'strong'
                WHEN external_job_id IS NOT NULL THEN 'strong'
                WHEN source_url IS NOT NULL THEN 'strong'
                ELSE 'partial'
            END
        """
    )
    op.alter_column("external_applications", "identity_strategy", nullable=False)
    op.alter_column("external_applications", "identity_quality", nullable=False)
    op.create_check_constraint(
        "ck_external_applications_identity_quality",
        "external_applications",
        "identity_quality IN ('strong','partial','weak')",
    )
    op.create_unique_constraint(
        "uq_application_platform_connection_source",
        "application_platform_connections",
        ["recruiting_source_id"],
    )
    op.create_unique_constraint(
        "uq_external_application_source_identity",
        "external_applications",
        ["user_profile_id", "recruiting_source_id", "identity_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_external_application_source_identity", "external_applications", type_="unique"
    )
    op.drop_constraint(
        "uq_application_platform_connection_source",
        "application_platform_connections",
        type_="unique",
    )
    op.drop_constraint(
        "ck_external_applications_identity_quality", "external_applications", type_="check"
    )
    op.drop_column("external_applications", "identity_quality")
    op.drop_column("external_applications", "identity_strategy")

    for table in (
        "application_sync_runs",
        "application_tracking_bindings",
        "external_applications",
        "application_platform_connections",
    ):
        op.drop_index(f"ix_{table}_recruiting_source_id", table_name=table)
        op.drop_constraint(f"fk_{table}_recruiting_source_id", table, type_="foreignkey")
        op.drop_column(table, "recruiting_source_id")

    op.drop_index(
        "ix_recruiting_source_extraction_profiles_status",
        table_name="recruiting_source_extraction_profiles",
    )
    op.drop_index(
        "ix_recruiting_source_extraction_profiles_recruiting_source_id",
        table_name="recruiting_source_extraction_profiles",
    )
    op.drop_table("recruiting_source_extraction_profiles")
    for column in ("is_active", "collector_key", "source_type", "source_key", "user_profile_id"):
        op.drop_index(f"ix_recruiting_sources_{column}", table_name="recruiting_sources")
    op.drop_table("recruiting_sources")
