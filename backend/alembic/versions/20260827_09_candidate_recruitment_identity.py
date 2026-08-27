"""candidate recruitment identity

Revision ID: 20260827_09
Revises: 20260826_08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_09"
down_revision: str | None = "20260826_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("candidate_type", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("graduation_year", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_user_profiles_candidate_type",
        "user_profiles",
        "candidate_type IS NULL OR candidate_type IN ('graduate', 'experienced', 'both')",
    )
    op.create_check_constraint(
        "ck_user_profiles_graduation_year",
        "user_profiles",
        "graduation_year IS NULL OR (graduation_year >= 1900 AND graduation_year <= 2200)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_profiles_graduation_year", "user_profiles", type_="check"
    )
    op.drop_constraint(
        "ck_user_profiles_candidate_type", "user_profiles", type_="check"
    )
    op.drop_column("user_profiles", "graduation_year")
    op.drop_column("user_profiles", "candidate_type")
