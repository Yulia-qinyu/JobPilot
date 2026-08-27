"""Backfill deterministic Target Role families and refresh Phase 5 decisions."""

import json

from app.db.session import SessionLocal
from app.services.job_decision_service import JobDecisionService
from app.services.profile_service import ProfileService


def main() -> None:
    with SessionLocal() as db:
        profile = ProfileService(db).recompute_target_role_families()
        decisions = JobDecisionService(db).recompute()
        print(
            json.dumps(
                {
                    "target_roles": [
                        {
                            "id": role.id,
                            "name": role.name,
                            "priority": role.priority,
                            "auto_role_family": role.auto_role_family,
                            "role_family_override": role.role_family_override,
                            "effective_role_family": role.effective_role_family,
                        }
                        for role in profile.target_roles
                    ],
                    "job_decisions": decisions.model_dump(),
                    "claude_api_calls": 0,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
