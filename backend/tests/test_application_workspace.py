from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.models import ActivityEvent, Job, JobAnalysis, PlanItem
from app.db.session import get_db
from app.main import app
from app.schemas.analysis import JDRequirements, KeyRequirement, ResumeProfile, WorkExperience
from app.schemas.fit_analysis import FitAnalysisOutput, PreparationOutput, RequirementMatchOutput
from app.schemas.job import JobCreate, JobUpdate
from app.schemas.workspace import (
    ApplicationStatusCreate,
    ApplicationStatusUpdate,
    PlanItemCreate,
    PlanItemUpdate,
)
from app.services.fit_analysis_service import FitAnalysisService
from app.services.job_service import JobService
from app.services.matcher_client import active_matcher_model
from app.services.preview_analysis_store import preview_analysis_store
from app.services.profile_service import ProfileService
from app.services.requirement_matcher import RequirementMatcher
from app.services.workspace_service import WorkspaceConflictError, WorkspaceService


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        preview_analysis_store.clear()


def profile_with_resume(db: Session) -> None:
    ProfileService(db).replace_resume(
        "master.docx", "verified resume",
        ResumeProfile(work_experience=[WorkExperience(company="Acme", title="PM", highlights=["Built an AI product workflow."])]),
    )


def job_payload() -> JobCreate:
    structured = JDRequirements(
        company="Example", role="AI Product Manager", location="Beijing",
        key_requirements=[KeyRequirement(title="AI 产品经验", explanation="有 AI 产品经验", priority="high")],
    )
    return JobCreate(
        company="Example", role="AI Product Manager", location="Beijing",
        original_jd="Example company seeks an AI Product Manager with evidence-grounded product delivery experience." * 2,
        structured_jd=structured,
    )


def test_strategy_defaults_persists_and_records_activity(db: Session) -> None:
    service = WorkspaceService(db)
    assert service.get_strategy().job_search_strategy == "balanced"
    assert service.update_strategy("high_volume").job_search_strategy == "high_volume"
    assert WorkspaceService(db).get_strategy().job_search_strategy == "high_volume"
    event = db.scalar(select(ActivityEvent).where(ActivityEvent.event_type == "job_search_strategy_changed"))
    assert event is not None
    assert event.metadata_json == {"from": "balanced", "to": "high_volume"}


def test_custom_status_lifecycle_and_transactional_migration(db: Session) -> None:
    profile_with_resume(db)
    workspace = WorkspaceService(db)
    defaults = workspace.list_statuses()
    custom = workspace.create_status(ApplicationStatusCreate(label="一面"))
    renamed = workspace.update_status(custom.id, ApplicationStatusUpdate(label="技术一面", sort_order=45))
    assert renamed.label == "技术一面"
    job = JobService(db, get_settings()).create(job_payload())
    JobService(db, get_settings()).update(job.id, JobUpdate(application_status_id=custom.id))
    with pytest.raises(WorkspaceConflictError, match="选择迁移"):
        workspace.delete_status(custom.id, None)
    target = next(item for item in defaults if item.key == "interview")
    result = workspace.delete_status(custom.id, target.id)
    assert result.migrated_jobs == 1
    persisted = db.get(Job, job.id)
    assert persisted is not None and persisted.application_status_id == target.id
    assert persisted.status == "Interview"
    with pytest.raises(WorkspaceConflictError, match="默认状态"):
        workspace.delete_status(target.id, None)


def test_plan_crud_completion_job_relation_and_job_delete_set_null(db: Session) -> None:
    profile_with_resume(db)
    job = JobService(db, get_settings()).create(job_payload())
    workspace = WorkspaceService(db)
    plan = workspace.create_plan(PlanItemCreate(
        title="修改岗位简历", date=datetime.now(UTC).date(), time_optional="09:30",
        job_id=job.id, type="resume", notes="只使用真实证据",
    ))
    assert plan.job is not None and plan.job.id == job.id
    done = workspace.update_plan(plan.id, PlanItemUpdate(status="done"))
    assert done.status == "done" and done.completed_at is not None
    todo = workspace.update_plan(plan.id, PlanItemUpdate(status="todo", title="完善岗位简历"))
    assert todo.completed_at is None
    JobService(db, get_settings()).delete(job.id)
    db.expire_all()
    stored = db.get(PlanItem, plan.id)
    assert stored is not None and stored.job_id is None
    workspace.delete_plan(plan.id)
    assert db.get(PlanItem, plan.id) is None


class DynamicMatcher:
    PROMPT_VERSION = RequirementMatcher.PROMPT_VERSION
    SCHEMA_VERSION = RequirementMatcher.SCHEMA_VERSION

    def __init__(self):
        self.client = Mock(model=active_matcher_model(get_settings()))
        self.calls = 0

    def analyze(self, requirements, evidence):
        self.calls += 1
        req = requirements.requirements[0]
        source_id = next(iter(evidence.by_catalog_id))
        return FitAnalysisOutput(
            summary="证据支持岗位要求。",
            requirement_matches=[RequirementMatchOutput(
                requirement_id=req.requirement_id, importance="Critical",
                is_hard_requirement=False, hard_requirement_category="none",
                match_status="Strong", reason="现有 AI 产品经历支持。", confidence="High",
                evidence_source_ids=[source_id],
            )],
            suggested_preparation=[PreparationOutput(title="突出 AI 产品", action="前置已有 AI 产品事实。", priority="High", requirement_ids=[req.requirement_id])],
        )


def test_preview_promotes_exact_analysis_without_second_matcher_call(db: Session) -> None:
    profile_with_resume(db)
    matcher = DynamicMatcher()
    preview = FitAnalysisService(db, get_settings()).analyze_preview(job_payload().structured_jd, matcher)  # type: ignore[arg-type]
    assert preview.artifact_token
    payload = job_payload().model_copy(update={"preview_artifact_token": preview.artifact_token})
    created = JobService(db, get_settings()).create(payload)
    assert created.analysis_promoted is True
    assert created.match_score == preview.match_score
    stored = db.scalar(select(JobAnalysis).where(JobAnalysis.job_id == created.id))
    assert stored is not None and stored.match_score == preview.match_score
    assert matcher.calls == 1


def test_preview_not_promoted_after_candidate_evidence_changes(db: Session) -> None:
    profile_with_resume(db)
    matcher = DynamicMatcher()
    preview = FitAnalysisService(db, get_settings()).analyze_preview(job_payload().structured_jd, matcher)  # type: ignore[arg-type]
    profile = ProfileService(db).get_profile()
    ProfileService(db).add_fact(profile.experiences[0].id, "A newly confirmed fact.", True)
    created = JobService(db, get_settings()).create(job_payload().model_copy(update={"preview_artifact_token": preview.artifact_token}))
    assert created.analysis_promoted is False
    assert db.scalar(select(JobAnalysis).where(JobAnalysis.job_id == created.id)) is None


def test_preview_not_promoted_after_candidate_identity_changes(db: Session) -> None:
    profile_with_resume(db)
    matcher = DynamicMatcher()
    preview = FitAnalysisService(db, get_settings()).analyze_preview(
        job_payload().structured_jd, matcher  # type: ignore[arg-type]
    )
    ProfileService(db).update_candidate_identity("graduate", 2027)
    created = JobService(db, get_settings()).create(
        job_payload().model_copy(update={"preview_artifact_token": preview.artifact_token})
    )
    assert created.analysis_promoted is False
    assert db.scalar(select(JobAnalysis).where(JobAnalysis.job_id == created.id)) is None


@pytest.mark.parametrize("mutation", ["expired", "version", "jd"])
def test_preview_promotion_rejects_expired_version_or_jd_mismatch(db: Session, mutation: str) -> None:
    profile_with_resume(db)
    preview = FitAnalysisService(db, get_settings()).analyze_preview(job_payload().structured_jd, DynamicMatcher())  # type: ignore[arg-type]
    assert preview.artifact_token
    payload = job_payload()
    if mutation in {"expired", "version"}:
        artifact = preview_analysis_store.get(preview.artifact_token)
        assert artifact is not None
        artifact = replace(
            artifact,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        ) if mutation == "expired" else replace(artifact, matcher_prompt_version="old-version")
        preview_analysis_store.put(artifact)
    else:
        changed = payload.structured_jd.model_copy(update={
            "key_requirements": [KeyRequirement(
                title="Changed requirement", explanation="Different normalized JD", priority="high"
            )]
        })
        payload = payload.model_copy(update={"structured_jd": changed})
    created = JobService(db, get_settings()).create(payload.model_copy(update={"preview_artifact_token": preview.artifact_token}))
    assert created.analysis_promoted is False


def test_workspace_api_rejects_invalid_strategy_and_plan_job() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing = sessionmaker(bind=engine, expire_on_commit=False)
    def override_db():
        with testing() as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        assert client.patch("/api/workspace/strategy", json={"job_search_strategy": "fast"}).status_code == 422
        response = client.post("/api/workspace/plan-items", json={"title": "Test", "date": str(datetime.now(UTC).date()), "job_id": 999, "type": "other"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
