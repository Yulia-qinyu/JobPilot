"""Generate a deterministic Phase 7C.1 human-review artifact (zero Claude calls)."""

import hashlib
from pathlib import Path

from app.schemas.analysis import JDRequirements
from app.schemas.discovery import DiscoverySearchContext
from app.services.discovery_intent import DiscoveryIntentParser
from app.services.discovery_ranking import derive_search_relevance, extract_explicit_hard_signals
from app.services.discovery_tags import DiscoveryTagCatalog
from app.services.job_sources.base import ImportedJobDraft

INTENT_QUERIES = (
    "我想看看大模型平台方向",
    "多模态 AI 产品",
    "AIGC 内容产品经理",
    "ToB AI 产品经理",
    "增长产品经理 电商",
    "AI 产品，出海和电商都可以",
)
CLARIFICATION_QUERIES = (
    "帮我找 AI 工作",
    "北京 AI Agent 产品经理 大厂",
    "北京应届 AI 产品，不要运营",
    "腾讯北京产品",
)
RANKING_CASES = (
    ("AI Product Manager", "ai_product"),
    ("Agent 产品经理", "ai_product"),
    ("Senior Product Manager, Agent Platform", "general_product"),
    ("Engineering Manager, Agent Cloud Platform", "engineering"),
    ("AI Infrastructure Engineer, Agent Runtime", "engineering"),
    ("Applied AI Engineer", "engineering"),
)
HARD_SIGNAL_CASES = (
    ("True experience", "Candidates must have at least 6 years of product experience"),
    ("True education", "Bachelor's degree required"),
    (
        "Responsibility",
        "As a Production AI Ops Manager, you will design and develop production systems.",
    ),
    ("You will", "You will design and develop reliable AI services"),
)


def _draft(role: str, requirement: str) -> ImportedJobDraft:
    original = f"Build Agent products.\n{requirement}"
    return ImportedJobDraft(
        source="fixture",
        external_job_id=hashlib.sha256(role.encode()).hexdigest()[:10],
        external_job_code=None,
        company="Fixture Company",
        role=role,
        location="北京",
        recruitment_type="experienced",
        source_url="https://example.test/job",
        original_jd=original,
        structured_jd=JDRequirements(
            role=role,
            company="Fixture Company",
            location="北京",
            responsibilities=["Build Agent products."],
            required_skills=[requirement],
        ),
        published_date=None,
        source_metadata={},
        source_content_hash=hashlib.sha256(original.encode()).hexdigest(),
    )


def _context(parser: DiscoveryIntentParser, query: str) -> DiscoverySearchContext:
    parsed = parser.parse(query)
    return DiscoverySearchContext(
        session_id="phase7c1-eval",
        input_kind="natural_language",
        raw_input=query,
        explicit_constraints=parsed.constraints,
        include_terms=parsed.include_terms,
        exclusions=parsed.exclusions,
        freeform_terms=parsed.freeform_terms,
        selected_tag_ids=parsed.selected_tag_ids,
        ambiguities=parsed.ambiguities,
        clarification_required=bool(
            parsed.required_refinement_dimension_ids or parsed.required_refinement_groups
        ),
        created_at="2026-08-25T00:00:00Z",
        expires_at="2026-08-25T01:00:00Z",
    )


def render() -> str:
    parser = DiscoveryIntentParser()
    tags = DiscoveryTagCatalog()
    lines = [
        "# Phase 7C.1 Human Product Evaluation",
        "",
        "> Deterministic regression artifact. Claude calls: 0. Human labels are intentionally blank.",
        "",
        "## A. Intent Preservation",
        "",
        "| Raw Query | Parsed Role Family | Explicit Concepts Preserved | Required Clarification? | Optional Refinements | Intent Fully Preserved | Clarification Decision Correct |",
        "|---|---|---|---|---|---|---|",
    ]
    for query in INTENT_QUERIES:
        parsed = parser.parse(query)
        concepts = [tags.get(tag_id).label for tag_id in parsed.selected_tag_ids if tags.get(tag_id)]
        lines.append(
            f"| {query} | {', '.join(parsed.constraints.role_families) or '—'} | "
            f"{', '.join(concepts) or '—'} | "
            f"{'Yes' if parsed.required_refinement_dimension_ids else 'No'} | "
            f"{', '.join(parsed.optional_refinement_dimension_ids) or '—'} | Yes / Partial / No | Yes / No |"
        )
    lines.extend(
        [
            "",
            "## B. Clarification",
            "",
            "| Raw Query | Decision | Question / Tag Group | Clarification Decision Correct |",
            "|---|---|---|---|",
        ]
    )
    for query in CLARIFICATION_QUERIES:
        parsed = parser.parse(query)
        required = [
            *(group.id for group in parsed.required_refinement_groups),
            *parsed.required_refinement_dimension_ids,
        ]
        optional = [
            *(group.id for group in parsed.optional_refinement_groups),
            *parsed.optional_refinement_dimension_ids,
        ]
        decision = "Required" if required else "Optional" if optional else "Ready"
        offered = required or optional
        lines.append(f"| {query} | {decision} | {', '.join(offered) or '—'} | Yes / No |")
    lines.extend(
        [
            "",
            "## C. Ranking Regression — AI Agent 产品经理",
            "",
            "| Title | Classified Role Family | Relevance Band | Reason | Ranking Correct |",
            "|---|---|---|---|---|",
        ]
    )
    context = _context(parser, "AI Agent 产品经理")
    for title, family in RANKING_CASES:
        draft = _draft(title, "Agent product experience preferred")
        result = derive_search_relevance(context, draft, family, [])
        reason = " · ".join(item.label for item in result.reason_items)
        lines.append(f"| {title} | {family} | {result.relevance_band} | {reason} | Yes / No |")
    lines.extend(
        [
            "",
            "## D. Hard Signal Regression",
            "",
            "| Case | Source Text | Extracted Hard Signal | Hard Signal Decision Correct |",
            "|---|---|---|---|",
        ]
    )
    for label, requirement in HARD_SIGNAL_CASES:
        signals = extract_explicit_hard_signals(_draft("AI Product Manager", requirement))
        display = " · ".join(signal.display for signal in signals) or "None"
        lines.append(f"| {label} | {requirement} | {display} | Yes / No |")
    return "\n".join(lines) + "\n"


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "evals" / "phase7c1_human_evaluation.md"
    output.write_text(render(), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
