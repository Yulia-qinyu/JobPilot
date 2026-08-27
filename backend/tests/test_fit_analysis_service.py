import logging
from unittest.mock import Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import JDRequirements, KeyRequirement, ResumeProfile, WorkExperience
from app.schemas.fit_analysis import FitAnalysisOutput, PreparationOutput, RequirementMatchOutput
from app.schemas.job import JobCreate
from app.services.evidence_catalog import EvidenceCatalogBuilder
from app.services.fit_analysis_service import FitAnalysisService
from app.services.job_service import JobService
from app.services.profile_service import ProfileService
from app.services.requirement_catalog import RequirementCatalogBuilder


def setup_case() -> tuple[Session, int, Mock, str]:
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
                    company="Acme", title="PM", highlights=["Led an LLM evaluation launch."]
                )
            ],
        ),
    )
    structured_jd = JDRequirements(
        role="AI Product Manager",
        key_requirements=[
            KeyRequirement(
                title="At least 3 years of AI product experience",
                explanation="Required for the role",
                priority="high",
            )
        ],
        required_skills=["At least 3 years of AI product experience"],
    )
    job = JobService(db, Settings()).create(
        JobCreate(
            company="Example AI",
            role="AI Product Manager",
            original_jd="A sufficiently long fictional job description for an AI Product Manager role.",
            structured_jd=structured_jd,
        )
    )
    profile = ProfileRepository(db).get_full_profile()
    evidence = EvidenceCatalogBuilder().build(profile)
    evidence_id = next(iter(evidence.by_catalog_id))
    requirement_id = (
        RequirementCatalogBuilder().build(job.structured_jd).requirements[0].requirement_id
    )
    matcher = Mock()
    matcher.client.model = "test-model"
    matcher.PROMPT_VERSION = "fit-prompt-test"
    matcher.SCHEMA_VERSION = "fit-schema-test"
    matcher.analyze.return_value = FitAnalysisOutput(
        summary="候选人具备相关 AI 产品证据，但明确年限仍需核实。",
        requirement_matches=[
            RequirementMatchOutput(
                requirement_id=requirement_id,
                importance="Important",
                is_hard_requirement=True,
                hard_requirement_category="experience",
                match_status="Partial",
                reason="有直接项目证据，但未证明完整三年经验。",
                confidence="High",
                evidence_source_ids=[evidence_id],
            )
        ],
        suggested_preparation=[
            PreparationOutput(
                title="核实经验年限",
                action="整理 AI 产品经历时间线。",
                priority="High",
                requirement_ids=[requirement_id],
            )
        ],
    )
    return db, job.id, matcher, requirement_id


def test_analysis_persists_derives_output_and_get_does_not_call_matcher(caplog) -> None:
    db, job_id, matcher, _ = setup_case()
    service = FitAnalysisService(db, Settings())
    with caplog.at_level(logging.INFO):
        result = service.analyze(job_id, matcher)
    assert result.analysis is not None
    assert result.analysis.match_score == 50
    assert result.analysis.recommendation == "Skip"
    assert result.analysis.strengths == []
    assert result.analysis.gaps[0].title.startswith("关键硬性缺口")
    assert result.analysis.gaps[0].next_step == "整理 AI 产品经历时间线。"
    assert matcher.analyze.call_count == 1
    assert "sensitive full resume" not in caplog.text
    assert "claude_api_calls=1" in caplog.text

    reloaded = FitAnalysisService(db, Settings()).get_state(job_id)
    assert reloaded.analysis is not None
    assert reloaded.analysis.id == result.analysis.id
    assert matcher.analyze.call_count == 1
    assert JobService(db, Settings()).get(job_id).match_score == 50


def test_manual_reanalysis_updates_same_record_and_stale_detection() -> None:
    db, job_id, matcher, requirement_id = setup_case()
    service = FitAnalysisService(db, Settings())
    first = service.analyze(job_id, matcher)
    matcher.analyze.return_value = FitAnalysisOutput(
        summary="补充证据后匹配更强。",
        requirement_matches=[
            RequirementMatchOutput(
                requirement_id=requirement_id,
                importance="Critical",
                is_hard_requirement=False,
                hard_requirement_category="none",
                match_status="Strong",
                reason="已有直接交付证据。",
                confidence="High",
                evidence_source_ids=[
                    next(
                        iter(
                            EvidenceCatalogBuilder()
                            .build(ProfileRepository(db).get_full_profile())
                            .by_catalog_id
                        )
                    )
                ],
            )
        ],
        suggested_preparation=[],
    )
    second = service.analyze(job_id, matcher)
    assert second.analysis is not None and first.analysis is not None
    assert second.analysis.id == first.analysis.id
    assert matcher.analyze.call_count == 2

    profile = ProfileRepository(db).get_full_profile()
    ProfileService(db).add_fact(profile.experiences[0].id, "Confirmed new evidence.", True)
    stale = service.get_state(job_id)
    assert stale.is_stale is True
    assert stale.stale_reasons == ["experience_bank"]


def test_unsupported_evidence_and_hard_claim_are_safely_downgraded() -> None:
    db, job_id, matcher, requirement_id = setup_case()
    matcher.analyze.return_value.requirement_matches[0] = RequirementMatchOutput(
        requirement_id=requirement_id,
        importance="Important",
        is_hard_requirement=True,
        hard_requirement_category="eligibility",
        match_status="Strong",
        reason="Unsupported claim",
        confidence="High",
        evidence_source_ids=["manual_unconfirmed:999", "invented:123"],
    )
    result = FitAnalysisService(db, Settings()).analyze(job_id, matcher)
    assert result.analysis is not None
    normalized = result.analysis.requirement_matches[0]
    # The years wording supports a hard requirement, but backend derives its category as experience.
    assert normalized.hard_requirement_category == "experience"
    assert normalized.match_status == "Missing"
    assert normalized.evidence_sources == []


def test_preview_analysis_uses_verified_evidence_without_persisting_a_job() -> None:
    db, job_id, matcher, _ = setup_case()
    original_job = JobService(db, Settings()).get(job_id)
    JobService(db, Settings()).delete(job_id)

    preview = FitAnalysisService(db, Settings()).analyze_preview(
        original_job.structured_jd, matcher
    )

    assert preview.match_score == 50
    assert preview.requirement_matches[0].evidence_sources
    assert JobService(db, Settings()).list() == []
    assert matcher.analyze.call_count == 1
