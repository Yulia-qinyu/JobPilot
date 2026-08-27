"""Run the real Phase 7A/B ByteDance discovery flow in an isolated database."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.models import Job, JobAnalysis
from app.services.discovery_service import DiscoveryService
from app.services.discovery_store import InMemoryDiscoverySessionStore
from app.services.job_sources.bytedance import ByteDanceJobSource
from app.services.job_sources.registry import JobSourceRegistry


class CountingByteDanceJobSource(ByteDanceJobSource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages_requested = 0

    def discover(self, query):
        for page in super().discover(query):
            self.pages_requested += 1
            yield page


def render_artifact(metrics: dict, samples: list[dict]) -> str:
    lines = [
        "# Phase 7A + 7B Human Product Evaluation",
        "",
        "## Discover Experience",
        "",
        "- Landing: `今天你想搜索什么机会？` with a ByteDance search URL input.",
        "- Personalization: visibly OFF; Candidate Profile is not read.",
        "- Progress: Ready → Searching → Completed/Partial/Failed with counts and expiry.",
        "- Results: temporary cards with deterministic filters, Why this job, and explicit Add to My Jobs.",
        "- My Jobs: existing persistent Decision Center; no temporary result appears there before Add.",
        "",
        "## Live Persistence Test",
        "",
        "```json",
        json.dumps(metrics, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Temporary Result Sample",
        "",
        "| External ID | Title | Company | Location | Role Family | Relevance | Why This Job | Already in My Jobs | Relevant | Explanation | Would Add |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in samples:
        why = "；".join(item["why"]).replace("|", "/")
        title = item["title"].replace("|", "/")
        lines.append(
            f"| {item['external_id']} | {title} | {item['company']} | {item['location']} | "
            f"{item['role_family']} | {item['relevance']} | {why} | "
            f"{item['already']} | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |"
        )
    lines.extend(
        [
            "",
            "## UX Review",
            "",
            "- Discover clarity:",
            "- My Jobs distinction:",
            "- Why-this-job usefulness:",
            "- Filter usefulness:",
            "- Add-to-My-Jobs clarity:",
            "",
            "> Human labels are intentionally blank. No Claude evaluation was used.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "search_url",
        nargs="?",
        default=(
            "https://jobs.bytedance.com/experienced/position?"
            "keywords=AI%20Product%20Manager&location=CT_11"
        ),
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[1] / "evals/phase7ab_human_evaluation.md"),
        help="Human-evaluation artifact path; use a temporary path for isolated smoke runs.",
    )
    args = parser.parse_args()
    db_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(db_engine)
    settings = get_settings()
    adapter = CountingByteDanceJobSource(settings)
    registry = JobSourceRegistry([adapter])
    store = InMemoryDiscoverySessionStore(ttl_minutes=60, max_sessions=20, max_results=500)
    try:
        with Session(db_engine, expire_on_commit=False) as db:
            service = DiscoveryService(db, store, registry)
            before = int(db.scalar(select(func.count(Job.id))) or 0)
            session = service.create_session(args.search_url, False)
            search_started = perf_counter()
            service.search(session.id)
            search_seconds = round(perf_counter() - search_started, 3)
            state = service.get_session(session.id)
            after_search = int(db.scalar(select(func.count(Job.id))) or 0)
            page = service.result_page(
                session.id,
                page=1,
                page_size=25,
                location=None,
                company=None,
                role_family=None,
                relevance=None,
                already_in_my_jobs=None,
                source=None,
                sort="relevance",
            )
            add_started = perf_counter()
            added = service.add_to_my_jobs(session.id, page.items[0].result_id)
            add_seconds = round(perf_counter() - add_started, 3)
            after_add = int(db.scalar(select(func.count(Job.id))) or 0)
            repeated = service.add_to_my_jobs(session.id, page.items[0].result_id)
            after_repeat = int(db.scalar(select(func.count(Job.id))) or 0)
            detail_accessible = service.jobs.get(added.persistent_job_id) is not None
            metrics = {
                "search_url": state.search_context.raw_input,
                "state": state.state,
                "pages_requested": adapter.pages_requested,
                "jobs_discovered": state.discovered_count,
                "temporary_results": state.result_count,
                "search_duration_seconds": search_seconds,
                "persistent_jobs_before": before,
                "persistent_jobs_after_search": after_search,
                "search_persistent_delta": after_search - before,
                "add_outcome": added.outcome,
                "add_duration_seconds": add_seconds,
                "persistent_jobs_after_add": after_add,
                "add_persistent_delta": after_add - after_search,
                "repeat_add_outcome": repeated.outcome,
                "persistent_jobs_after_repeat": after_repeat,
                "job_detail_accessible": detail_accessible,
                "phase3_rows": int(db.scalar(select(func.count(JobAnalysis.id))) or 0),
                "phase3_calls": 0,
                "claude_calls": 0,
            }
            samples = [
                {
                    "external_id": item.identity.external_job_id,
                    "title": item.normalized.role,
                    "company": item.normalized.company,
                    "location": item.normalized.location or "未注明",
                    "role_family": item.deterministic_derived.role_family,
                    "relevance": item.search_derived.relevance_band,
                    "why": item.search_derived.reasons,
                    "already": "Yes" if item.in_my_jobs else "No",
                }
                for item in page.items[:20]
            ]
            output = Path(args.output)
            output.write_text(render_artifact(metrics, samples), encoding="utf-8")
            print(json.dumps({**metrics, "artifact": str(output)}, ensure_ascii=False))
    finally:
        registry.close()


if __name__ == "__main__":
    main()
