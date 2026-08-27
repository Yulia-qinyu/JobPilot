from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import (
    ActivityEvent,
    ApplicationStatusDefinition,
    DailyAdviceSnapshot,
    Job,
    PlanItem,
)
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.planning import (
    AddAdviceToPlanRequest,
    ApplicationSummary,
    CandidateIdentitySummary,
    DailyAdviceItemOutput,
    DailyAdviceOutput,
    PlanningCandidate,
    PlanningContext,
    PlanningGenerateRequest,
    PlanningJobSummary,
    PlanningPlanItem,
    PlanningSignals,
    PlanSummary,
)
from app.schemas.workspace import PlanItemUpdate
from app.services.application_management_agent import ApplicationManagementAgent
from app.services.claude_client import ClaudeServiceError
from app.services.planning_candidate_service import PlanningCandidateService
from app.services.planning_context_service import PlanningContextService
from app.services.planning_service import PlanningService
from app.services.workspace_service import WorkspaceService


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    ProfileRepository(session).ensure_default_profile()
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class PlanningClient:
    def __init__(self, output: DailyAdviceOutput | None = None, fail: bool = False):
        self.model = "planning-test-model"
        self.calls = 0
        self.fail = fail
        self.output = output
        self.last_call_metrics = {}

    def generate(self, **_kwargs):
        self.calls += 1
        self.last_call_metrics = {
            "model": self.model,
            "input_tokens": 640,
            "output_tokens": 180,
            "elapsed_seconds": 0.12,
        }
        if self.fail:
            raise ClaudeServiceError("timeout")
        assert self.output is not None
        return self.output


def local_today() -> date:
    return datetime.now(ZoneInfo("Australia/Sydney")).date()


def add_job(
    db: Session,
    *,
    company: str,
    role: str,
    status_key: str,
    match_score: int | None = None,
    interview_date: date | None = None,
) -> Job:
    statuses = WorkspaceService(db).ensure_default_statuses()
    status = next(item for item in statuses if item.key == status_key)
    job = Job(
        user_profile_id=DEFAULT_PROFILE_ID,
        company=company,
        role=role,
        location="北京",
        original_jd=f"{company} {role} full private JD that must not enter planning context",
        structured_jd={
            "company": company,
            "role": role,
            "location": "北京",
            "key_requirements": [],
        },
        status=status.legacy_status or "Interested",
        application_status_id=status.id,
        match_score=match_score,
        interview_date=interview_date,
        source_content_hash=f"hash-{company}-{role}",
    )
    db.add(job)
    db.flush()
    return job


def advice_for(candidate_id: str, *, job_id: int | None = None) -> DailyAdviceOutput:
    return DailyAdviceOutput(
        summary="今天优先完成最接近行动的事项。",
        items=[
            DailyAdviceItemOutput(
                id=candidate_id,
                priority="high",
                action_type="apply",
                title="推进岗位投递",
                reason="岗位当前处于待投递状态。",
                related_job_id=job_id,
                suggested_plan_type="application",
                suggested_date=local_today(),
            )
        ],
    )


def test_context_is_compact_bounded_and_hashes_only_planning_state(db: Session) -> None:
    today = local_today()
    for index in range(18):
        add_job(
            db,
            company=f"Company {index}",
            role=f"Role {index}",
            status_key="interested",
        )
    for index in range(35):
        db.add(
            PlanItem(
                user_profile_id=DEFAULT_PROFILE_ID,
                title=f"Plan {index}",
                date=today + timedelta(days=index % 7),
                type="other",
                status="todo",
                created_by="user",
            )
        )
    for index in range(35):
        db.add(
            ActivityEvent(
                user_profile_id=DEFAULT_PROFILE_ID,
                event_type="job_added",
                metadata_json={"index": index},
            )
        )
    db.commit()
    service = PlanningContextService(db, Settings())
    context = service.build()
    payload = context.model_dump_json()
    assert len(context.active_jobs) == 15
    assert len(context.plan_items) == 30
    assert len(context.recent_activity) == 30
    assert "full private JD" not in payload
    assert "structured_jd" not in payload
    assert "extracted_text" not in payload
    assert service.context_hash(context) == service.context_hash(service.build())
    before = service.context_hash(context)
    db.add(
        PlanItem(
            user_profile_id=DEFAULT_PROFILE_ID,
            title="Planning relevant change",
            date=today,
            type="other",
            status="todo",
            created_by="user",
        )
    )
    db.commit()
    assert service.context_hash(service.build()) != before


def candidate_context(strategy: str, *, interview: bool = False) -> PlanningContext:
    today = local_today()
    jobs = [
        PlanningJobSummary(
            job_id=1,
            company="A",
            title="AI Product Manager",
            status_key="to_apply",
            status_label="待投递",
            status_category="to_apply",
            match_score=85,
            has_valid_analysis=True,
            tailored_resume_status=None,
            application_date=None,
            interview_date=None,
            days_in_current_status=3,
            next_known_date=None,
        )
    ]
    if interview:
        jobs.append(
            PlanningJobSummary(
                job_id=2,
                company="B",
                title="Product Manager",
                status_key="interview",
                status_label="一面",
                status_category="interview",
                match_score=72,
                has_valid_analysis=True,
                tailored_resume_status="Accepted",
                application_date=today - timedelta(days=5),
                interview_date=today + timedelta(days=1),
                days_in_current_status=1,
                next_known_date=today + timedelta(days=1),
            )
        )
    return PlanningContext(
        as_of=today,
        timezone="Australia/Sydney",
        job_search_strategy=strategy,
        candidate_identity=CandidateIdentitySummary(
            candidate_type="graduate", graduation_year=2027
        ),
        application_summary=ApplicationSummary(to_apply_count=1),
        active_jobs=jobs,
        plan_summary=PlanSummary(),
        plan_items=[],
        recent_activity=[],
        derived_signals=PlanningSignals(
            days_since_last_job_added=5,
            days_since_last_application=5,
            pending_application_count=1,
            jobs_ready_to_apply_count=1,
            jobs_without_tailored_resume_count=1,
            upcoming_interview_count=int(interview),
            overdue_plan_count=0,
            today_plan_load=0,
            recent_completed_plan_count=0,
        ),
        freshness_metadata={"context_version": "test"},
    )


def test_strategy_changes_deterministic_candidate_order() -> None:
    service = PlanningCandidateService()
    assert service.build(candidate_context("high_volume"))[0].action_type == "apply"
    assert service.build(candidate_context("focused"))[0].action_type == "resume"
    assert (
        service.build(candidate_context("interview_first", interview=True))[0].action_type
        == "interview_prep"
    )
    balanced = [item.action_type for item in service.build(candidate_context("balanced"))]
    assert balanced[:2] == ["apply", "resume"]


def test_existing_interview_plan_prevents_duplicate_interview_candidate() -> None:
    context = candidate_context("interview_first", interview=True)
    context.plan_items = [
        PlanningPlanItem(
            id=40,
            title="准备明天面试",
            date=context.as_of,
            time=None,
            type="interview_prep",
            status="todo",
            related_job_id=2,
            related_job="B · Product Manager",
        )
    ]
    candidates = PlanningCandidateService().build(context)
    related_interview_actions = [
        item
        for item in candidates
        if item.related_job_id == 2
        and item.action_type in {"plan", "interview_prep"}
    ]
    assert [item.id for item in related_interview_actions] == ["plan:40"]
    assert "已记录面试日期" in " ".join(related_interview_actions[0].rationale_facts)


def test_agent_drops_invalid_duplicate_unsafe_and_caps_five() -> None:
    context = candidate_context("balanced")
    candidates = [
        PlanningCandidate(
            id=f"candidate:{index}",
            action_type="review",
            related_job_id=1,
            suggested_plan_type="other",
            suggested_date=context.as_of,
            title=f"Review {index}",
            signal="test",
            urgency=50,
            readiness="ready",
            rationale_facts=["Grounded fact"],
        )
        for index in range(7)
    ]
    items = [
        DailyAdviceItemOutput(
            id=item.id,
            priority="medium",
            action_type=item.action_type,
            title=item.title,
            reason="Grounded fact",
            related_job_id=item.related_job_id,
            suggested_plan_type=item.suggested_plan_type,
            suggested_date=context.as_of,
        )
        for item in candidates
    ]
    items.insert(1, items[0])
    items[2] = items[2].model_copy(update={"title": "自动投递这个岗位"})
    client = PlanningClient(DailyAdviceOutput(summary="test", items=items[:8]))
    result = ApplicationManagementAgent(client).generate(context, candidates)
    assert len(result.output.items) == 5
    assert len({item.id for item in result.output.items}) == 5
    assert all("自动投递" not in item.title for item in result.output.items)
    assert result.validation_drops == 2


def test_all_invalid_or_malformed_output_uses_deterministic_fallback() -> None:
    context = candidate_context("balanced")
    candidates = PlanningCandidateService().build(context)
    invalid = advice_for("unknown", job_id=999)
    result = ApplicationManagementAgent(PlanningClient(invalid)).generate(
        context, candidates
    )
    assert result.fallback_used is True
    assert result.output.items[0].id == candidates[0].id
    failure = ApplicationManagementAgent(PlanningClient(fail=True)).generate(
        context, candidates
    )
    assert failure.fallback_used is True


def test_generate_cache_freshness_replan_and_explicit_advice_to_plan(db: Session) -> None:
    job = add_job(
        db,
        company="Example",
        role="AI Product Manager",
        status_key="to_apply",
    )
    db.commit()
    output = advice_for(f"apply:{job.id}", job_id=job.id)
    client = PlanningClient(output)
    service = PlanningService(db, Settings())

    assert service.get_today().snapshot is None
    generated = service.generate(PlanningGenerateRequest(), client)  # type: ignore[arg-type]
    assert client.calls == 1
    assert generated.snapshot is not None
    assert generated.snapshot.input_tokens == 640
    cached = service.generate(PlanningGenerateRequest(), client)  # type: ignore[arg-type]
    assert cached.snapshot is not None and cached.snapshot.id == generated.snapshot.id
    assert client.calls == 1

    plan = service.add_to_plan(
        generated.snapshot.id,
        f"apply:{job.id}",
        AddAdviceToPlanRequest(),
    )
    assert plan.created_by == "agent_suggestion"
    assert plan.job_id == job.id and plan.type == "application"
    assert db.get(Job, job.id).status == "Preparing"
    repeated = service.add_to_plan(
        generated.snapshot.id,
        f"apply:{job.id}",
        AddAdviceToPlanRequest(),
    )
    assert repeated.id == plan.id
    assert client.calls == 1
    assert service.get_today().is_stale is True

    WorkspaceService(db).update_plan(plan.id, PlanItemUpdate(status="done"))
    assert service.get_today().is_stale is True
    regenerated = service.generate(PlanningGenerateRequest(), client)  # type: ignore[arg-type]
    assert regenerated.snapshot is not None
    assert regenerated.snapshot.id != generated.snapshot.id
    assert client.calls == 2
    assert db.scalar(select(DailyAdviceSnapshot).where(DailyAdviceSnapshot.id == generated.snapshot.id))


def test_empty_context_never_calls_claude(db: Session) -> None:
    client = PlanningClient(fail=True)
    result = PlanningService(db, Settings()).generate(
        PlanningGenerateRequest(), client  # type: ignore[arg-type]
    )
    assert result.empty_context is True
    assert result.snapshot is None
    assert client.calls == 0


def test_custom_status_is_normalized_for_planning(db: Session) -> None:
    custom = ApplicationStatusDefinition(
        user_profile_id=DEFAULT_PROFILE_ID,
        key="custom-first-interview",
        label="一面",
        sort_order=100,
        is_system_default=False,
        is_active=True,
    )
    db.add(custom)
    db.flush()
    job = add_job(db, company="Example", role="PM", status_key="interested")
    job.application_status_id = custom.id
    db.commit()
    context = PlanningContextService(db, Settings()).build()
    planned = next(item for item in context.active_jobs if item.job_id == job.id)
    assert planned.status_label == "一面"
    assert planned.status_category == "interview"
    assert context.application_summary.custom_statuses[0].semantic_category == "interview"
