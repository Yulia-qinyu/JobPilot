"""Backfill or refresh Phase 5 decisions without invoking Claude."""

import json

from app.db.session import SessionLocal
from app.services.job_decision_service import JobDecisionService


def main() -> None:
    with SessionLocal() as db:
        result = JobDecisionService(db).recompute()
        print(json.dumps(result.model_dump(), ensure_ascii=False))


if __name__ == "__main__":
    main()
