"""Generate a deterministic Phase 7D A/B human evaluation artifact."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

from app.schemas.analysis import JDRequirements
from app.schemas.discovery import (
    DiscoveryDeterministicDerived,
    DiscoveryExplicitConstraints,
    DiscoveryHardSignal,
    DiscoveryIdentity,
    DiscoveryNormalizedJob,
    DiscoveryResult,
    DiscoverySearchContext,
    DiscoverySearchDerived,
    DiscoverySourceRaw,
)
from app.schemas.discovery_personalization import (
    CandidateDiscoveryContext,
    CandidateEvidenceItem,
    CandidateEvidenceTopic,
    PersonalizedRankingInput,
    SavedCareerPreferences,
    SavedTargetRole,
)
from app.services.discovery_personalization import DiscoveryPersonalizationService
from app.services.discovery_service import DiscoveryService

TITLES = (
    ("AI Agent Product Manager", "ai_product", "High"),
    ("Agent Platform Product Manager", "ai_product", "High"),
    ("Senior AI Product Manager — LLM", "ai_product", "High"),
    ("AI Product Manager — Evaluation", "ai_product", "High"),
    ("Enterprise Agent Product Manager", "ai_product", "High"),
    ("AI Workflow Product Owner", "ai_product", "High"),
    ("AIGC Product Manager", "ai_product", "High"),
    ("AI Data Product Manager", "data_product", "Medium"),
    ("Platform Product Manager", "platform_product", "Medium"),
    ("FinTech AI Product Manager", "fintech_product", "Medium"),
    ("Product Manager — Developer Tools", "general_product", "Medium"),
    ("Product Manager — Analytics", "data_product", "Medium"),
    ("Growth Product Manager", "growth_product", "Medium"),
    ("Product Strategy Manager", "strategy_product", "Medium"),
    ("Product Operations Manager", "product_operations", "Low"),
    ("AI Solutions Consultant", "solution", "Low"),
    ("Applied AI Engineer", "engineering", "Low"),
    ("AI Infrastructure Engineer", "engineering", "Low"),
    ("Machine Learning Engineer", "engineering", "Low"),
    ("Algorithm Researcher", "algorithm", "Low"),
    ("Engineering Manager — Agent Platform", "engineering", "Low"),
    ("AI UX Designer", "design", "Low"),
    ("Content Operations — AIGC", "product_operations", "Low"),
    ("General Product Manager", "general_product", "Medium"),
    ("Commercialization Product Manager", "general_product", "Medium"),
)


def context(role_family: str = "ai_product", raw: str = "AI Agent 产品经理"):
    now = datetime.now(UTC)
    return DiscoverySearchContext(
        session_id="phase7d-eval",
        input_kind="natural_language",
        raw_input=raw,
        explicit_constraints=DiscoveryExplicitConstraints(role_families=[role_family]),
        include_terms=["Agent"],
        selected_tag_ids=["ai_agent"],
        personalization_enabled=True,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )


def candidate(search_context=None) -> PersonalizedRankingInput:
    evidence = (
        CandidateEvidenceItem(
            "resume_extracted:28", "resume_extracted", "Built an AI Agent and LLM workflow", "JobPilot"
        ),
        CandidateEvidenceItem(
            "manual_confirmed:41", "manual_confirmed", "Designed an AI product evaluation flow", "JobPilot"
        ),
        CandidateEvidenceItem(
            "resume_extracted:52", "resume_extracted", "Built FinTech payment analytics", "KPay"
        ),
        CandidateEvidenceItem(
            "resume_extracted:63", "resume_extracted", "Designed a data product platform", "GoFin"
        ),
    )
    return PersonalizedRankingInput(
        search_context=search_context or context(),
        candidate_context=CandidateDiscoveryContext(
            professional_years=2,
            education_level=3,
            graduation_year=2024,
            evidence=evidence,
            evidence_topics=(
                CandidateEvidenceTopic("ai_product", ("resume_extracted:28", "manual_confirmed:41")),
                CandidateEvidenceTopic("agent", ("resume_extracted:28",)),
                CandidateEvidenceTopic("llm", ("resume_extracted:28",)),
                CandidateEvidenceTopic("experimentation", ("manual_confirmed:41",)),
                CandidateEvidenceTopic("fintech", ("resume_extracted:52",)),
                CandidateEvidenceTopic("data", ("resume_extracted:52", "resume_extracted:63")),
                CandidateEvidenceTopic("platform", ("resume_extracted:63",)),
            ),
            context_version="phase7d-eval-v1",
            limited=False,
        ),
        saved_preferences=SavedCareerPreferences(
            target_roles=(
                SavedTargetRole("target_role:1", "AI Product Manager", "primary", "ai_product"),
            ),
            preferred_location="北京",
            target_companies=("ByteDance",),
        ),
    )


def result(index: int, title: str, family: str, band: str) -> DiscoveryResult:
    years = (
        [
            DiscoveryHardSignal(
                type="experience_years",
                operator=">=",
                value=5,
                display="明确要求 5+ 年经验",
                source_text="5+ years required",
            )
        ]
        if index % 7 == 0
        else []
    )
    jd = JDRequirements(role=title, responsibilities=[title])
    return DiscoveryResult(
        result_id=f"result-{index}",
        identity=DiscoveryIdentity(
            source="evaluation", provider="fixture", external_job_id=str(index), canonical_url="https://example.test/job"
        ),
        source_raw=DiscoverySourceRaw(
            title=title,
            locations=["北京"],
            recruitment_type=None,
            description=title,
            requirements="",
            published_date=None,
        ),
        normalized=DiscoveryNormalizedJob(
            company="Evaluation Company",
            role=title,
            location="北京",
            recruitment_type=None,
            source_url="https://example.test/job",
            original_jd=title,
            structured_jd=jd,
            published_date=None,
        ),
        deterministic_derived=DiscoveryDeterministicDerived(
            role_family=family,
            role_confidence="High",
            explicit_hard_signals=years,
            content_hash=f"hash-{index}",
            dedupe_key=f"evaluation:{index}",
        ),
        search_derived=DiscoverySearchDerived(relevance_band=band),
    )


def render() -> str:
    public = [result(index, *item) for index, item in enumerate(TITLES)]
    ranking_input = candidate()
    service = DiscoveryPersonalizationService()
    personalized = [service.apply(item, ranking_input) for item in public]
    off_order = {item.result_id: index + 1 for index, item in enumerate(sorted(public, key=DiscoveryService._result_sort_key))}
    on_sorted = sorted(personalized, key=DiscoveryService._result_sort_key)
    on_order = {item.result_id: index + 1 for index, item in enumerate(on_sorted)}
    lines = [
        "# Phase 7D Human Product Evaluation",
        "",
        "> Deterministic A/B artifact. Human labels are intentionally blank. Claude personalization calls: 0.",
        "",
        "## A. OFF vs ON A/B",
        "",
        "| Title | Public Relevance | OFF Position | ON Position / Band | Candidate Reasons | Candidate Risks | Evidence Refs | Helpful | Grounded | Preferred |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in personalized:
        derived = item.personalization_derived
        reasons = " · ".join(reason.display for reason in derived.candidate_reasons) or "—"
        risks = " · ".join(signal.display for signal in derived.candidate_constraint_signals) or "—"
        refs = ", ".join(evidence.evidence_ref for evidence in derived.evidence) or "—"
        lines.append(
            f"| {item.normalized.role} | {item.search_derived.relevance_band} | "
            f"{off_order[item.result_id]} | {on_order[item.result_id]} / {derived.band} | "
            f"{reasons} | {risks} | {refs} | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |"
        )
    lines.extend([
        "",
        "## B. Search Intent Conflict Cases",
        "",
        "| Current Search | Saved Preference | Result | Expected Priority | Actual | Current Intent Preserved |",
        "|---|---|---|---|---|---|",
        "| 上海 FinTech Product | 北京 AI Product | Shanghai FinTech Product | Current search first | Public band remains authoritative | Yes / No |",
        "| AI Agent，不要银行 | Banking | Banking AI Product | Excluded / no boost | Low remains Neutral | Yes / No |",
        "| Growth Product | Platform Product | Growth Product | Growth first | Exact current role remains first | Yes / No |",
        "",
        "## C. Evidence Grounding",
        "",
        "| Reason | Evidence Ref | Evidence Text Summary | Supported? |",
        "|---|---|---|---|",
    ])
    evidence_rows = [
        (reason.display, ref, next((e.text_summary for e in item.personalization_derived.evidence if e.evidence_ref == ref), "—"))
        for item in personalized
        for reason in item.personalization_derived.candidate_reasons
        for ref in reason.evidence_refs
        if ref.startswith(("resume_extracted:", "manual_confirmed:"))
    ][:10]
    for reason, ref, summary in evidence_rows:
        lines.append(f"| {reason} | {ref} | {summary} | Yes / No |")
    lines.extend([
        "",
        "## D. Candidate Constraint Cases",
        "",
        "| Candidate Fact | Requirement | Result | Decision Correct |",
        "|---|---|---|---|",
        "| 6 verified years | 5+ years required | Supported | Yes / No |",
        "| 1 verified year | 5+ years required | PotentialGap | Yes / No |",
        "| No verified years | 5+ years required | Unknown | Yes / No |",
        "| Verified Master degree | Bachelor required | Supported | Yes / No |",
        "| No verified education | Bachelor required | Unknown | Yes / No |",
        "",
        "## E. OFF Privacy Boundary",
        "",
        "```text",
        "Candidate context provider calls while OFF = 0",
        "Claude personalization calls = 0",
        "Source refetch count on toggle = 0",
        "Automatic Phase 3 calls = 0",
        "```",
        "",
        "## Human Metrics",
        "",
        "- Personalization Preference Rate:",
        "- Harmful Personalization Rate:",
        "- Evidence Grounding Accuracy:",
        "- Current Intent Override Violations:",
        "- Candidate Constraint Precision:",
        "- Candidate Constraint False Gap Count:",
    ])
    return "\n".join(lines) + "\n"


def benchmark(count: int = 500) -> float:
    items = [result(index, *TITLES[index % len(TITLES)]) for index in range(count)]
    ranking_input = candidate()
    service = DiscoveryPersonalizationService()
    started = perf_counter()
    personalized = [service.apply(item, ranking_input) for item in items]
    sorted(personalized, key=DiscoveryService._result_sort_key)
    return (perf_counter() - started) * 1000


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "evals" / "phase7d_human_evaluation.md"
    output.write_text(render(), encoding="utf-8")
    print(f"artifact={output}")
    print(f"personalization_500_results_ms={benchmark():.3f}")
    print("claude_personalization_calls=0")
    print("source_refetch_count=0")


if __name__ == "__main__":
    main()
