"""Add automatic and override Target Role family semantics.

Revision ID: 20260824_06
Revises: 20260824_05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260824_06"
down_revision: str | None = "20260824_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_FAMILIES_SQL = (
    "'ai_product', 'fintech_product', 'data_product', 'strategy_product', "
    "'platform_product', 'growth_product', 'general_product', 'product_operations', "
    "'solution', 'engineering', 'algorithm', 'design', 'other', 'unknown'"
)


def upgrade() -> None:
    op.add_column(
        "target_roles",
        sa.Column(
            "auto_role_family", sa.String(length=40), nullable=False, server_default="unknown"
        ),
    )
    op.add_column(
        "target_roles", sa.Column("role_family_override", sa.String(length=40), nullable=True)
    )
    # A non-unknown value in the previous UI was explicitly selected by the user.
    # Preserve it as an override; the deterministic backfill supplies the auto value.
    op.execute(
        "UPDATE target_roles SET role_family_override = role_family "
        "WHERE role_family <> 'unknown'"
    )
    op.create_check_constraint(
        "ck_target_roles_auto_role_family",
        "target_roles",
        f"auto_role_family IN ({ROLE_FAMILIES_SQL})",
    )
    op.create_check_constraint(
        "ck_target_roles_role_family_override",
        "target_roles",
        f"role_family_override IS NULL OR role_family_override IN ({ROLE_FAMILIES_SQL})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_target_roles_role_family_override", "target_roles", type_="check"
    )
    op.drop_constraint("ck_target_roles_auto_role_family", "target_roles", type_="check")
    op.drop_column("target_roles", "role_family_override")
    op.drop_column("target_roles", "auto_role_family")
