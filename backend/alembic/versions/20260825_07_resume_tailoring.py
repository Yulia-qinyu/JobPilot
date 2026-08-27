"""Add evidence-grounded resume tailoring persistence.

Revision ID: 20260825_07
Revises: 20260824_06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_07"
down_revision: str | None = "20260824_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resume_tailorings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("source_resume_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("tailoring_plan", sa.JSON(), nullable=False),
        sa.Column("generated_draft", sa.JSON(), nullable=False),
        sa.Column("user_edited_draft", sa.JSON(), nullable=True),
        sa.Column("validation_results", sa.JSON(), nullable=False),
        sa.Column("plan_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resume_hash", sa.String(length=64), nullable=False),
        sa.Column("experience_bank_hash", sa.String(length=64), nullable=False),
        sa.Column("structured_jd_hash", sa.String(length=64), nullable=False),
        sa.Column("analysis_hash", sa.String(length=64), nullable=False),
        sa.Column("plan_hash", sa.String(length=64), nullable=False),
        sa.Column("generator_model", sa.String(length=120), nullable=True),
        sa.Column("generator_prompt_version", sa.String(length=40), nullable=True),
        sa.Column("generator_schema_version", sa.String(length=40), nullable=True),
        sa.Column("validator_model", sa.String(length=120), nullable=True),
        sa.Column("validator_prompt_version", sa.String(length=40), nullable=True),
        sa.Column("validator_schema_version", sa.String(length=40), nullable=True),
        sa.Column("guardrail_version", sa.String(length=40), nullable=False),
        sa.Column("generation_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PlanReady', 'DraftReady', 'Edited', 'PendingValidation', "
            "'ValidationFailed', 'Accepted')",
            name="ck_resume_tailorings_status",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_resume_tailorings_job_id"),
    )
    for column in (
        "job_id",
        "source_resume_id",
        "status",
        "resume_hash",
        "experience_bank_hash",
        "structured_jd_hash",
        "analysis_hash",
        "plan_hash",
    ):
        op.create_index(f"ix_resume_tailorings_{column}", "resume_tailorings", [column])


def downgrade() -> None:
    op.drop_table("resume_tailorings")
