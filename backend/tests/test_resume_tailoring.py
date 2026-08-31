from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routes.resume_tailoring import get_rewriter, get_semantic_validator
from app.schemas.analysis import JDRequirements, KeyRequirement, ResumeProfile, WorkExperience
from app.schemas.fit_analysis import FitAnalysisOutput, RequirementMatchOutput
from app.schemas.job import JobCreate
from app.schemas.resume_tailoring import (
    DraftEditItem,
    GeneratedBulletOutput,
    SemanticValidationItemOutput,
    SemanticValidationOutput,
    TailoredDraftOutput,
    TailoredDraftPatch,
    TailoringPlanPatch,
)
from app.services.evidence_catalog import EvidenceCatalogBuilder
from app.services.fit_analysis_service import FitAnalysisService
from app.services.job_service import JobService
from app.services.profile_service import ProfileService
from app.services.requirement_catalog import RequirementCatalogBuilder
from app.services.resume_claim_validator import ResumeClaimValidator
from app.services.resume_tailoring_service import (
    AnalysisRequiredError,
    AnalysisStaleError,
    InvalidEvidenceReferenceError,
    NoMatchableRequirementsError,
    PlanNotConfirmedError,
    ResumeTailoringService,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)


def setup_case(db: Session) -> tuple[int, Mock]:
    profile = ProfileService(db).replace_resume(
        "master.docx",
        "private resume",
        ResumeProfile(
            skills=["LLM", "PostgreSQL", "TypeScript"],
            work_experience=[
                WorkExperience(
                    company="Acme",
                    title="Product Manager",
                    period="2024–2026",
                    highlights=["参与实现使用 PostgreSQL 的 LLM 匹配模块，服务 10 名用户。"],
                )
            ],
        ),
    )
    experience_id = profile.experiences[0].id
    ProfileService(db).add_fact(experience_id, "采访 12 名客户并整理产品需求。", True)
    job = JobService(db, Settings()).create(
        JobCreate(
            company="Example",
            role="AI Product Manager",
            original_jd="A sufficiently detailed fictional JD for safe testing.",
            structured_jd=JDRequirements(
                role="AI Product Manager",
                key_requirements=[
                    KeyRequirement(
                        title="LLM 产品交付", explanation="负责 LLM 产品", priority="high"
                    ),
                    KeyRequirement(title="客户研究", explanation="开展客户访谈", priority="high"),
                    KeyRequirement(
                        title="AWS 认证", explanation="必须持有 AWS 认证", priority="high"
                    ),
                ],
            ),
        )
    )
    from app.repositories.profile_repository import ProfileRepository

    catalog = EvidenceCatalogBuilder().build(ProfileRepository(db).get_full_profile())
    requirements = RequirementCatalogBuilder().build(job.structured_jd).requirements
    resume_evidence = next(
        key
        for key in catalog.by_catalog_id
        if key.startswith("resume_extracted:") and key.split(":")[-1].isdigit()
    )
    manual_evidence = next(
        key for key in catalog.by_catalog_id if key.startswith("manual_confirmed:")
    )
    matcher = Mock()
    matcher.client.model = "test-model"
    matcher.PROMPT_VERSION = "fit-test"
    matcher.SCHEMA_VERSION = "fit-test"
    matcher.analyze.return_value = FitAnalysisOutput(
        summary="测试分析",
        requirement_matches=[
            RequirementMatchOutput(
                requirement_id=requirements[0].requirement_id,
                importance="Critical",
                is_hard_requirement=False,
                hard_requirement_category="none",
                match_status="Strong",
                reason="有实现证据",
                confidence="High",
                evidence_source_ids=[resume_evidence],
            ),
            RequirementMatchOutput(
                requirement_id=requirements[1].requirement_id,
                importance="Important",
                is_hard_requirement=False,
                hard_requirement_category="none",
                match_status="Strong",
                reason="有访谈证据",
                confidence="High",
                evidence_source_ids=[manual_evidence],
            ),
            RequirementMatchOutput(
                requirement_id=requirements[2].requirement_id,
                importance="Critical",
                is_hard_requirement=True,
                hard_requirement_category="qualification",
                match_status="Missing",
                reason="没有证书",
                confidence="High",
                evidence_source_ids=[],
            ),
        ],
        suggested_preparation=[],
    )
    FitAnalysisService(db, Settings()).analyze(job.id, matcher)
    return job.id, matcher


def test_analysis_is_required_and_stale_analysis_is_rejected(db: Session) -> None:
    job = JobService(db, Settings()).create(
        JobCreate(
            company="X",
            role="PM",
            original_jd="A sufficiently long fictional job description for prerequisite testing.",
            structured_jd=JDRequirements(),
        )
    )
    with pytest.raises(AnalysisRequiredError):
        ResumeTailoringService(db, Settings()).create_plan(job.id)

    job_id, _ = setup_case(db)
    ProfileService(db).add_fact(1, "新的已确认事实。", True)
    with pytest.raises(AnalysisStaleError):
        ResumeTailoringService(db, Settings()).create_plan(job_id)


def test_v2_job_without_matchable_requirements_has_no_tailoring_and_no_claude(db: Session) -> None:
    from app.schemas.analysis import StructuredRequirement

    ProfileService(db).replace_resume(
        "master.docx",
        "private resume",
        ResumeProfile(
            skills=["LLM"],
            work_experience=[
                WorkExperience(company="Acme", title="PM", highlights=["Shipped an LLM feature."])
            ],
        ),
    )
    knowledge = StructuredRequirement(
        requirement_id=RequirementCatalogBuilder.stable_requirement_id(
            source_text="理解 RAG 原理",
            normalized_requirement="理解 RAG 原理",
            requirement_type="knowledge",
            source_section="requirements",
        ),
        source_text="理解 RAG 原理",
        normalized_requirement="理解 RAG 原理",
        source_section="requirements",
        requirement_type="knowledge",
        importance="Important",
        knowledge_topics=["RAG 原理"],
    )
    job = JobService(db, Settings()).create(
        JobCreate(
            company="Example",
            role="AI Researcher",
            original_jd="A sufficiently detailed fictional knowledge-only JD for safe testing.",
            structured_jd=JDRequirements(
                role="AI Researcher",
                requirement_taxonomy_version="v2",
                requirements=[knowledge],
            ),
        )
    )
    matcher = Mock()
    matcher.client.model = "test-model"
    matcher.PROMPT_VERSION = "fit-test"
    matcher.SCHEMA_VERSION = "fit-test"
    FitAnalysisService(db, Settings()).analyze(job.id, matcher)
    matcher.analyze.assert_not_called()

    service = ResumeTailoringService(db, Settings())
    assert service.get_state(job.id).prerequisite == "NoMatchableRequirements"

    rewriter, validator = Mock(), Mock()
    with pytest.raises(NoMatchableRequirementsError):
        service.create_plan(job.id)
    with pytest.raises(NoMatchableRequirementsError):
        service.generate_draft(job.id, rewriter, validator)
    rewriter.generate.assert_not_called()
    validator.semantic_validate.assert_not_called()


def test_plan_is_deterministic_includes_manual_add_and_unsupported(db: Session) -> None:
    job_id, matcher = setup_case(db)
    service = ResumeTailoringService(db, Settings())
    state = service.create_plan(job_id)
    assert matcher.analyze.call_count == 1
    assert state.tailoring is not None
    plan = state.tailoring.tailoring_plan
    actions = [item.recommended_action for exp in plan.experiences for item in exp.bullet_items]
    assert "Keep" in actions
    assert "Add" in actions
    assert plan.unsupported_requirements[0].text == "AWS 认证"
    assert plan.confirmed is False

    with pytest.raises(PlanNotConfirmedError):
        service.generate_draft(job_id, Mock(), Mock())


def test_unconfirmed_manual_fact_is_excluded_from_plan(db: Session) -> None:
    job_id, _ = setup_case(db)
    ProfileService(db).add_fact(1, "尚未确认的 Kubernetes 经验。", False)
    # Ineligible evidence is absent and therefore does not invalidate Phase 3.
    from app.repositories.profile_repository import ProfileRepository

    assert all(
        source.text != "尚未确认的 Kubernetes 经验。"
        for source in EvidenceCatalogBuilder()
        .build(ProfileRepository(db).get_full_profile())
        .sources
    )
    state = ResumeTailoringService(db, Settings()).create_plan(job_id)
    assert all(
        item.text != "尚未确认的 Kubernetes 经验。"
        for item in state.tailoring.tailoring_plan.evidence  # type: ignore[union-attr]
    )


def test_omit_requires_explicit_confirmation(db: Session) -> None:
    job_id, _ = setup_case(db)
    service = ResumeTailoringService(db, Settings())
    state = service.create_plan(job_id)
    assert state.tailoring is not None
    item_id = state.tailoring.tailoring_plan.experiences[0].bullet_items[0].plan_item_id
    patched = service.patch_plan(
        job_id,
        TailoringPlanPatch(
            items=[{"plan_item_id": item_id, "action": "Omit", "omit_confirmed": False}],
            confirmed=True,
        ),
    )
    item = patched.tailoring.tailoring_plan.experiences[0].bullet_items[0]  # type: ignore[union-attr]
    assert item.effective_action == "Keep"
    assert item.omit_confirmed is False


def test_generation_and_semantic_validation_are_one_batch_each(db: Session) -> None:
    job_id, _ = setup_case(db)
    service = ResumeTailoringService(db, Settings())
    planned = service.create_plan(job_id)
    service.patch_plan(job_id, TailoringPlanPatch(confirmed=True))
    plan = planned.tailoring.tailoring_plan  # type: ignore[union-attr]
    requested = [
        item
        for exp in plan.experiences
        for item in exp.bullet_items
        if item.effective_action in {"Rewrite", "Add"}
    ]
    rewriter = Mock()
    rewriter.client.model = "generator-test"
    rewriter.PROMPT_VERSION = "generator-v1"
    rewriter.SCHEMA_VERSION = "generator-wire-v1"
    rewriter.generate.return_value = TailoredDraftOutput(
        summary="针对岗位突出相关事实。",
        bullets=[
            GeneratedBulletOutput(
                plan_item_id=item.plan_item_id,
                action="Rewrite",
                rewritten_text=item.original_text,
                evidence_source_ids=item.allowed_evidence_ids,
                requirement_ids=item.target_requirement_ids,
                change_summary="保持事实并调整措辞。",
            )
            for item in requested
        ],
    )
    validator = Mock()
    validator.client.model = "validator-test"
    validator.PROMPT_VERSION = "validator-v1"
    validator.SCHEMA_VERSION = "validator-wire-v1"
    validator.GUARDRAIL_VERSION = "guard-v1"
    validator.deterministic.side_effect = lambda text, evidence, skills, context: (
        ResumeClaimValidator().deterministic(text, evidence, skills, context)
    )
    validator.semantic_validate.return_value = SemanticValidationOutput(
        results=[
            SemanticValidationItemOutput(plan_item_id=item.plan_item_id, unsupported_spans=[])
            for item in requested
        ]
    )
    result = service.generate_draft(job_id, rewriter, validator)
    assert rewriter.generate.call_count == 1
    assert validator.semantic_validate.call_count == 1
    assert result.tailoring is not None
    assert result.tailoring.status == "DraftReady"
    assert result.tailoring.generation_count == 1
    service.accept(job_id)
    assert service.get_state(job_id).tailoring.status == "Accepted"  # type: ignore[union-attr]

    edited_id = requested[0].plan_item_id
    edited = service.edit_draft(
        job_id,
        TailoredDraftPatch(
            items=[DraftEditItem(plan_item_id=edited_id, text=requested[0].original_text)]
        ),
    )
    assert edited.tailoring.status == "PendingValidation"  # type: ignore[union-attr]
    validator.semantic_validate.reset_mock()
    validator.semantic_validate.return_value = SemanticValidationOutput(
        results=[SemanticValidationItemOutput(plan_item_id=edited_id, unsupported_spans=[])]
    )
    service.validate_edits(job_id, validator)
    assert validator.semantic_validate.call_count == 1
    service.accept(job_id)

    ProfileService(db).add_fact(1, "新的已确认事实使分析与简历草稿过期。", True)
    assert service.get_state(job_id).prerequisite == "AnalysisStale"
    with pytest.raises(AnalysisStaleError):
        service.accept(job_id)


def test_duplicate_or_unknown_generation_ids_are_rejected(db: Session) -> None:
    job_id, _ = setup_case(db)
    service = ResumeTailoringService(db, Settings())
    service.create_plan(job_id)
    service.patch_plan(job_id, TailoringPlanPatch(confirmed=True))
    rewriter = Mock()
    rewriter.generate.return_value = TailoredDraftOutput(summary="bad", bullets=[])
    validator = Mock()
    with pytest.raises(InvalidEvidenceReferenceError):
        service.generate_draft(job_id, rewriter, validator)
    assert validator.semantic_validate.call_count == 0


def test_semantic_failure_falls_back_to_original(db: Session) -> None:
    job_id, _ = setup_case(db)
    service = ResumeTailoringService(db, Settings())
    planned = service.create_plan(job_id)
    service.patch_plan(job_id, TailoringPlanPatch(confirmed=True))
    requested = [
        item
        for exp in planned.tailoring.tailoring_plan.experiences  # type: ignore[union-attr]
        for item in exp.bullet_items
        if item.effective_action in {"Rewrite", "Add"}
    ]
    rewriter = Mock(client=Mock(model="generator"), PROMPT_VERSION="v1", SCHEMA_VERSION="v1")
    rewriter.generate.return_value = TailoredDraftOutput(
        summary="test",
        bullets=[
            GeneratedBulletOutput(
                plan_item_id=item.plan_item_id,
                action="Rewrite",
                rewritten_text=item.original_text,
                evidence_source_ids=item.allowed_evidence_ids,
                requirement_ids=item.target_requirement_ids,
                change_summary="test",
            )
            for item in requested
        ],
    )
    validator = Mock(
        client=Mock(model="validator"),
        PROMPT_VERSION="v1",
        SCHEMA_VERSION="v1",
        GUARDRAIL_VERSION="v1",
    )
    validator.deterministic.side_effect = lambda text, evidence, skills, context: (
        ResumeClaimValidator().deterministic(text, evidence, skills, context)
    )
    validator.semantic_validate.return_value = SemanticValidationOutput(
        results=[
            SemanticValidationItemOutput(
                plan_item_id=item.plan_item_id,
                unsupported_spans=[item.original_text[:2]],
            )
            for item in requested
        ]
    )
    state = service.generate_draft(job_id, rewriter, validator)
    draft = state.tailoring.generated_draft  # type: ignore[union-attr]
    assert state.tailoring.status == "ValidationFailed"  # type: ignore[union-attr]
    assert all(
        bullet.state == "FallbackOriginal" and bullet.effective_text == bullet.original_text
        for experience in draft.experiences  # type: ignore[union-attr]
        for bullet in experience.bullets
        if bullet.action in {"Rewrite", "Add"}
    )


def test_tailoring_api_plan_does_not_call_ai(db: Session) -> None:
    job_id, _ = setup_case(db)
    rewriter = Mock()
    validator = Mock()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_rewriter] = lambda: rewriter
    app.dependency_overrides[get_semantic_validator] = lambda: validator
    try:
        with TestClient(app) as client:
            initial = client.get(f"/api/jobs/{job_id}/resume-tailoring")
            assert initial.status_code == 200
            assert initial.json()["prerequisite"] == "Ready"
            created = client.post(f"/api/jobs/{job_id}/resume-tailoring/plan")
            assert created.status_code == 200
            assert created.json()["tailoring"]["status"] == "PlanReady"
    finally:
        app.dependency_overrides.clear()
    rewriter.generate.assert_not_called()
    validator.semantic_validate.assert_not_called()


@pytest.mark.parametrize(
    ("bullet", "evidence", "field", "valid"),
    [
        ("服务 10 名用户", "服务 10 名用户", "numbers_valid", True),
        ("服务 35% 更多用户", "服务 10 名用户", "numbers_valid", False),
        ("服务 10万+ 用户", "服务 10 名用户", "numbers_valid", False),
        ("创造 $2M 营收", "改善内部流程", "numbers_valid", False),
        ("交付周期为 3 个月", "交付周期为 3 个月", "numbers_valid", True),
        ("交付周期为 2 个月", "交付周期为 3 个月", "numbers_valid", False),
        ("2025 年交付", "2024 年交付", "numbers_valid", False),
        ("管理 5 人团队", "参与团队交付", "numbers_valid", False),
        ("Built the matching module", "Implemented the matching module", "ownership_valid", True),
        ("Led the matching module", "Implemented the matching module", "ownership_valid", False),
        ("主导匹配模块", "参与匹配模块", "ownership_valid", False),
        ("使用 Postgres 构建模块", "使用 PostgreSQL 构建模块", "skills_valid", True),
        ("使用 AWS 构建模块", "使用 PostgreSQL 构建模块", "skills_valid", False),
        ("获得 AWS Certified 认证", "使用 PostgreSQL 构建模块", "skills_valid", False),
        ("服务全球市场", "构建内部产品", "entities_valid", False),
    ],
)
def test_deterministic_claim_guardrails(
    bullet: str, evidence: str, field: str, valid: bool
) -> None:
    result = (
        ResumeClaimValidator().deterministic(bullet, [evidence], ["PostgreSQL", "LLM"]).validation
    )
    assert getattr(result, field) is valid
