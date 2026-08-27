from datetime import date
from unittest.mock import Mock

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import Job
from app.schemas.analysis import JDRequirements, KeyRequirement
from app.schemas.job import JobCreate, JobUpdate
from app.services.job_service import JobService


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
