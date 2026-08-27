"""Live, ephemeral-only smoke test for ByteDance recruitment-channel planning."""

import json
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from time import perf_counter

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import Job, JobAnalysis
from app.services.discovery_service import DiscoveryService
from app.services.discovery_store import InMemoryDiscoverySessionStore
from app.services.job_import_runner import build_source_registry

QUERIES = (
    ("campus", "北京 应届 AI 产品经理 字节跳动"),
    ("experienced", "北京 社招 AI 产品经理 字节跳动"),
    ("unspecified", "北京 AI 产品经理 字节跳动"),
)


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = Settings(job_import_page_delay_seconds=0)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    registry = build_source_registry(settings)
    reports: list[dict[str, object]] = []
    try:
        with Session(engine) as db:
            for scenario, query in QUERIES:
                store = InMemoryDiscoverySessionStore(max_results=500)
                service = DiscoveryService(
                    db,
                    store,
                    registry,
                    settings=settings,
                )
                before = db.scalar(select(func.count(Job.id))) or 0
                session = service.create_session(query, False)
                started = perf_counter()
                service.search(session.id)
                duration = perf_counter() - started
                stored = store.get(session.id)
                after = db.scalar(select(func.count(Job.id))) or 0
                phase3 = db.scalar(select(func.count(JobAnalysis.id))) or 0
                channels = Counter(
                    result.normalized.recruitment_type or "unknown"
                    for result in stored.results
                )
                reports.append(
                    {
                        "scenario": scenario,
                        "query": query,
                        "selected_source_plans": session.selected_source_plans,
                        "state": stored.session.state,
                        "duration_seconds": round(duration, 3),
                        "temporary_results": len(stored.results),
                        "campus_count": channels["campus"],
                        "experienced_count": channels["experienced"],
                        "unknown_count": channels["unknown"],
                        "persistent_delta": after - before,
                        "claude_calls": stored.session.claude_api_calls,
                        "phase3_calls": phase3,
                        "source_progress": [
                            item.model_dump(mode="json")
                            for item in stored.session.source_progress
                        ],
                    }
                )
    finally:
        registry.close()
        engine.dispose()
    rendered = json.dumps(reports, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    safe = all(
        report["persistent_delta"] == 0
        and report["claude_calls"] == 0
        and report["phase3_calls"] == 0
        for report in reports
    )
    return 0 if safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
