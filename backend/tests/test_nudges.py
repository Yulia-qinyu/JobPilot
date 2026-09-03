"""Smart Nudge engine: deterministic, strategy-aware, zero-LLM."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db.base import Base
from app.db.models import (
    Job,
    JobAnalysis,
    JobDecision,
    Resume,
    ResumeTailoring,
    UserProfile,
)
from app.db.session import get_db
from app.main import app
from app.services.nudge_service import NudgeService

TODAY = date(2026, 9, 3)


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    profile = UserProfile(id=1, job_search_strategy="balanced")
    session.add(profile)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class FixedNudgeService(NudgeService):
    def _today(self) -> date:
        return TODAY


def set_strategy(db: Session, strategy: str) -> None:
    db.get(UserProfile, 1).job_search_strategy = strategy
    db.commit()


_job_seq = [0]


def make_job(
    db: Session,
    *,
    company: str = "Acme",
    status: str = "Interested",
    match_score: int | None = None,
    updated_days_ago: int = 0,
    created_days_ago: int = 0,
    interview_in_days: int | None = None,
    with_analysis: bool = False,
    eligibility: str | None = None,
    blocking: list[str] | None = None,
    unknown: list[str] | None = None,
    final_decision: str | None = None,
    tailoring_status: str | None = None,
) -> Job:
    _job_seq[0] += 1
    n = _job_seq[0]
    updated_at = datetime(TODAY.year, TODAY.month, TODAY.day, tzinfo=UTC) - timedelta(
        days=updated_days_ago
    )
    created_at = datetime(TODAY.year, TODAY.month, TODAY.day, tzinfo=UTC) - timedelta(
        days=created_days_ago
    )
    job = Job(
        user_profile_id=1,
        company=company,
        role="Engineer",
        original_jd="jd " * 20,
        structured_jd={"requirement_taxonomy_version": "v2"},
        source_content_hash=f"hash-{n}",
        status=status,
        match_score=match_score,
        created_at=created_at,
        updated_at=updated_at,
        interview_date=(TODAY + timedelta(days=interview_in_days))
        if interview_in_days is not None
        else None,
    )
    db.add(job)
    db.flush()
    if with_analysis or match_score is not None:
        db.add(
            JobAnalysis(
                job_id=job.id,
                resume_hash="r",
                experience_bank_hash="e",
                structured_jd_hash="j",
                matcher_model="qwen3.8-max",
                matcher_prompt_version="job-fit-v3-rubric-refined-v2",
                matcher_schema_version="fit-analysis-wire-v2",
                match_score=match_score,
                recommendation="Apply",
                summary="ok",
                requirement_matches=[],
                strengths=[],
                gaps=[],
                suggested_preparation=[],
            )
        )
    if (
        eligibility is not None
        or blocking is not None
        or unknown is not None
        or final_decision is not None
    ):
        db.add(
            JobDecision(
                job_id=job.id,
                auto_role_family="software",
                effective_role_family="software",
                role_classification_confidence="High",
                classifier_version="v1",
                auto_eligibility_status=eligibility or "Unknown",
                effective_eligibility_status=eligibility or "Unknown",
                blocking_requirements=blocking or [],
                unknown_requirements=unknown or [],
                target_role_fit="Primary",
                pre_match_decision="WorthAnalyzing",
                final_decision=final_decision,
                candidate_hash="c",
                target_roles_hash="t",
                job_input_hash="ji",
                analysis_hash="a",
                engine_version="v1",
            )
        )
    if tailoring_status is not None:
        resume = db.query(Resume).filter(Resume.user_profile_id == 1).first()
        if resume is None:
            resume = Resume(
                user_profile_id=1,
                original_filename="r.docx",
                extracted_text="text",
                structured_profile={},
            )
            db.add(resume)
            db.flush()
        db.add(
            ResumeTailoring(
                job_id=job.id,
                source_resume_id=resume.id,
                status=tailoring_status,
                resume_hash="r",
                experience_bank_hash="e",
                structured_jd_hash="j",
                analysis_hash="a",
                plan_hash="p",
            )
        )
    db.commit()
    return job


def run(db: Session):
    return FixedNudgeService(db, Settings()).list_nudges()


# --- A. strategy differences -------------------------------------------
def test_strategy_changes_which_nudges_fire(db: Session) -> None:
    # A strong match sitting 3 days idle: fires for balanced (threshold 70,
    # stale 3) but not for focused (threshold 80).
    make_job(db, match_score=75, updated_days_ago=3, created_days_ago=3)
    set_strategy(db, "balanced")
    assert [n.type for n in run(db)] == ["high_match_stale"]
    set_strategy(db, "focused")
    assert run(db) == []


# --- B. high-match stale: score + stale thresholds --------------------
def test_high_match_stale_requires_score_and_staleness(db: Session) -> None:
    set_strategy(db, "balanced")
    make_job(db, company="LowScore", match_score=50, updated_days_ago=10, created_days_ago=10)
    make_job(db, company="Fresh", match_score=90, updated_days_ago=1, created_days_ago=1)
    hi = make_job(
        db, company="Ripe", match_score=88, updated_days_ago=5, created_days_ago=5
    )
    types = {(n.type, n.job_id) for n in run(db)}
    assert ("high_match_stale", hi.id) in types
    assert not any(t == "high_match_stale" and j != hi.id for t, j in types)


def test_eligibility_blocker_suppresses_push_to_apply(db: Session) -> None:
    set_strategy(db, "balanced")
    make_job(
        db,
        match_score=90,
        updated_days_ago=6,
        created_days_ago=6,
        eligibility="Ineligible",
        blocking=["需要 5 年经验"],
    )
    nudges = run(db)
    assert all(n.type != "high_match_stale" for n in nudges)


# --- C. eligibility review -------------------------------------------
def test_eligibility_review_fires_on_unknown_and_clears_when_resolved(db: Session) -> None:
    set_strategy(db, "balanced")
    job = make_job(
        db,
        match_score=90,
        updated_days_ago=6,
        created_days_ago=6,
        eligibility="PossiblyEligible",
        unknown=["是否接受该地点"],
    )
    nudges = run(db)
    assert nudges[0].type == "eligibility_review"
    assert nudges[0].job_id == job.id
    assert nudges[0].reason["unknown_requirements"] == ["是否接受该地点"]
    # Resolve it.
    db.get(JobDecision, job.decision.id).effective_eligibility_status = "Eligible"
    db.get(JobDecision, job.decision.id).unknown_requirements = []
    db.commit()
    assert all(n.type != "eligibility_review" for n in run(db))


# --- D. dedupe: one nudge per job ------------------------------------
def test_one_nudge_per_job_keeps_highest_priority(db: Session) -> None:
    set_strategy(db, "balanced")
    # Qualifies for eligibility_review (P1) and would also qualify for
    # stale_decision (P2) — only the P1 one survives.
    job = make_job(
        db,
        match_score=40,
        updated_days_ago=10,
        created_days_ago=10,
        eligibility="Unknown",
        unknown=["工作签证"],
    )
    nudges = [n for n in run(db) if n.job_id == job.id]
    assert len(nudges) == 1
    assert nudges[0].type == "eligibility_review"


# --- D2. ready-to-apply (N7) ---------------------------------------
def test_ready_to_apply_fires_when_tailored_resume_accepted(db: Session) -> None:
    set_strategy(db, "balanced")
    ready = make_job(db, company="Ready", updated_days_ago=1, created_days_ago=3, tailoring_status="Accepted")
    make_job(db, company="Drafting", updated_days_ago=1, created_days_ago=3, tailoring_status="DraftReady")
    by_job = {n.job_id: n for n in run(db)}
    assert by_job[ready.id].type == "ready_to_apply"
    assert all(n.type != "ready_to_apply" for jid, n in by_job.items() if jid != ready.id)
    # focused treats resume preparation as higher priority than balanced does.
    set_strategy(db, "focused")
    focused_ready = next(n for n in run(db) if n.type == "ready_to_apply")
    set_strategy(db, "balanced")
    balanced_ready = next(n for n in run(db) if n.type == "ready_to_apply")
    assert focused_ready.priority < balanced_ready.priority


# --- E. top-3 deterministic -----------------------------------------
def test_returns_at_most_three_in_stable_order(db: Session) -> None:
    set_strategy(db, "balanced")
    make_job(db, company="A", match_score=95, updated_days_ago=9, created_days_ago=9)
    make_job(db, company="B", match_score=94, updated_days_ago=9, created_days_ago=9)
    make_job(db, company="C", match_score=93, updated_days_ago=9, created_days_ago=9)
    make_job(db, company="D", match_score=92, updated_days_ago=9, created_days_ago=9)
    make_job(db, company="E", interview_in_days=1, created_days_ago=30)
    first = run(db)
    assert len(first) == 3
    assert first[0].type == "interview_soon"  # P0 wins
    assert [n.job_id for n in first] == [n.job_id for n in run(db)]  # deterministic


# --- F. no-new-jobs: strategy gating -------------------------------
def test_no_new_jobs_enabled_for_high_volume_and_balanced_only(db: Session) -> None:
    make_job(db, created_days_ago=8, updated_days_ago=8)
    for strategy, expected in [
        ("high_volume", True),
        ("balanced", True),
        ("focused", False),
        ("interview_first", False),
    ]:
        set_strategy(db, strategy)
        fired = any(n.type == "no_new_jobs" for n in run(db))
        assert fired is expected, strategy


# --- G. GET does not mutate --------------------------------------
def test_get_nudges_endpoint_is_read_only(db: Session) -> None:
    make_job(db, match_score=90, updated_days_ago=6, created_days_ago=6)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: Settings()
    try:
        client = TestClient(app)
        before = client.get("/api/nudges")
        assert before.status_code == 200
        assert isinstance(before.json(), list)
        after = client.get("/api/nudges")
        assert before.json() == after.json()
    finally:
        app.dependency_overrides.clear()

    from app.db.models import ActivityEvent

    assert db.query(ActivityEvent).count() == 0


# --- H. zero LLM ---------------------------------------------------
def test_engine_makes_no_provider_calls(db: Session, monkeypatch) -> None:
    import app.services.matcher_client as mc

    monkeypatch.setattr(
        mc.httpx, "post", lambda *a, **k: pytest.fail("nudge engine called a provider")
    )
    import app.services.claude_client as cc

    monkeypatch.setattr(
        cc.Anthropic,
        "__init__",
        lambda *a, **k: pytest.fail("nudge engine constructed an LLM client"),
    )
    set_strategy(db, "high_volume")
    make_job(db, match_score=80, updated_days_ago=4, created_days_ago=4)
    make_job(db, interview_in_days=2, created_days_ago=20)
    make_job(db, eligibility="Unknown", unknown=["x"], updated_days_ago=1)
    assert isinstance(run(db), list)


def test_empty_pool_returns_empty_or_cadence_only(db: Session) -> None:
    set_strategy(db, "focused")  # cadence disabled
    assert run(db) == []
