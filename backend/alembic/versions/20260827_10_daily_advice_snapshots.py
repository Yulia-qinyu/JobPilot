"""daily advice snapshots

Revision ID: 20260827_10
Revises: 20260827_09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_10"
down_revision: str | None = "20260827_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_advice_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_profile_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("advice_date", sa.Date(), nullable=False),
        sa.Column("planning_context_hash", sa.String(length=64), nullable=False),
        sa.Column("strategy", sa.String(length=24), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "strategy IN ('high_volume','focused','balanced','interview_first')",
            name="ck_daily_advice_snapshots_strategy",
        ),
        sa.CheckConstraint(
            "status IN ('Generated','Fallback')",
            name="ck_daily_advice_snapshots_status",
        ),
    )
    for column in (
        "user_profile_id",
        "advice_date",
        "planning_context_hash",
        "generated_at",
    ):
        op.create_index(
            f"ix_daily_advice_snapshots_{column}",
            "daily_advice_snapshots",
            [column],
        )


def downgrade() -> None:
    op.drop_table("daily_advice_snapshots")
