"""application workspace foundation

Revision ID: 20260826_08
Revises: 20260825_07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_08"
down_revision: str | None = "20260825_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULTS = [
    ("interested", "感兴趣", 10, "Interested"),
    ("to_apply", "待投递", 20, "Preparing"),
    ("applied", "已投递", 30, "Applied"),
    ("oa", "笔试", 40, "OA"),
    ("interview", "面试中", 50, "Interview"),
    ("final_interview", "终面", 60, "Final Interview"),
    ("offer", "Offer", 70, "Offer"),
    ("rejected", "未通过", 80, "Rejected"),
    ("withdrawn", "已撤回", 90, "Withdrawn"),
]


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("job_search_strategy", sa.String(length=24), nullable=False, server_default="balanced"),
    )
    op.create_table(
        "application_status_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_system_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("legacy_status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_profile_id", "key", name="uq_application_status_profile_key"),
        sa.UniqueConstraint("user_profile_id", "label", name="uq_application_status_profile_label"),
    )
    op.create_index("ix_application_status_definitions_user_profile_id", "application_status_definitions", ["user_profile_id"])
    status_table = sa.table(
        "application_status_definitions",
        sa.column("user_profile_id", sa.Integer), sa.column("key", sa.String),
        sa.column("label", sa.String), sa.column("sort_order", sa.Integer),
        sa.column("is_system_default", sa.Boolean), sa.column("is_active", sa.Boolean),
        sa.column("legacy_status", sa.String),
    )
    bind = op.get_bind()
    profile_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM user_profiles"))]
    for profile_id in profile_ids:
        op.bulk_insert(status_table, [dict(user_profile_id=profile_id, key=key, label=label, sort_order=order, is_system_default=True, is_active=True, legacy_status=legacy) for key, label, order, legacy in DEFAULTS])
    op.add_column("jobs", sa.Column("application_status_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_jobs_application_status_id", "jobs", "application_status_definitions", ["application_status_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_jobs_application_status_id", "jobs", ["application_status_id"])
    bind.execute(sa.text("UPDATE jobs SET application_status_id = s.id FROM application_status_definitions s WHERE s.user_profile_id = jobs.user_profile_id AND s.legacy_status = jobs.status"))
    op.create_table(
        "plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time_optional", sa.String(length=5), nullable=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=24), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('application','resume','interview_prep','job_search','follow_up','other')", name="ck_plan_items_type"),
        sa.CheckConstraint("status IN ('todo','done')", name="ck_plan_items_status"),
        sa.CheckConstraint("created_by IN ('user','agent_suggestion')", name="ck_plan_items_created_by"),
    )
    for column in ("user_profile_id", "date", "job_id", "status"):
        op.create_index(f"ix_plan_items_{column}", "plan_items", [column])
    op.create_table(
        "activity_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_item_id", sa.Integer(), sa.ForeignKey("plan_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("user_profile_id", "event_type", "job_id", "plan_item_id"):
        op.create_index(f"ix_activity_events_{column}", "activity_events", [column])


def downgrade() -> None:
    op.drop_table("activity_events")
    op.drop_table("plan_items")
    op.drop_index("ix_jobs_application_status_id", table_name="jobs")
    op.drop_constraint("fk_jobs_application_status_id", "jobs", type_="foreignkey")
    op.drop_column("jobs", "application_status_id")
    op.drop_table("application_status_definitions")
    op.drop_column("user_profiles", "job_search_strategy")
