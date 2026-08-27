"""Add target-role priorities and persisted job decisions.

Revision ID: 20260824_05
Revises: 20260823_04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260824_05"
down_revision: str | None = "20260823_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLE_FAMILIES = (
    "ai_product",
    "fintech_product",
    "data_product",
    "strategy_product",
    "platform_product",
    "growth_product",
    "general_product",
    "product_operations",
    "solution",
    "engineering",
    "algorithm",
    "design",
    "other",
    "unknown",
)


def upgrade() -> None:
    op.add_column(
        "target_roles",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="primary"),
    )
    op.add_column(
        "target_roles",
        sa.Column("role_family", sa.String(length=40), nullable=False, server_default="unknown"),
    )
    op.create_check_constraint(
        "ck_target_roles_priority",
        "target_roles",
        "priority IN ('primary', 'secondary', 'exploratory')",
    )
    families_sql = ", ".join(f"'{item}'" for item in ROLE_FAMILIES)
    op.create_check_constraint(
        "ck_target_roles_role_family",
        "target_roles",
        f"role_family IN ({families_sql})",
    )

    op.create_table(
        "job_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("auto_role_family", sa.String(length=40), nullable=False),
        sa.Column("role_family_override", sa.String(length=40), nullable=True),
        sa.Column("effective_role_family", sa.String(length=40), nullable=False),
        sa.Column("role_classification_confidence", sa.String(length=10), nullable=False),
        sa.Column("role_classification_reasons", sa.JSON(), nullable=False),
        sa.Column("classifier_version", sa.String(length=40), nullable=False),
        sa.Column("auto_eligibility_status", sa.String(length=24), nullable=False),
        sa.Column("eligibility_override", sa.String(length=24), nullable=True),
        sa.Column("effective_eligibility_status", sa.String(length=24), nullable=False),
        sa.Column("eligibility_reasons", sa.JSON(), nullable=False),
        sa.Column("blocking_requirements", sa.JSON(), nullable=False),
        sa.Column("unknown_requirements", sa.JSON(), nullable=False),
        sa.Column("eligibility_override_reason", sa.Text(), nullable=True),
        sa.Column("target_role_fit", sa.String(length=20), nullable=False),
        sa.Column("pre_match_decision", sa.String(length=24), nullable=False),
        sa.Column("final_decision", sa.String(length=16), nullable=True),
        sa.Column("decision_reasons", sa.JSON(), nullable=False),
        sa.Column("candidate_hash", sa.String(length=64), nullable=False),
        sa.Column("target_roles_hash", sa.String(length=64), nullable=False),
        sa.Column("job_input_hash", sa.String(length=64), nullable=False),
        sa.Column("analysis_hash", sa.String(length=64), nullable=True),
        sa.Column("engine_version", sa.String(length=40), nullable=False),
        sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_job_decisions_job_id"),
        sa.CheckConstraint(
            "role_classification_confidence IN ('High', 'Medium', 'Low')",
            name="ck_job_decisions_role_confidence",
        ),
        sa.CheckConstraint(
            "auto_eligibility_status IN ('Eligible', 'PossiblyEligible', 'Ineligible', 'Unknown')",
            name="ck_job_decisions_auto_eligibility",
        ),
        sa.CheckConstraint(
            "effective_eligibility_status IN ('Eligible', 'PossiblyEligible', 'Ineligible', 'Unknown')",
            name="ck_job_decisions_effective_eligibility",
        ),
        sa.CheckConstraint(
            "eligibility_override IS NULL OR eligibility_override IN "
            "('Eligible', 'PossiblyEligible', 'Ineligible', 'Unknown')",
            name="ck_job_decisions_eligibility_override",
        ),
        sa.CheckConstraint(
            "target_role_fit IN ('Primary', 'Secondary', 'Exploratory', 'Low', 'NotTarget', 'Unknown')",
            name="ck_job_decisions_target_role_fit",
        ),
        sa.CheckConstraint(
            "pre_match_decision IN ('WorthAnalyzing', 'LowPriority', 'Exclude')",
            name="ck_job_decisions_pre_match",
        ),
        sa.CheckConstraint(
            "final_decision IS NULL OR final_decision IN ('Priority', 'Apply', 'Consider', 'Skip')",
            name="ck_job_decisions_final",
        ),
    )
    for column in (
        "job_id",
        "auto_role_family",
        "role_family_override",
        "effective_role_family",
        "auto_eligibility_status",
        "eligibility_override",
        "effective_eligibility_status",
        "target_role_fit",
        "pre_match_decision",
        "final_decision",
        "candidate_hash",
        "target_roles_hash",
        "job_input_hash",
        "analysis_hash",
        "is_stale",
    ):
        op.create_index(f"ix_job_decisions_{column}", "job_decisions", [column])


def downgrade() -> None:
    op.drop_table("job_decisions")
    op.drop_constraint("ck_target_roles_role_family", "target_roles", type_="check")
    op.drop_constraint("ck_target_roles_priority", "target_roles", type_="check")
    op.drop_column("target_roles", "role_family")
    op.drop_column("target_roles", "priority")
