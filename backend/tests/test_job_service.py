from datetime import date
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import ActivityEvent, Job, JobAnalysis
from app.schemas.analysis import JDRequirements, KeyRequirement
from app.schemas.job import JobCreate, JobQuickCreate, JobUpdate
from app.services.job_service import JobService
from app.services.workspace_service import WorkspaceService


def make_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def requirements(role: str = "AI Product Manager") -> JDRequirements:
    return JDRequirements(
        role=role,
        company="Example AI",
        location="Sydney",
        role_summary="负责把 AI 能力转化为可验证的产品价值。",
        key_requirements=[
            KeyRequirement(
                title="AI 产品经验",
                explanation="能够定义并交付 AI 产品。",
                category="product",
                priority="high",
            )
        ],
        knowledge_topics=["LLM", "AI Evaluation"],
        responsibilities=["Own the roadmap"],
        required_skills=["Product strategy"],
        preferred_skills=["SQL"],
    )


def create_payload(status: str = "Interested") -> JobCreate:
    return JobCreate(
        company="Example AI",
        role="AI Product Manager",
        location="Sydney",
        original_jd="A long fictional job description that is sufficiently detailed for safe testing.",
        structured_jd=requirements(),
        published_date=date(2026, 8, 20),
        status=status,
    )


def test_create_edit_detail_and_persist_across_sessions() -> None:
    engine = make_engine()
    with Session(engine) as db:
        created = JobService(db, Settings()).create(create_payload())
        assert created.id
        assert created.structured_jd.role_summary
        assert created.structured_jd.knowledge_topics == ["LLM", "AI Evaluation"]
        updated = JobService(db, Settings()).update(
            created.id,
            JobUpdate(
                company="Example AI Labs",
                status="Preparing",
                application_date=date(2026, 8, 21),
                next_stage="准备材料",
                interview_date=date(2026, 9, 1),
                notes="Follow up next week",
            ),
        )
        assert updated.company == "Example AI Labs"
        assert updated.status == "Preparing"
        assert updated.structured_jd.company == "Example AI Labs"

    with Session(engine) as reloaded_db:
        reloaded = JobService(reloaded_db, Settings()).get(created.id)
        assert reloaded.status == "Preparing"
        assert reloaded.application_date == date(2026, 8, 21)
        assert reloaded.next_stage == "准备材料"
        assert reloaded.interview_date == date(2026, 9, 1)
        assert reloaded.notes == "Follow up next week"


def test_manual_status_change_updates_timestamp_once_and_noop_is_stable() -> None:
    engine = make_engine()
    with Session(engine) as db:
        created = JobService(db, Settings()).create(create_payload())
        statuses = WorkspaceService(db).ensure_default_statuses()
        applied = next(item for item in statuses if item.key == "applied")

        JobService(db, Settings()).update(
            created.id, JobUpdate(application_status_id=applied.id)
        )
        stored = db.get(Job, created.id)
        assert stored is not None
        changed_at = stored.application_status_changed_at
        assert changed_at is not None
        event_count = db.scalar(
            select(func.count(ActivityEvent.id)).where(
                ActivityEvent.job_id == created.id,
                ActivityEvent.event_type == "application_status_changed",
            )
        )

        JobService(db, Settings()).update(
            created.id, JobUpdate(application_status_id=applied.id)
        )
        db.refresh(stored)
        assert stored.application_status_changed_at == changed_at
        assert db.scalar(
            select(func.count(ActivityEvent.id)).where(
                ActivityEvent.job_id == created.id,
                ActivityEvent.event_type == "application_status_changed",
            )
        ) == event_count


def test_quick_add_creates_workspace_job_without_analysis() -> None:
    engine = make_engine()
    with Session(engine) as db, patch(
        "app.services.job_service.safe_recompute_job_decisions"
    ) as recompute:
        statuses = WorkspaceService(db).ensure_default_statuses()
        to_apply = next(item for item in statuses if item.key == "to_apply")
        created = JobService(db, Settings()).create_quick(
            JobQuickCreate(
                company="Example",
                role="产品经理",
                location="北京",
                application_date=date(2026, 9, 8),
                application_status_id=to_apply.id,
            )
        )
        assert created.company == "Example"
        assert created.role == "产品经理"
        assert created.location == "北京"
        assert created.application_date == date(2026, 9, 8)
        assert created.application_status_id == to_apply.id
        assert created.status == "Preparing"
        assert created.original_jd == ""
        assert created.source == "manual"
        assert created.source_metadata == {"creation_mode": "quick_add"}
        assert db.scalar(select(JobAnalysis).where(JobAnalysis.job_id == created.id)) is None
        recompute.assert_not_called()


def test_quick_add_defaults_to_interested_with_optional_location() -> None:
    engine = make_engine()
    with Session(engine) as db:
        created = JobService(db, Settings()).create_quick(
            JobQuickCreate(company="Example", role="产品经理")
        )
        assert created.location is None
        assert created.application_date is None
        assert created.status == "Interested"
        assert created.application_status_label == "感兴趣"


def test_dashboard_uses_application_funnel_metric_semantics() -> None:
    engine = make_engine()
    statuses = [
        "Interested",
        "Preparing",
        "Applied",
        "OA",
        "Interview",
        "Final Interview",
        "Offer",
        "Rejected",
        "Withdrawn",
    ]
    with Session(engine) as db:
        service = JobService(db, Settings())
        for index, status in enumerate(statuses):
            payload = create_payload(status)
            payload.company = f"Company {index}"
            service.create(payload)
        counts = service.dashboard().counts

    assert counts.total == 9
    assert counts.applied == 6
    assert counts.interviews == 2
    assert counts.offers == 1


def test_filtering_and_sorting_keep_null_scores_last() -> None:
    engine = make_engine()
    with Session(engine) as db:
        service = JobService(db, Settings())
        first = service.create(create_payload("Interview"))
        second_payload = create_payload("Final Interview")
        second_payload.company = "A Company"
        second = service.create(second_payload)
        third_payload = create_payload("Applied")
        third_payload.company = "Z Company"
        service.create(third_payload)

        interview_jobs = service.list("Interview", "company")
        assert [item.id for item in interview_jobs] == [second.id, first.id]
        assert all(item.status in {"Interview", "Final Interview"} for item in interview_jobs)
        assert all(item.match_score is None for item in service.list("all", "match_score"))


def test_paste_jd_preview_calls_existing_parser_once_and_keeps_quick_overview() -> None:
    engine = make_engine()
    parser = Mock()
    parser.parse.return_value = requirements()
    parser.client.model = "test-model"
    parser.PROMPT_VERSION = "prompt-v2"
    parser.SCHEMA_VERSION = "schema-v2"
    text = "A long fictional pasted JD with responsibilities and qualifications for an AI role."
    with Session(engine) as db:
        preview = JobService(db, Settings()).preview_jd(text, parser)

    parser.parse.assert_called_once_with(None, text)
    assert preview.structured_jd.role_summary == "负责把 AI 能力转化为可验证的产品价值。"
    assert preview.parser_model == "test-model"
    assert len(preview.source_content_hash) == 64


def test_repeated_manual_add_is_idempotent_and_delete_removes_workspace_job() -> None:
    engine = make_engine()
    with Session(engine) as db:
        service = JobService(db, Settings())
        payload = create_payload()
        payload.source_content_hash = service.content_hash(payload.original_jd)
        first = service.create(payload)
        repeated = service.create(payload)
        assert repeated.id == first.id
        assert db.scalar(select(func.count(Job.id))) == 1

        service.delete(first.id)
        assert db.scalar(select(func.count(Job.id))) == 0
