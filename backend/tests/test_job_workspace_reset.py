import json

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Experience,
    ExperienceFact,
    Job,
    JobAnalysis,
    JobDecision,
    JobImportSession,
    Resume,
    ResumeTailoring,
    TargetCompany,
    TargetRole,
    UserProfile,
)
from app.schemas.analysis import JDRequirements
from app.services.job_sources.base import ImportedJobDraft
from app.services.job_workspace_reset import JobWorkspaceResetService
from app.services.workspace_job_upsert import WorkspaceJobUpsertService
from scripts.reset_job_workspace import assert_local_reset_allowed


@pytest.fixture
def db_and_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_workspace(db)
        db.commit()
        yield db, engine
    Base.metadata.drop_all(engine)


def seed_workspace(db: Session) -> None:
    profile = UserProfile(id=1, preferred_location="北京")
    db.add(profile)
    db.flush()
    resume = Resume(
        user_profile_id=profile.id,
        original_filename="master.docx",
        extracted_text="verified resume",
        structured_profile={},
    )
    experience = Experience(
        user_profile_id=profile.id,
        organization="Example",
        title="Product Manager",
        experience_type="work",
        sort_order=0,
    )
    db.add_all(
        [
            resume,
            experience,
            TargetCompany(user_profile_id=profile.id, name="小米"),
            TargetRole(
                user_profile_id=profile.id,
                name="AI 产品经理",
                priority="primary",
                auto_role_family="ai_product",
                role_family="ai_product",
            ),
        ]
    )
    db.flush()
    db.add(
        ExperienceFact(
            experience_id=experience.id,
            text="Built an AI product.",
            source_type="manual",
            confirmed=True,
        )
    )
    job = Job(
        user_profile_id=profile.id,
        company="ByteDance",
        role="AI Product Manager",
        original_jd="JD",
        structured_jd={},
        source_content_hash="a" * 64,
        source="bytedance",
        external_job_id="legacy-1",
    )
    db.add(job)
    db.flush()
    db.add_all(
        [
            JobAnalysis(
                job_id=job.id,
                resume_hash="r" * 64,
                experience_bank_hash="e" * 64,
                structured_jd_hash="j" * 64,
                matcher_model="test",
                matcher_prompt_version="v1",
                matcher_schema_version="v1",
                match_score=80,
                recommendation="Apply",
                summary="summary",
                requirement_matches=[],
                strengths=[],
                gaps=[],
                suggested_preparation=[],
            ),
            JobDecision(
                job_id=job.id,
                auto_role_family="ai_product",
                effective_role_family="ai_product",
                role_classification_confidence="High",
                role_classification_reasons=[],
                classifier_version="v1",
                auto_eligibility_status="Unknown",
                effective_eligibility_status="Unknown",
                eligibility_reasons=[],
                blocking_requirements=[],
                unknown_requirements=[],
                target_role_fit="Primary",
                pre_match_decision="WorthAnalyzing",
                decision_reasons=[],
                candidate_hash="c" * 64,
                target_roles_hash="t" * 64,
                job_input_hash="i" * 64,
                engine_version="v1",
            ),
            ResumeTailoring(
                job_id=job.id,
                source_resume_id=resume.id,
                status="PlanReady",
                tailoring_plan={},
                generated_draft={},
                validation_results={},
                resume_hash="r" * 64,
                experience_bank_hash="e" * 64,
                structured_jd_hash="j" * 64,
                analysis_hash="a" * 64,
                plan_hash="p" * 64,
                guardrail_version="v1",
            ),
            JobImportSession(
                user_profile_id=profile.id,
                source="bytedance",
                search_url="https://jobs.bytedance.com/experienced/position",
                search_url_hash="s" * 64,
                status="Completed",
                stage="Completed",
                result_job_ids=[job.id],
                failure_details=[],
            ),
        ]
    )


def test_local_only_guard() -> None:
    assert_local_reset_allowed("development", "postgresql://u:p@localhost:5433/jobpilot")
    assert_local_reset_allowed("test", "sqlite://")
    with pytest.raises(RuntimeError, match="JOBPILOT_ENVIRONMENT"):
        assert_local_reset_allowed("production", "postgresql://u:p@localhost/db")
    with pytest.raises(RuntimeError, match="not local"):
        assert_local_reset_allowed("development", "postgresql://u:p@db.example.com/prod")


def test_reset_deletes_workspace_and_preserves_candidate_data(db_and_engine) -> None:
    db, _engine = db_and_engine
    service = JobWorkspaceResetService(db)
    candidate_before = service.candidate_counts()
    deleted = service.reset()
    db.commit()

    assert deleted.jobs == 1
    assert all(value == 0 for value in service.workspace_counts().as_dict().values())
    assert service.candidate_counts() == candidate_before
    assert db.scalar(select(func.count()).select_from(ExperienceFact)) == 1

    outcome = WorkspaceJobUpsertService(db).upsert(
        ImportedJobDraft(
            source="bytedance",
            external_job_id="new-1",
            external_job_code="A1",
            company="ByteDance",
            role="AI Product Manager",
            location="北京",
            recruitment_type="社招",
            source_url="https://jobs.bytedance.com/job/new-1",
            original_jd="职位描述",
            structured_jd=JDRequirements(role="AI Product Manager"),
            published_date=None,
            source_metadata={},
            source_content_hash="n" * 64,
        )
    )
    db.commit()
    assert outcome.outcome == "created"
    assert service.workspace_counts().jobs == 1
    assert service.candidate_counts() == candidate_before


def test_reset_rolls_back_if_any_delete_fails(db_and_engine) -> None:
    db, engine = db_and_engine

    def fail_jobs_delete(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.lower().startswith("delete from jobs"):
            raise RuntimeError("simulated delete failure")

    event.listen(engine, "before_cursor_execute", fail_jobs_delete)
    try:
        with pytest.raises(RuntimeError, match="simulated"), db.begin():
            JobWorkspaceResetService(db).reset()
    finally:
        event.remove(engine, "before_cursor_execute", fail_jobs_delete)
    db.rollback()
    assert JobWorkspaceResetService(db).workspace_counts().jobs == 1
    assert JobWorkspaceResetService(db).workspace_counts().job_analyses == 1
    assert JobWorkspaceResetService(db).workspace_counts().resume_tailorings == 1


def test_count_models_are_json_serializable(db_and_engine) -> None:
    db, _engine = db_and_engine
    service = JobWorkspaceResetService(db)
    assert json.loads(json.dumps(service.workspace_counts().as_dict()))["jobs"] == 1
