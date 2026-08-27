from unittest.mock import Mock

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import ActivityEvent
from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import Education, JDRequirements, KeyRequirement, ResumeProfile
from app.schemas.fit_analysis import FitAnalysisOutput, RequirementMatchOutput
from app.schemas.job import JobCreate
from app.services.eligibility_service import EligibilityService
from app.services.evidence_catalog import EvidenceCatalogBuilder
from app.services.fit_analysis_service import FitAnalysisService
from app.services.job_service import JobService
from app.services.profile_service import ProfileService
from app.services.requirement_matcher import RequirementMatcher


class IdentityMatcher:
    PROMPT_VERSION = RequirementMatcher.PROMPT_VERSION
    SCHEMA_VERSION = RequirementMatcher.SCHEMA_VERSION

    def __init__(self, source_id: str):
        self.client = Mock(model="identity-test-model")
        self.source_id = source_id

    def analyze(self, requirements, evidence):
        return FitAnalysisOutput(
            summary="校招身份要求已按结构化证据核验。",
            requirement_matches=[
                RequirementMatchOutput(
                    requirement_id=requirements.requirements[0].requirement_id,
                    importance="Critical",
                    is_hard_requirement=True,
                    hard_requirement_category="eligibility",
                    match_status="Strong",
                    reason="模型仅引用了毕业届别。",
                    confidence="High",
                    evidence_source_ids=[self.source_id],
                )
            ],
            suggested_preparation=[],
        )


def identity_case(*, graduation_year: int | None, with_degree: bool = True):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    education = (
        [Education(institution="Example University", degree="本科", period="2023-2027")]
        if with_degree
        else []
    )
    ProfileService(db).replace_resume(
        "master.docx", "verified resume", ResumeProfile(education=education)
    )
    if graduation_year is not None:
        ProfileService(db).update_candidate_identity("graduate", graduation_year)
    return db


def create_identity_job(
    db: Session,
    requirement: str,
    explanation: str = "校园招聘硬性要求",
):
    structured = JDRequirements(
        role="Campus Product Manager",
        key_requirements=[
            KeyRequirement(title=requirement, explanation=explanation, priority="high")
        ],
    )
    return JobService(db, Settings()).create(
        JobCreate(
            company="Example",
            role="Campus Product Manager",
            original_jd=(f"Example campus role requires {requirement}. " * 4),
            structured_jd=structured,
        )
    )


def test_candidate_identity_persists_as_confirmed_evidence_and_changes_hash() -> None:
    db = identity_case(graduation_year=None)
    try:
        profile = ProfileRepository(db).get_full_profile()
        before = EvidenceCatalogBuilder().build(profile).experience_bank_hash
        updated = ProfileService(db).update_candidate_identity("graduate", 2027)
        assert updated.candidate_type == "graduate"
        assert updated.graduation_year == 2027
        catalog = EvidenceCatalogBuilder().build(ProfileRepository(db).get_full_profile())
        assert catalog.experience_bank_hash != before
        assert catalog.by_catalog_id[
            "manual_confirmed:profile:candidate_type"
        ].text == "求职身份：应届 / 校招"
        assert catalog.by_catalog_id[
            "manual_confirmed:profile:graduation_year"
        ].text == "毕业届别：2027届"
        event = db.scalar(
            select(ActivityEvent).where(ActivityEvent.event_type == "candidate_identity_changed")
        )
        assert event is not None
        assert event.metadata_json["to"] == {
            "candidate_type": "graduate",
            "graduation_year": 2027,
        }
    finally:
        db.close()


def test_2027_compound_requirement_needs_separate_cohort_and_degree_evidence() -> None:
    db = identity_case(graduation_year=2027, with_degree=True)
    try:
        job = create_identity_job(db, "2027届本科及以上学历")
        result = FitAnalysisService(db, Settings(claude_model="identity-test-model")).analyze(
            job.id, IdentityMatcher("manual_confirmed:profile:graduation_year")
        )
        assert result.analysis is not None
        match = result.analysis.requirement_matches[0]
        assert match.match_status == "Strong"
        assert result.analysis.match_score == 100
        assert result.analysis.summary == (
            "已按最终验证证据完成 1 项岗位要求核验："
            "1 项已匹配，0 项部分匹配，0 项暂无匹配证据。"
        )
        assert {source.context for source in match.evidence_sources} == {
            "求职档案 · 求职身份",
            "教育经历",
        }
        assert "毕业届别为 2027 届" in match.reason
        assert "本科及以上学历" in match.reason
    finally:
        db.close()


def test_compound_requirement_can_span_parsed_title_and_context() -> None:
    db = identity_case(graduation_year=2027, with_degree=True)
    try:
        job = create_identity_job(
            db,
            "2027届应届毕业生学历要求",
            "2027届毕业生，获得本科及以上学历，计算机相关专业优先",
        )
        result = FitAnalysisService(
            db, Settings(claude_model="identity-test-model")
        ).analyze(
            job.id, IdentityMatcher("manual_confirmed:profile:graduation_year")
        )
        assert result.analysis is not None
        match = result.analysis.requirement_matches[0]
        assert match.match_status == "Strong"
        assert match.reason.endswith("且主简历教育经历支持本科及以上学历。")
        assert {source.context for source in match.evidence_sources} == {
            "求职档案 · 求职身份",
            "教育经历",
        }
    finally:
        db.close()


def test_matching_cohort_without_degree_is_partial_not_strong() -> None:
    db = identity_case(graduation_year=2027, with_degree=False)
    try:
        job = create_identity_job(db, "2027届本科及以上学历")
        result = FitAnalysisService(db, Settings(claude_model="identity-test-model")).analyze(
            job.id, IdentityMatcher("manual_confirmed:profile:graduation_year")
        )
        assert result.analysis is not None
        match = result.analysis.requirement_matches[0]
        assert match.match_status == "Partial"
        assert result.analysis.match_score == 50
        assert "尚未确认本科及以上学历" in match.reason
    finally:
        db.close()


def test_wrong_or_unknown_cohort_is_never_treated_as_supported() -> None:
    wrong = identity_case(graduation_year=2026, with_degree=True)
    try:
        job = create_identity_job(wrong, "2027届本科及以上学历")
        result = FitAnalysisService(
            wrong, Settings(claude_model="identity-test-model")
        ).analyze(job.id, IdentityMatcher("manual_confirmed:profile:graduation_year"))
        assert result.analysis is not None
        match = result.analysis.requirement_matches[0]
        assert match.match_status == "Partial"
        assert "2026 届" in match.reason and "2027 届" in match.reason
        assert all("graduation_year" not in source.source_id for source in match.evidence_sources)
    finally:
        wrong.close()

    unknown = identity_case(graduation_year=None, with_degree=True)
    try:
        job = create_identity_job(unknown, "2027届")
        catalog = EvidenceCatalogBuilder().build(ProfileRepository(unknown).get_full_profile())
        unrelated_id = next(iter(catalog.by_catalog_id))
        result = FitAnalysisService(
            unknown, Settings(claude_model="identity-test-model")
        ).analyze(job.id, IdentityMatcher(unrelated_id))
        assert result.analysis is not None
        match = result.analysis.requirement_matches[0]
        assert match.match_status == "Missing"
        assert match.evidence_sources == []
        assert "尚未确认该毕业届别" in match.reason
    finally:
        unknown.close()


def test_phase5_eligibility_uses_confirmed_identity_and_keeps_degree_independent() -> None:
    supported = identity_case(graduation_year=2027, with_degree=True)
    try:
        job = create_identity_job(supported, "2027届本科及以上学历")
        profile = ProfileRepository(supported).get_full_profile()
        assert EligibilityService().evaluate(profile, job).status == "Eligible"
    finally:
        supported.close()

    degree_unknown = identity_case(graduation_year=2027, with_degree=False)
    try:
        job = create_identity_job(degree_unknown, "2027届本科及以上学历")
        profile = ProfileRepository(degree_unknown).get_full_profile()
        result = EligibilityService().evaluate(profile, job)
        assert result.status == "PossiblyEligible"
        assert result.unknown_requirements == ["2027届本科及以上学历"]
    finally:
        degree_unknown.close()
