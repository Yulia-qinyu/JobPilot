"""Safely reset the local Job workspace while preserving candidate knowledge."""

import argparse
import json
import os

from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db.session import SessionLocal
from app.services.job_workspace_reset import JobWorkspaceResetService

ALLOWED_ENVIRONMENTS = {"development", "local", "test"}
LOCAL_DATABASE_HOSTS = {None, "", "localhost", "127.0.0.1", "::1"}


def assert_local_reset_allowed(environment: str, database_url: str) -> None:
    normalized = environment.strip().lower()
    if normalized not in ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            "Refusing reset: set JOBPILOT_ENVIRONMENT to development, local, or test."
        )
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" and url.host not in LOCAL_DATABASE_HOSTS:
        raise RuntimeError("Refusing reset: database host is not local.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required to perform the deletion. Without it, only counts are printed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    environment = os.getenv("JOBPILOT_ENVIRONMENT", "")
    assert_local_reset_allowed(environment, settings.database_url)

    with SessionLocal.begin() as db:
        service = JobWorkspaceResetService(db)
        before_workspace = service.workspace_counts()
        before_candidate = service.candidate_counts()
        print(
            json.dumps(
                {
                    "mode": "preview" if not args.confirm else "confirmed_reset",
                    "job_workspace_before": before_workspace.as_dict(),
                    "candidate_knowledge_before": before_candidate.as_dict(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not args.confirm:
            print("No rows deleted. Re-run with --confirm to reset the local Job workspace.")
            return 2
        deleted = service.reset()
        after_workspace = service.workspace_counts()
        after_candidate = service.candidate_counts()
        if any(after_workspace.as_dict().values()):
            raise RuntimeError("Job workspace reset verification failed; transaction will roll back.")
        if after_candidate != before_candidate:
            raise RuntimeError("Candidate data changed unexpectedly; transaction will roll back.")
        print(
            json.dumps(
                {
                    "deleted": deleted.as_dict(),
                    "job_workspace_after": after_workspace.as_dict(),
                    "candidate_knowledge_after": after_candidate.as_dict(),
                    "candidate_knowledge_preserved": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
