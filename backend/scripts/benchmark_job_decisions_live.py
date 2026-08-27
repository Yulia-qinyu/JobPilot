"""Benchmark the current local PostgreSQL Phase 5 workload without Claude."""

import json
from statistics import quantiles
from time import perf_counter

from app.db.session import SessionLocal
from app.services.job_decision_service import JobDecisionService


def main() -> None:
    with SessionLocal() as db:
        service = JobDecisionService(db)
        recompute = service.recompute()
        latencies = []
        for index in range(40):
            started = perf_counter()
            service.repo.page(
                page=(index % 8) + 1,
                page_size=50,
                eligibility=None,
                role_family=None,
                role_fit=None,
                match_status=None,
                decision_value=None,
                company=None,
                source="bytedance",
                application_status=None,
                job_ids=None,
                sort="decision",
            )
            latencies.append((perf_counter() - started) * 1_000)
        print(
            json.dumps(
                {
                    "jobs": recompute.processed,
                    "recompute_seconds": recompute.elapsed_seconds,
                    "paginated_query_p95_ms": round(quantiles(latencies, n=20)[18], 3),
                    "claude_api_calls": 0,
                }
            )
        )


if __name__ == "__main__":
    main()
