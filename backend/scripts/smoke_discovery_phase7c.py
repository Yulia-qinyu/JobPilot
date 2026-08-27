import json
from pathlib import Path
from time import perf_counter

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import Base
from app.db.models import Job, JobAnalysis
from app.schemas.discovery import DiscoveryContextUpdate
from app.services.discovery_intent import DiscoveryIntentParser
from app.services.discovery_service import DiscoveryService
from app.services.discovery_store import InMemoryDiscoverySessionStore
from app.services.discovery_tags import DiscoveryTagCatalog
from app.services.job_import_runner import build_source_registry

QUERIES = [
    "北京 AI 产品经理",
    "北京 AI Agent 产品经理 大厂",
    "上海 FinTech 产品经理",
    "北京应届 AI 产品，不要运营",
    "AI 产品，出海和电商都可以",
    "不看高级和资深岗的 AI 产品经理",
    "腾讯北京产品",
    "帮我找 AI 工作",
    "我想看看大模型平台方向",
    "AI 平台产品经理",
    "数据产品经理 上海",
    "策略产品经理 北京",
    "增长产品经理 电商",
    "AI 评测产品经理",
    "多模态 AI 产品",
    "AIGC 内容产品经理",
    "ToB AI 产品经理",
    "AI 产品经理，不要解决方案",
    "校招 Agent 产品",
    "社招 AI Product Manager",
]


def main() -> None:
    settings = get_settings()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    store = InMemoryDiscoverySessionStore(max_results=500)
    registry = build_source_registry(settings, include_greenhouse=True)
    parser = DiscoveryIntentParser()
    tags = DiscoveryTagCatalog()
    try:
        with Session(engine, expire_on_commit=False) as db:
            service = DiscoveryService(db, store, registry, settings=settings, intent_parser=parser)
            before = db.scalar(select(func.count(Job.id))) or 0
            live_query = "AI Agent 产品经理"
            session = service.create_session(live_query, False)
            if session.state == "NeedsRefinement":
                session = service.update_context(
                    session.id, DiscoveryContextUpdate(skip_refinement=True)
                )
            started = perf_counter()
            service.search(session.id)
            duration = perf_counter() - started
            state = service.get_session(session.id)
            after_search = db.scalar(select(func.count(Job.id))) or 0
            all_results = []
            for page_number in range(1, 6):
                page = service.result_page(
                    session.id,
                    page=page_number,
                    page_size=100,
                    location=None,
                    company=None,
                    role_family=None,
                    relevance=None,
                    already_in_my_jobs=None,
                    source=None,
                    sort="relevance",
                    include_excluded=True,
                )
                all_results.extend(page.items)
                if page_number >= page.total_pages:
                    break
            greenhouse = next(
                (item for item in all_results if item.identity.provider == "greenhouse"), None
            )
            if greenhouse is None:
                diagnostics = {
                    "source_progress": [
                        item.model_dump(mode="json") for item in state.source_progress
                    ],
                    "source_failures": state.source_failures,
                    "providers": sorted({item.identity.provider for item in all_results}),
                    "total_pages": page.total_pages,
                }
                raise RuntimeError(
                    f"Live multi-source smoke returned no Greenhouse result: {diagnostics}"
                )
            add_started = perf_counter()
            added = service.add_to_my_jobs(session.id, greenhouse.result_id)
            add_duration = perf_counter() - add_started
            after_add = db.scalar(select(func.count(Job.id))) or 0
            repeated = service.add_to_my_jobs(session.id, greenhouse.result_id)
            after_repeat = db.scalar(select(func.count(Job.id))) or 0
            phase3_rows = db.scalar(select(func.count(JobAnalysis.id))) or 0
            metrics = {
                "query": live_query,
                "intent_parsing_method": state.search_context.parsing_method,
                "claude_calls": state.claude_api_calls,
                "selected_sources": state.selected_sources,
                "source_progress": [item.model_dump(mode="json") for item in state.source_progress],
                "session_state": state.state,
                "search_duration_seconds": round(duration, 3),
                "temporary_results": state.result_count,
                "duplicate_count": state.duplicate_count,
                "persistent_before": before,
                "persistent_after_search": after_search,
                "search_persistent_delta": after_search - before,
                "add_outcome": added.outcome,
                "add_duration_seconds": round(add_duration, 3),
                "persistent_after_add": after_add,
                "add_persistent_delta": after_add - after_search,
                "repeat_add_outcome": repeated.outcome,
                "persistent_after_repeat": after_repeat,
                "phase3_calls": 0,
                "phase3_rows": phase3_rows,
            }
            artifact = Path(__file__).resolve().parents[1] / "evals" / "phase7c_human_evaluation.md"
            artifact.write_text(
                render_artifact(metrics, parser, tags, sample_results(all_results)),
                encoding="utf-8",
            )
            metrics["artifact"] = str(artifact)
            print(json.dumps(metrics, ensure_ascii=False))
    finally:
        registry.close()


def render_artifact(metrics: dict, parser, tags, results) -> str:
    lines = [
        "# Phase 7C Human Product Evaluation",
        "",
        "## A. Query Understanding",
        "",
        "| Raw Query | Parsed Constraints | Method | Clarification | Tags Offered | Intent Correct | Clarification Useful | Tags Useful |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for query in QUERIES:
        parsed = parser.parse(query)
        constraints = parsed.constraints.model_dump(mode="json")
        offered = [
            tag.label
            for group in tags.groups()
            if group.id in parsed.refinement_dimension_ids
            for tag in group.tags
        ]
        lines.append(
            f"| {query} | `{json.dumps(constraints, ensure_ascii=False)}` | "
            f"{parsed.method.title()} | {'Yes' if parsed.refinement_dimension_ids else 'No'} | "
            f"{', '.join(offered) or '—'} | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |"
        )
    lines.extend(
        [
            "",
            "## B. Discovery Results",
            "",
            "| Source | Company | Title | Location | Role Family | Relevance | Matched Reasons | Hard Signals | Excluded | Relevant | Ranking | Explanation |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in results:
        matched = (
            " · ".join(
                reason.label
                for reason in item.search_derived.reason_items
                if reason.kind == "matched"
            )
            or "—"
        )
        hard = (
            " · ".join(
                signal.display for signal in item.deterministic_derived.explicit_hard_signals
            )
            or "—"
        )
        lines.append(
            f"| {item.identity.source} | {item.normalized.company} | {item.normalized.role} | "
            f"{item.normalized.location or '—'} | {item.deterministic_derived.role_family} | "
            f"{item.search_derived.relevance_band} | {matched} | {hard} | "
            f"{'Yes' if item.search_derived.excluded_by_current_search else 'No'} | "
            "Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |"
        )
    lines.extend(
        [
            "",
            "## C. Multi-source",
            "",
            "```json",
            json.dumps(
                {
                    key: metrics[key]
                    for key in (
                        "selected_sources",
                        "source_progress",
                        "duplicate_count",
                        "session_state",
                    )
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
            "## D. Persistence",
            "",
            "```json",
            json.dumps(
                {
                    key: metrics[key]
                    for key in (
                        "persistent_before",
                        "persistent_after_search",
                        "persistent_after_add",
                        "persistent_after_repeat",
                        "add_outcome",
                        "repeat_add_outcome",
                        "claude_calls",
                        "phase3_calls",
                    )
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
            "## Human Summary",
            "",
            "- Intent Constraint Accuracy:",
            "- Unnecessary Clarification Rate:",
            "- Clarification Usefulness:",
            "- Tag Usefulness:",
            "- Source Routing Accuracy:",
            "- Discovery Precision@10:",
            "- Discovery Precision@20:",
            "- Exclusion Precision:",
            "- Incorrect Hard Exclusion Count:",
            "- Explanation Quality:",
            "",
            "> Human labels are intentionally blank. No Claude evaluation was used.",
        ]
    )
    return "\n".join(lines) + "\n"


def sample_results(results):
    by_provider = {}
    for item in results:
        by_provider.setdefault(item.identity.provider, []).append(item)
    sample = []
    for items in by_provider.values():
        sample.extend(items[:15])
    return sample[:30]


if __name__ == "__main__":
    main()
