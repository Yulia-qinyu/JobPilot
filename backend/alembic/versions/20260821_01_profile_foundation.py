"""Create Profile foundation tables.

Revision ID: 20260821_01
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260821_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("preferred_location", sa.String(length=120), nullable=True),
        *timestamp_columns(),
    )
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_profile_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("structured_profile", sa.JSON(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_profile_id"),
    )
    op.create_index("ix_resumes_user_profile_id", "resumes", ["user_profile_id"])
    for table_name, constraint_name in (
        ("target_companies", "uq_company_profile_name"),
        ("target_roles", "uq_role_profile_name"),
    ):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_profile_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            *timestamp_columns(),
            sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_profile_id", "name", name=constraint_name),
        )
        op.create_index(f"ix_{table_name}_user_profile_id", table_name, ["user_profile_id"])
    op.create_table(
        "experiences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_profile_id", sa.Integer(), nullable=False),
        sa.Column("source_resume_id", sa.Integer(), nullable=True),
        sa.Column("organization", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("experience_type", sa.String(length=20), nullable=False),
        sa.Column("date_range", sa.String(length=120), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["source_resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_experiences_user_profile_id", "experiences", ["user_profile_id"])
    op.create_index("ix_experiences_source_resume_id", "experiences", ["source_resume_id"])
    op.create_table(
        "experience_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experience_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["experience_id"], ["experiences.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_experience_facts_experience_id", "experience_facts", ["experience_id"])


def downgrade() -> None:
    op.drop_table("experience_facts")
    op.drop_table("experiences")
    op.drop_table("target_roles")
    op.drop_table("target_companies")
    op.drop_table("resumes")
    op.drop_table("user_profiles")
