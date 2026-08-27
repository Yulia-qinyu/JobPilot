from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import Job, JobAnalysis, JobDecision, TargetRole
from app.db.session import get_db
from app.main import app
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.analysis import Education, JDRequirements, ResumeProfile, WorkExperience
from app.schemas.job import JobCreate
from app.schemas.job_decision import JobDecisionOverride
from app.services.eligibility_service import EligibilityService
from app.services.evidence_catalog import EvidenceCatalogBuilder
from app.services.job_decision_service import JobDecisionService
from app.services.job_service import JobService
from app.services.profile_service import ProfileService
from app.services.requirement_catalog import RequirementCatalogBuilder
from app.services.role_classifier import RoleClassifier
from app.services.target_role_fit_service import TargetRoleFitService


def make_engine():
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)


def seed_profile(db: Session, *, years: str = "2022–2026", degree: str = "本科") -> None:
    ProfileService(db).replace_resume(
        "master.docx",
        "private resume text",
        ResumeProfile(
            education=[Education(institution="Example", degree=degree, period="2023–2027")],
            work_experience=[WorkExperience(company="Acme", title="Product Manager", period=years)],
        ),
    )


def seed_job(db: Session, role: str, requirements: list[str] | None = None) -> Job:
    result = JobService(db, Settings()).create(
        JobCreate(
            company="Example",
            role=role,
            location="北京",
            original_jd="A sufficiently detailed fictional job description for deterministic tests.",
            structured_jd=JDRequirements(
                company="Example",
                role=role,
                responsibilities=["负责产品工作"],
                required_skills=requirements or [],
            ),
        )
    )
    return db.get(Job, result.id)  # type: ignore[return-value]


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("AI产品经理", "ai_product"),
        ("金融科技产品经理", "fintech_product"),
        ("数据产品经理", "data_product"),
        ("策略产品经理", "strategy_product"),
        ("平台产品经理", "platform_product"),
        ("增长产品经理", "growth_product"),
        ("产品经理", "general_product"),
        ("产品运营", "product_operations"),
        ("后端工程师", "engineering"),
        ("算法工程师", "algorithm"),
        ("交互设计师", "design"),
        ("业务伙伴", "unknown"),
    ],
)
def test_role_classifier_is_conservative_and_stable(db: Session, role: str, expected: str) -> None:
    job = seed_job(db, role)
    first = RoleClassifier().classify(job)
    second = RoleClassifier().classify(job)
    assert first.role_family == expected
    assert first == second


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        ("至少 3 年工作经验", "Eligible"),
        ("至少 5 年工作经验", "Ineligible"),
        ("必须为 2026 届毕业生", "Ineligible"),
        ("本科及以上学历", "Eligible"),
        ("必须具备 CET-6", "PossiblyEligible"),
        ("必须具备工作许可", "PossiblyEligible"),
        ("5 年经验者优先", "Eligible"),
        ("熟悉 Python", "Eligible"),
    ],
)
def test_eligibility_requires_explicit_conflicting_evidence(
    db: Session, requirement: str, expected: str
) -> None:
    seed_profile(db)
    job = seed_job(db, "AI 产品经理", [requirement])
    profile = ProfileRepository(db).get_full_profile()
    assert EligibilityService().evaluate(profile, job).status == expected


def test_missing_candidate_profile_is_unknown_not_ineligible(db: Session) -> None:
    job = seed_job(db, "AI 产品经理", ["必须具备 CET-6"])
    profile = ProfileRepository(db).get_full_profile()
    assert EligibilityService().evaluate(profile, job).status == "Unknown"


def test_target_role_fit_uses_highest_exact_priority(db: Session) -> None:
    ProfileRepository(db).ensure_default_profile()
    roles = [
        TargetRole(
            user_profile_id=DEFAULT_PROFILE_ID,
            name="Explore AI PM",
            priority="exploratory",
            role_family="ai_product",
        ),
        TargetRole(
            user_profile_id=DEFAULT_PROFILE_ID,
            name="Primary AI PM",
            priority="primary",
            role_family="ai_product",
        ),
    ]
    db.add_all(roles)
    db.commit()
    assert TargetRoleFitService().evaluate("ai_product", roles) == "Primary"
    assert TargetRoleFitService().evaluate("engineering", roles) == "NotTarget"
    assert TargetRoleFitService().evaluate("general_product", roles) == "Low"


def test_target_role_fit_uses_persisted_effective_family(db: Session) -> None:
    ProfileRepository(db).ensure_default_profile()
    role = TargetRole(
        user_profile_id=DEFAULT_PROFILE_ID,
        name="AI 产品经理",
        priority="primary",
        auto_role_family="ai_product",
        role_family_override="strategy_product",
        role_family="strategy_product",
    )
    db.add(role)
    db.commit()

    assert TargetRoleFitService().evaluate("strategy_product", [role]) == "Primary"
    assert TargetRoleFitService().evaluate("ai_product", [role]) == "Low"


def test_recompute_override_freshness_and_phase3_final_decision(db: Session) -> None:
    seed_profile(db)
    profile_service = ProfileService(db)
    profile_service.add_role("AI Product Manager", "primary")
    job = seed_job(db, "AI 产品经理", ["本科及以上学历"])
    service = JobDecisionService(db)
    first = service.get(job.id)
    assert first.pre_match_decision == "WorthAnalyzing"
    assert first.final_decision is None

    overridden = service.update_overrides(
        job.id,
        JobDecisionOverride(
            role_family_override="strategy_product",
            eligibility_override="PossiblyEligible",
            eligibility_override_reason="已知仍需确认条件",
        ),
    )
    assert overridden.effective_role_family == "strategy_product"
    assert overridden.eligibility_override == "PossiblyEligible"
    ProfileService(db).update_location("上海")
    assert service.get(job.id).is_stale is True
    service.recompute([job.id])
    assert service.get(job.id).role_family_override == "strategy_product"

    cleared = service.update_overrides(
        job.id,
        JobDecisionOverride(role_family_override=None, eligibility_override=None),
    )
    assert cleared.effective_role_family == "ai_product"

    profile = ProfileRepository(db).get_full_profile()
    evidence = EvidenceCatalogBuilder().build(profile)
    requirement_hash = RequirementCatalogBuilder().build(job.structured_jd).structured_jd_hash
    db.add(
        JobAnalysis(
            job_id=job.id,
            resume_hash=evidence.resume_hash,
            experience_bank_hash=evidence.experience_bank_hash,
            structured_jd_hash=requirement_hash,
            matcher_model="test",
            matcher_prompt_version="test",
            matcher_schema_version="test",
            match_score=90,
            recommendation="Strong Apply",
            summary="Supported result",
            requirement_matches=[],
            strengths=[],
            gaps=[],
            suggested_preparation=[],
        )
    )
    db.commit()
    service.recompute([job.id])
    assert service.get(job.id).final_decision == "Priority"

    ProfileService(db).add_role("Data Product Manager", "secondary")
    stale = service.get(job.id)
    assert stale.is_stale is True
    assert stale.final_decision == "Priority"
    service.recompute([job.id])
    assert service.get(job.id).final_decision == "Priority"

    experience_id = ProfileRepository(db).get_full_profile().experiences[0].id
    ProfileService(db).add_fact(experience_id, "New confirmed evidence.", True)
    service.recompute([job.id])
    assert service.get(job.id).final_decision is None


def test_job_decision_api_paginates_filters_summarizes_and_never_calls_claude() -> None:
    engine = make_engine()
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with testing_session() as db:
            seed_profile(db)
            ProfileService(db).add_role("AI Product Manager", "primary")
            for index in range(406):
                db.add(
                    Job(
                        user_profile_id=DEFAULT_PROFILE_ID,
                        company=f"Company {index:02d}",
                        role="AI 产品经理" if index % 2 == 0 else "后端工程师",
                        location="北京",
                        original_jd="职位描述\n测试\n职位要求\n本科及以上学历",
                        structured_jd=JDRequirements(
                            role="AI 产品经理" if index % 2 == 0 else "后端工程师",
                            responsibilities=["测试"],
                            required_skills=["本科及以上学历"],
                        ).model_dump(mode="json"),
                        status="Interested",
                        source_content_hash=f"hash-{index}",
                    )
                )
            db.commit()
            result = JobDecisionService(db).recompute()
            assert result.claude_api_calls == 0
            assert db.scalar(select(func.count(JobDecision.id))) == 406

        client = TestClient(app)
        page = client.get("/api/job-decisions?page=1&page_size=25&role_fit=Primary")
        assert page.status_code == 200
        assert page.json()["total"] == 203
        assert len(page.json()["items"]) == 25
        assert page.json()["total_pages"] == 9
        summary = client.get("/api/job-decisions/summary").json()
        assert summary == {
            "total": 406,
            "no_explicit_blocker": 406,
            "target_fit": 203,
            "analyzed": 0,
            "priority": 0,
        }
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_recompute_supports_2000_jobs_without_ai(db: Session) -> None:
    ProfileRepository(db).ensure_default_profile()
    structured = JDRequirements(
        role="Product Manager", responsibilities=["Own roadmap"]
    ).model_dump(mode="json")
    db.add_all(
        Job(
            user_profile_id=DEFAULT_PROFILE_ID,
            company="Scale Test",
            role="Product Manager",
            location="北京",
            original_jd="Synthetic scale test content",
            structured_jd=structured,
            status="Interested",
            source_content_hash=f"scale-{index}",
        )
        for index in range(2_000)
    )
    db.commit()
    result = JobDecisionService(db).recompute()
    assert result.processed == 2_000
    assert result.failed == 0
    assert result.claude_api_calls == 0
