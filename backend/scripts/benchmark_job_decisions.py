"""Local deterministic Phase 5 benchmark; never calls Claude."""

import json
from statistics import quantiles
from time import perf_counter

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Job
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.analysis import JDRequirements
from app.services.job_decision_service import JobDecisionService


def main() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        ProfileRepository(db).ensure_default_profile()
        structured = JDRequirements(
            role="AI 产品经理",
            responsibilities=["负责 AI 产品规划与交付"],
            required_skills=["本科及以上学历"],
        ).model_dump(mode="json")
        db.add_all(
            Job(
                user_profile_id=DEFAULT_PROFILE_ID,
                company=f"Company {index % 40}",
                role="AI 产品经理" if index % 3 else "后端工程师",
                location="北京",
                original_jd="Synthetic benchmark content",
                structured_jd=structured,
                status="Interested",
                source_content_hash=f"synthetic-{index}",
            )
            for index in range(2_000)
        )
        db.commit()
        started = perf_counter()
        result = JobDecisionService(db).recompute()
        recompute_seconds = perf_counter() - started
        latencies = []
        for page in range(1, 21):
            started = perf_counter()
            JobDecisionService(db).repo.page(
                page=page,
                page_size=50,
                eligibility=None,
                role_family=None,
                role_fit=None,
                match_status=None,
                decision_value=None,
                company=None,
                source=None,
                application_status=None,
                job_ids=None,
                sort="decision",
            )
            latencies.append((perf_counter() - started) * 1_000)
        print(
            json.dumps(
                {
                    "jobs": 2_000,
                    "recompute_seconds": round(recompute_seconds, 4),
                    "paginated_query_p95_ms": round(quantiles(latencies, n=20)[18], 3),
                    "claude_api_calls": result.claude_api_calls,
                }
            )
        )


if __name__ == "__main__":
    main()
