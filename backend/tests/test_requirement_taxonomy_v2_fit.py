"""Phase 8C — V2 taxonomy boundary inside the fit-analysis chain.

Covers the parts of the acceptance matrix that are not exercised by the pure
parser tests in test_requirement_taxonomy_v2.py: matcher input filtering, Match
Score exclusion, zero-matchable behaviour, and per-requirement eligibility.
"""

from unittest.mock import Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import (
    Education,
    JDRequirements,
    ResumeProfile,
    StructuredRequirement,
    WorkExperience,
)
from app.schemas.fit_analysis import FitAnalysisOutput, RequirementMatchOutput
from app.schemas.job import JobCreate
from app.services.eligibility_service import EligibilityService
from app.services.evidence_catalog import EvidenceCatalogBuilder
from app.services.fit_analysis_service import (
    FitAnalysisNormalizationError,
    FitAnalysisService,
)
from app.services.job_service import JobService
from app.services.matcher_client import active_matcher_model
from app.services.profile_service import ProfileService
from app.services.requirement_catalog import RequirementCatalogBuilder
from app.services.requirement_matcher import RequirementMatcher


def _requirement(
    source_text: str,
    normalized: str,
    requirement_type: str,
    *,
    importance: str = "Important",
    eligibility_category: str | None = None,
    knowledge_topics: list[str] | None = None,
    source_section: str = "requirements",
) -> StructuredRequirement:
    return StructuredRequirement(
        requirement_id=RequirementCatalogBuilder.stable_requirement_id(
            source_text=source_text,
            normalized_requirement=normalized,
            requirement_type=requirement_type,
            source_section=source_section,
        ),
        source_text=source_text,
        normalized_requirement=normalized,
        source_section=source_section,
        requirement_type=requirement_type,
        importance=importance,
        eligibility_category=eligibility_category,
        knowledge_topics=knowledge_topics or [],
    )


def _v2_jd(*requirements: StructuredRequirement) -> JDRequirements:
    return JDRequirements(
        role="AI Product Manager",
        requirement_taxonomy_version="v2",
        requirements=list(requirements),
    )


def _setup(structured_jd: JDRequirements) -> tuple[Session, int, Mock]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    ProfileService(db).replace_resume(
        "master.docx",
        "sensitive full resume",
        ResumeProfile(
            skills=["LLM", "SQL"],
            work_experience=[
                WorkExperience(
                    company="Acme", title="PM", highlights=["Shipped an SQL analytics dashboard."]
                )
            ],
        ),
    )
    job = JobService(db, Settings()).create(
        JobCreate(
            company="Example AI",
            role="AI Product Manager",
            original_jd="A sufficiently long fictional job description for an AI Product Manager role.",
            structured_jd=structured_jd,
        )
    )
    matcher = Mock()
    matcher.client.model = active_matcher_model(Settings())
    matcher.PROMPT_VERSION = RequirementMatcher.PROMPT_VERSION
    matcher.SCHEMA_VERSION = RequirementMatcher.SCHEMA_VERSION
    return db, job.id, matcher


def _profile_with_education(*, field: str, degree: str | None = "学士"):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    ProfileService(db).replace_resume(
        "master.docx",
        "verified education resume",
        ResumeProfile(
            education=[
                Education(
                    institution="Example University",
                    degree=degree,
                    field=field,
                    period="2023–2027",
                )
            ]
        ),
    )
    return db, ProfileRepository(db).get_full_profile()


def _evaluate_education_requirement(
    *, field: str, source_text: str, normalized: str, category: str, degree: str | None = "学士"
):
    db, profile = _profile_with_education(field=field, degree=degree)
    requirement = _requirement(
        source_text,
        normalized,
        "eligibility",
        importance="Critical",
        eligibility_category=category,
    )
    result = EligibilityService().evaluate_requirements(profile, _v2_jd(requirement))[0]
    db.close()
    return result


def test_artificial_intelligence_major_supports_computer_related_requirement() -> None:
    # Compatibility case: historical parser output misclassified this as degree.
    result = _evaluate_education_requirement(
        field="Artificial Intelligence",
        source_text="统计学/数学/计算机相关专业优先",
        normalized="统计学、数学或计算机相关专业背景",
        category="degree",
    )

    assert result.status == "Supported"
    assert result.evidence_ids
    assert "专业" in result.reason
    assert "学历层级" not in result.reason


def test_computer_science_major_supports_computer_related_requirement() -> None:
    result = _evaluate_education_requirement(
        field="Computer Science",
        source_text="计算机相关专业背景",
        normalized="计算机相关专业背景",
        category="education_field",
    )

    assert result.status == "Supported"
    assert "计算机相关" in result.reason


def test_unrelated_major_is_not_automatically_supported() -> None:
    result = _evaluate_education_requirement(
        field="History",
        source_text="计算机相关专业背景",
        normalized="计算机相关专业背景",
        category="education_field",
    )

    assert result.status == "Unknown"
    assert "专业" in result.reason
    assert "学历层级" not in result.reason


def test_degree_level_is_evaluated_independently_from_major() -> None:
    degree_result = _evaluate_education_requirement(
        field="History",
        source_text="本科及以上学历",
        normalized="本科及以上学历",
        category="degree",
    )
    major_result = _evaluate_education_requirement(
        field="人工智能",
        degree=None,
        source_text="计算机相关专业背景",
        normalized="计算机相关专业背景",
        category="education_field",
    )

    assert degree_result.status == "Supported"
    assert "学历门槛" in degree_result.reason
    assert major_result.status == "Supported"
    assert "专业" in major_result.reason


def test_knowledge_only_v2_job_is_unscorable_and_skips_the_matcher(caplog) -> None:
    jd = _v2_jd(
        _requirement(
            "深入理解 LLM、Agent、RAG 原理及能力边界",
            "理解 LLM、Agent、RAG 原理及能力边界",
            "knowledge",
            knowledge_topics=["LLM 原理", "Agent 架构", "RAG 原理"],
        ),
    )
    db, job_id, matcher = _setup(jd)

    with caplog.at_level("INFO"):
        result = FitAnalysisService(db, Settings()).analyze(job_id, matcher)

    matcher.analyze.assert_not_called()
    analysis = result.analysis
    assert analysis is not None
    assert analysis.match_score is None
    assert analysis.score_status == "unavailable_no_matchable_requirements"
    assert analysis.recommendation is None
    assert analysis.requirement_matches == []
    assert analysis.strengths == []
    assert analysis.gaps == []
    assert [item.requirement_text for item in analysis.knowledge_requirements] == [
        "理解 LLM、Agent、RAG 原理及能力边界"
    ]
    assert analysis.score_basis.included_requirement_ids == []
    assert analysis.score_basis.excluded_knowledge_count == 1
    assert "claude_api_calls=0" in caplog.text
    assert "sensitive full resume" not in caplog.text

    # Persisted state re-reads without another matcher call and stays unscorable.
    reloaded = FitAnalysisService(db, Settings()).get_state(job_id)
    matcher.analyze.assert_not_called()
    assert reloaded.analysis is not None
    assert reloaded.analysis.match_score is None
    assert reloaded.analysis.score_status == "unavailable_no_matchable_requirements"
    assert JobService(db, Settings()).get(job_id).match_score is None


def test_mixed_v2_job_sends_only_matchable_to_matcher_and_excludes_the_rest() -> None:
    matchable = _requirement("熟练使用 SQL", "熟练使用 SQL", "matchable", importance="Critical")
    knowledge = _requirement(
        "理解 RAG 原理", "理解 RAG 原理", "knowledge", knowledge_topics=["RAG 原理"]
    )
    eligibility = _requirement(
        "3年以上 AI 产品经验",
        "3年以上 AI 产品经验",
        "eligibility",
        importance="Critical",
        eligibility_category="experience_years",
    )
    db, job_id, matcher = _setup(_v2_jd(matchable, knowledge, eligibility))

    # The catalog sent to the matcher carries exactly the matchable requirement,
    # keyed by the SAME canonical reqv2_ id stored on the structured JD.
    sent_catalog = RequirementCatalogBuilder().build(
        JobService(db, Settings()).get(job_id).structured_jd
    )
    assert [item.requirement_id for item in sent_catalog.requirements] == [
        matchable.requirement_id
    ]
    catalog_id = sent_catalog.requirements[0].requirement_id
    assert catalog_id == matchable.requirement_id
    assert catalog_id.startswith("reqv2_")

    evidence = EvidenceCatalogBuilder().build(ProfileRepository(db).get_full_profile())
    evidence_id = next(iter(evidence.by_catalog_id))
    matcher.analyze.return_value = FitAnalysisOutput(
        summary="候选人具备直接 SQL 证据。",
        requirement_matches=[
            RequirementMatchOutput(
                requirement_id=catalog_id,
                importance="Critical",
                is_hard_requirement=False,
                hard_requirement_category="none",
                match_status="Strong",
                reason="有直接的 SQL 数据分析交付证据。",
                confidence="High",
                evidence_source_ids=[evidence_id],
            )
        ],
        suggested_preparation=[],
    )

    result = FitAnalysisService(db, Settings()).analyze(job_id, matcher)

    assert matcher.analyze.call_count == 1
    matcher_catalog = matcher.analyze.call_args.args[0]
    assert [item.text for item in matcher_catalog.requirements] == ["熟练使用 SQL"]

    analysis = result.analysis
    assert analysis is not None
    # Only the matchable requirement contributes to the deterministic score.
    assert analysis.match_score == 100
    assert analysis.score_status == "available"
    assert [item.requirement_id for item in analysis.requirement_matches] == [catalog_id]
    assert analysis.score_basis.included_requirement_ids == [catalog_id]
    assert analysis.score_basis.excluded_knowledge_count == 1
    assert analysis.score_basis.excluded_eligibility_count == 1

    # Knowledge surfaces separately; it is never a strength or a gap.
    assert [item.requirement_text for item in analysis.knowledge_requirements] == [
        "理解 RAG 原理"
    ]
    assert all(
        "RAG" not in gap.requirement for gap in analysis.gaps
    )

    # Missing evidence for an explicit duration gate is Unknown, not PotentialGap.
    assert len(analysis.eligibility_requirements) == 1
    assert analysis.eligibility_requirements[0].status == "Unknown"


def test_v2_analysis_path_uses_one_canonical_requirement_id_namespace() -> None:
    eligibility = _requirement(
        "3年以上 AI 产品经验",
        "3年以上 AI 产品经验",
        "eligibility",
        importance="Critical",
        eligibility_category="experience_years",
    )
    matchable = _requirement("熟练使用 SQL", "熟练使用 SQL", "matchable", importance="Critical")
    knowledge = _requirement(
        "理解 RAG 原理", "理解 RAG 原理", "knowledge", knowledge_topics=["RAG 原理"]
    )
    db, job_id, matcher = _setup(_v2_jd(eligibility, matchable, knowledge))
    structured_jd = JobService(db, Settings()).get(job_id).structured_jd

    by_type = {item.requirement_type: item.requirement_id for item in structured_jd.requirements}
    reqv2_e, reqv2_m, reqv2_k = by_type["eligibility"], by_type["matchable"], by_type["knowledge"]

    evidence = EvidenceCatalogBuilder().build(ProfileRepository(db).get_full_profile())
    matcher.analyze.return_value = FitAnalysisOutput(
        summary="候选人具备直接 SQL 证据。",
        requirement_matches=[
            RequirementMatchOutput(
                requirement_id=reqv2_m,
                importance="Critical",
                is_hard_requirement=False,
                hard_requirement_category="none",
                match_status="Strong",
                reason="有直接的 SQL 数据分析交付证据。",
                confidence="High",
                evidence_source_ids=[next(iter(evidence.by_catalog_id))],
            )
        ],
        suggested_preparation=[],
    )

    analysis = FitAnalysisService(db, Settings()).analyze(job_id, matcher).analysis
    assert analysis is not None

    # Phase 3 matcher input: ONLY reqv2_M.
    matcher_catalog = matcher.analyze.call_args.args[0]
    assert [item.requirement_id for item in matcher_catalog.requirements] == [reqv2_m]
    # RequirementMatch + score_basis: ONLY reqv2_M.
    assert [item.requirement_id for item in analysis.requirement_matches] == [reqv2_m]
    assert analysis.score_basis.included_requirement_ids == [reqv2_m]
    # Eligibility / knowledge references use their own canonical ids.
    assert [item.requirement_id for item in analysis.eligibility_requirements] == [reqv2_e]
    assert [item.requirement_id for item in analysis.knowledge_requirements] == [reqv2_k]

    # No legacy-generated req_* id anywhere in the V2 analysis path.
    seen_ids = (
        [item.requirement_id for item in matcher_catalog.requirements]
        + [item.requirement_id for item in analysis.requirement_matches]
        + analysis.score_basis.included_requirement_ids
        + [item.requirement_id for item in analysis.eligibility_requirements]
        + [item.requirement_id for item in analysis.knowledge_requirements]
    )
    assert seen_ids and all(rid.startswith("reqv2_") for rid in seen_ids)
    assert not any(rid.startswith("req_") for rid in seen_ids)


def test_matcher_returning_an_unknown_reqv2_id_is_rejected() -> None:
    matchable = _requirement("熟练使用 SQL", "熟练使用 SQL", "matchable", importance="Critical")
    db, job_id, matcher = _setup(_v2_jd(matchable))
    matcher.analyze.return_value = FitAnalysisOutput(
        summary="候选人具备直接 SQL 证据。",
        requirement_matches=[
            RequirementMatchOutput(
                requirement_id="reqv2_deadbeefdeadbeef",
                importance="Critical",
                is_hard_requirement=False,
                hard_requirement_category="none",
                match_status="Missing",
                reason="无关 id。",
                confidence="Low",
                evidence_source_ids=[],
            )
        ],
        suggested_preparation=[],
    )
    try:
        FitAnalysisService(db, Settings()).analyze(job_id, matcher)
    except FitAnalysisNormalizationError:
        pass
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("Unknown requirement_id must be rejected.")


def test_legacy_v1_job_keeps_its_req_prefixed_ids() -> None:
    from app.schemas.analysis import KeyRequirement

    legacy_jd = JDRequirements(
        role="AI Product Manager",
        key_requirements=[
            KeyRequirement(
                title="至少 3 年 AI 产品经验",
                explanation="岗位硬性要求",
                priority="high",
            )
        ],
        required_skills=["至少 3 年 AI 产品经验"],
    )
    assert legacy_jd.requirement_taxonomy_version == "legacy-v1"
    catalog = RequirementCatalogBuilder().build(legacy_jd)
    assert catalog.requirements
    assert all(item.requirement_id.startswith("req_") for item in catalog.requirements)
    assert not any(item.requirement_id.startswith("reqv2_") for item in catalog.requirements)


def test_preview_for_knowledge_only_v2_job_is_unscorable() -> None:
    jd = _v2_jd(
        _requirement("理解 Transformer 原理", "理解 Transformer 原理", "knowledge"),
    )
    db, job_id, matcher = _setup(jd)
    structured_jd = JobService(db, Settings()).get(job_id).structured_jd

    preview = FitAnalysisService(db, Settings()).analyze_preview(structured_jd, matcher)

    matcher.analyze.assert_not_called()
    assert preview.match_score is None
    assert preview.score_status == "unavailable_no_matchable_requirements"
    assert preview.recommendation is None
    assert len(preview.knowledge_requirements) == 1
