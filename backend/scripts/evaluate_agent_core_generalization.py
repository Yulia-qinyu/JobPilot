"""Generate the Phase 7 generalized Agent Core human-review worksheet."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.schemas.discovery import DiscoverySearchContext
from app.services.company_source_resolver import CompanySourceResolver
from app.services.discovery_intent import DiscoveryIntentParser
from app.services.job_sources.catalog import SourceCatalog

QUERIES = (
    "北京 AI Agent 产品经理",
    "北京 银行 应届 投资",
    "上海 数据分析 电商",
    "北京 战略咨询 应届",
    "深圳 大模型 算法",
    "北京 消费品 市场营销",
    "上海 风控 银行",
    "北京 产品运营 电商",
    "帮我找金融工作",
    "帮我找 AI 工作",
    "腾讯北京产品",
    "量化一级市场投资 北京",
    "我想做偏一级市场、科技方向的投资岗位",
    "上海 FinTech 产品经理",
    "北京 社招 AI 产品经理 字节跳动",
    "北京 校招 数据分析",
    "杭州 Developer Tools 产品经理",
    "深圳 AI 工程师 大模型",
    "北京 品牌营销 快消",
    "远程 Enterprise Agent 解决方案",
)


def _context(query: str, parser: DiscoveryIntentParser) -> tuple[object, DiscoverySearchContext]:
    parsed = parser.parse(query)
    now = datetime.now(UTC)
    return parsed, DiscoverySearchContext(
        session_id="evaluation",
        input_kind="natural_language",
        raw_input=query,
        explicit_constraints=parsed.constraints,
        include_terms=parsed.include_terms,
        exclusions=parsed.exclusions,
        freeform_terms=parsed.freeform_terms,
        explicit_concepts=parsed.explicit_concepts,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )


def main() -> None:
    parser = DiscoveryIntentParser()
    resolver = CompanySourceResolver(SourceCatalog())
    lines = [
        "# Phase 7 Agent Core Generalization — Human Evaluation",
        "",
        "> Human labels are intentionally blank. This artifact uses the offline deterministic path; partial coverage or high-impact semantic relations consume at most one semantic-planner call in a configured runtime.",
        "",
        "## A. Generalized Intent",
        "",
        "| # | Raw Query | Function | Industry | Domain | Location | Recruitment | Explicit Concepts | Method / Coverage | Required Clarification | Optional Refinement | Intent Correct | Question Useful | Options Useful |",
        "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for index, query in enumerate(QUERIES, 1):
        parsed, _ = _context(query, parser)
        constraints = parsed.constraints
        concepts = " · ".join(
            dict.fromkeys(item.raw_text for item in parsed.explicit_concepts)
        )
        required = " / ".join(
            group.label for group in parsed.required_refinement_groups
        ) or " / ".join(parsed.required_refinement_dimension_ids) or "—"
        optional = " / ".join(
            group.label for group in parsed.optional_refinement_groups
        ) or " / ".join(parsed.optional_refinement_dimension_ids) or "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    query,
                    ", ".join(constraints.job_functions) or "—",
                    ", ".join(constraints.industries) or "—",
                    ", ".join(constraints.domains) or "—",
                    ", ".join(constraints.locations) or "—",
                    ", ".join(constraints.recruitment_types) or "—",
                    concepts or "—",
                    f"{parsed.method} / {parsed.semantic_coverage_status}",
                    required,
                    optional,
                    "",
                    "",
                    "",
                ]
            )
            + " |"
        )

    source_queries = (
        ("No company", "北京 AI 产品经理"),
        ("One supported", "北京 AI 产品经理 字节跳动"),
        ("One unsupported", "北京 AI 产品经理 小米"),
        ("Multiple mixed", "北京 AI 产品经理 字节 小米 腾讯"),
        ("Campus", "北京 应届 AI 产品经理"),
        ("Experienced", "北京 社招 AI 产品经理"),
    )
    lines.extend(
        [
            "",
            "## B. Source Planning",
            "",
            "| Case | Query | Requested Companies | Selected Sources / Channels | Unsupported | Coverage | Message | Source Plan Correct |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for label, query in source_queries:
        _, context = _context(query, parser)
        plan = resolver.plan(context)
        selected = ", ".join(
            f"{item.company_name}/{item.channel}" for item in plan.selected_sources
        ) or "—"
        lines.append(
            f"| {label} | {query} | {', '.join(plan.requested_companies) or '—'} | "
            f"{selected} | {', '.join(plan.unsupported_companies) or '—'} | "
            f"{plan.coverage_status} | {plan.coverage_message} |  |"
        )

    lines.extend(
        [
            "",
            "## C. Claude Budget",
            "",
            "- Deterministically covered query: **0 calls**",
            "- Semantic coverage partial/high-impact relation: **at most 1 call**",
            "- Clarification/refinement click: **0 calls**",
            "- Source planning, acquisition, ranking, personalization: **0 calls**",
            "- Session hard max: **1 intent call**",
            "",
            "Human notes:",
            "",
            "- 0-call cases correct:",
            "- 1-call cases justified:",
            "- Hard max respected:",
        ]
    )
    destination = Path(__file__).resolve().parents[1] / "evals" / "phase7_agent_core_generalization_human_evaluation.md"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
