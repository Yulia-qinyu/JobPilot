"""Strategy-aware Smart Nudge engine.

Deterministic and explainable. Given the user's job-search strategy and the
stored state of their jobs (status, match score, analysis, eligibility decision,
tailored resume), it returns at most three ranked recommendations. There is no
LLM call, nothing is persisted, and ``GET /api/nudges`` never mutates state.

Priority bands:
  P0  time-sensitive        (interview coming up)
  P1  high-value / risk     (strong match sitting idle; eligibility unresolved)
  P2  decision hygiene      (analysed but undecided; tailored resume ready)
  P3  cadence               (no new jobs; analysed backlog piling up)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.db.models import Job, UserProfile
from app.repositories.profile_repository import DEFAULT_PROFILE_ID
from app.schemas.nudge import Nudge, NudgeCta

MAX_NUDGES = 3
INTERVIEW_WINDOW_DAYS = 3

# Job workflow buckets (Job.status is kept in sync with the active application
# status by JobService.update).
EARLY_STATUSES = frozenset({"Interested", "Preparing"})
CLOSED_STATUSES = frozenset({"Rejected", "Withdrawn", "Offer"})

# Lower number = higher urgency. Used only as a deterministic tie-breaker within
# a priority band and for picking the single nudge kept per job.
TYPE_RANK: dict[str, int] = {
    "interview_soon": 0,
    "eligibility_review": 1,
    "high_match_stale": 2,
    "stale_decision": 3,
    "ready_to_apply": 4,
    "no_new_jobs": 5,
    "pending_backlog": 6,
}


@dataclass(frozen=True)
class StrategyRules:
    match_threshold: int
    high_match_stale_days: int
    generic_stale_days: int
    no_new_job_days: int | None
    pending_backlog_threshold: int | None
    ready_to_apply_priority: int
    high_match_priority: int


# Defaults from the product strategy matrix. interview_first intentionally
# disables the cadence nudges and de-prioritises "push this match" so the
# upcoming interview stays the single focus.
STRATEGY_RULES: dict[str, StrategyRules] = {
    "high_volume": StrategyRules(
        match_threshold=60,
        high_match_stale_days=2,
        generic_stale_days=2,
        no_new_job_days=2,
        pending_backlog_threshold=4,
        ready_to_apply_priority=2,
        high_match_priority=1,
    ),
    "focused": StrategyRules(
        match_threshold=80,
        high_match_stale_days=3,
        generic_stale_days=4,
        no_new_job_days=None,
        pending_backlog_threshold=None,
        ready_to_apply_priority=1,
        high_match_priority=1,
    ),
    "balanced": StrategyRules(
        match_threshold=70,
        high_match_stale_days=3,
        generic_stale_days=4,
        no_new_job_days=5,
        pending_backlog_threshold=5,
        ready_to_apply_priority=2,
        high_match_priority=1,
    ),
    "interview_first": StrategyRules(
        match_threshold=75,
        high_match_stale_days=4,
        generic_stale_days=4,
        no_new_job_days=None,
        pending_backlog_threshold=None,
        ready_to_apply_priority=2,
        high_match_priority=2,
    ),
}
DEFAULT_STRATEGY = "balanced"

STRATEGY_LABELS = {
    "high_volume": "高频投递",
    "focused": "重点冲刺",
    "balanced": "平衡模式",
    "interview_first": "面试优先",
}


def rules_for(strategy: str) -> StrategyRules:
    return STRATEGY_RULES.get(strategy, STRATEGY_RULES[DEFAULT_STRATEGY])


class NudgeService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings

    def _today(self) -> date:
        tz = ZoneInfo(self.settings.app_timezone)
        return datetime.now(tz).date()

    def _strategy(self) -> str:
        profile = self.db.get(UserProfile, DEFAULT_PROFILE_ID)
        if profile is None or not profile.job_search_strategy:
            return DEFAULT_STRATEGY
        return profile.job_search_strategy

    def _jobs(self) -> list[Job]:
        return list(
            self.db.scalars(
                select(Job)
                .where(Job.user_profile_id == DEFAULT_PROFILE_ID)
                .options(
                    selectinload(Job.analysis),
                    selectinload(Job.decision),
                    selectinload(Job.resume_tailoring),
                )
                .order_by(Job.id)
            )
        )

    # -- public -----------------------------------------------------------
    def list_nudges(self) -> list[Nudge]:
        today = self._today()
        strategy = self._strategy()
        rules = rules_for(strategy)
        jobs = self._jobs()

        job_candidates: list[Nudge] = []
        for job in jobs:
            job_candidates.extend(self._job_nudges(job, today, strategy, rules))

        # One nudge per job: keep the most urgent (priority, then type rank).
        best_by_job: dict[int, Nudge] = {}
        for nudge in job_candidates:
            current = best_by_job.get(nudge.job_id)  # type: ignore[arg-type]
            if current is None or _sort_key(nudge) < _sort_key(current):
                best_by_job[nudge.job_id] = nudge  # type: ignore[index]

        nudges = list(best_by_job.values())
        nudges.extend(self._pool_nudges(jobs, today, strategy, rules))
        nudges.sort(key=_sort_key)
        return nudges[:MAX_NUDGES]

    # -- per-job rules --------------------------------------------------
    def _job_nudges(
        self, job: Job, today: date, strategy: str, rules: StrategyRules
    ) -> list[Nudge]:
        out: list[Nudge] = []
        status = job.status
        if status in CLOSED_STATUSES:
            return out
        decision = job.decision
        analysis = job.analysis
        stale_days = _days_since(job.updated_at, today)

        eligibility_status = (
            decision.effective_eligibility_status if decision is not None else None
        )
        blocking = list(decision.blocking_requirements) if decision is not None else []
        unknown = list(decision.unknown_requirements) if decision is not None else []
        eligibility_blocked = eligibility_status == "Ineligible" or bool(blocking)
        eligibility_unresolved = (
            eligibility_status in {"PossiblyEligible", "Unknown"} or bool(unknown)
        )

        # N6 INTERVIEW_SOON (P0)
        if job.interview_date is not None:
            days_until = (job.interview_date - today).days
            if 0 <= days_until <= INTERVIEW_WINDOW_DAYS:
                out.append(
                    Nudge(
                        type="interview_soon",
                        priority=0,
                        job_id=job.id,
                        title="面试快到了",
                        message=f"{job.company} 的面试在 {days_until} 天内，安排一次针对性准备。"
                        if days_until
                        else f"{job.company} 今天有面试，做最后一次准备。",
                        reason={
                            "interview_date": job.interview_date.isoformat(),
                            "days_until": days_until,
                            "strategy": strategy,
                        },
                        cta=NudgeCta(type="open_job", target=f"/jobs/{job.id}"),
                    )
                )

        # N3 ELIGIBILITY_REVIEW (P1) — only while still deciding, and only if the
        # question is genuinely open (resolved "Eligible" suppresses it).
        if (
            status in EARLY_STATUSES
            and eligibility_unresolved
            and not eligibility_blocked
        ):
            out.append(
                Nudge(
                    type="eligibility_review",
                    priority=1,
                    job_id=job.id,
                    title="先确认硬性条件",
                    message=f"{job.company} 还有关键条件没确认，投递前先核对是否满足。",
                    reason={
                        "eligibility_status": eligibility_status,
                        "unknown_requirements": unknown[:3],
                        "unknown_requirement_count": len(unknown),
                        "strategy": strategy,
                    },
                    cta=NudgeCta(type="open_job", target=f"/jobs/{job.id}"),
                )
            )

        # N1 HIGH_MATCH_STALE (P1 / P2 for interview_first) — do not nudge to
        # push a job that is eligibility-blocked.
        if (
            status in EARLY_STATUSES
            and analysis is not None
            and job.match_score is not None
            and job.match_score >= rules.match_threshold
            and stale_days >= rules.high_match_stale_days
            and not eligibility_blocked
        ):
            out.append(
                Nudge(
                    type="high_match_stale",
                    priority=rules.high_match_priority,
                    job_id=job.id,
                    title="这个匹配值得推进",
                    message=f"{job.company} 匹配度 {job.match_score}，已经搁置 {stale_days} 天，建议推进。",
                    reason={
                        "match_score": job.match_score,
                        "stale_days": stale_days,
                        "status": status,
                        "strategy": strategy,
                    },
                    cta=NudgeCta(type="open_job", target=f"/jobs/{job.id}"),
                )
            )

        # N2 STALE_DECISION (P2) — analysed, undecided, and not already covered
        # by the high-match nudge (lower / missing score).
        below_high_match = (
            job.match_score is None or job.match_score < rules.match_threshold
        )
        final_decision = decision.final_decision if decision is not None else None
        if (
            status in EARLY_STATUSES
            and analysis is not None
            and below_high_match
            and stale_days >= rules.generic_stale_days
            and final_decision in (None, "Consider")
            and not eligibility_blocked
        ):
            out.append(
                Nudge(
                    type="stale_decision",
                    priority=2,
                    job_id=job.id,
                    title="定个方向",
                    message=f"{job.company} 分析完成后 {stale_days} 天没有进展，决定投递还是搁置。",
                    reason={
                        "stale_days": stale_days,
                        "match_score": job.match_score,
                        "final_decision": final_decision,
                        "strategy": strategy,
                    },
                    cta=NudgeCta(type="open_job", target=f"/jobs/{job.id}"),
                )
            )

        # N7 READY_TO_APPLY (P1 focused / P2 otherwise)
        tailoring = job.resume_tailoring
        if (
            status in EARLY_STATUSES
            and tailoring is not None
            and tailoring.status == "Accepted"
            and not eligibility_blocked
        ):
            out.append(
                Nudge(
                    type="ready_to_apply",
                    priority=rules.ready_to_apply_priority,
                    job_id=job.id,
                    title="简历已就绪",
                    message=f"{job.company} 的定制简历已确认，可以投出去了。",
                    reason={
                        "resume_tailoring_status": tailoring.status,
                        "match_score": job.match_score,
                        "strategy": strategy,
                    },
                    cta=NudgeCta(type="open_job", target=f"/jobs/{job.id}"),
                )
            )
        return out

    # -- pool-level rules --------------------------------------------------
    def _pool_nudges(
        self, jobs: list[Job], today: date, strategy: str, rules: StrategyRules
    ) -> list[Nudge]:
        out: list[Nudge] = []

        # N4 NO_NEW_JOBS (P3) — cadence nudge, disabled for focused / interview_first.
        if rules.no_new_job_days is not None:
            created_dates = [_as_date(job.created_at) for job in jobs]
            if not created_dates:
                days_since = rules.no_new_job_days
            else:
                days_since = (today - max(created_dates)).days
            if days_since >= rules.no_new_job_days:
                out.append(
                    Nudge(
                        type="no_new_jobs",
                        priority=3,
                        job_id=None,
                        title="补充新的机会",
                        message=f"已经 {days_since} 天没有新增岗位了，去发现更多机会。"
                        if jobs
                        else "岗位池还是空的，先去发现一些机会。",
                        reason={
                            "days_since_last_added": days_since,
                            "threshold_days": rules.no_new_job_days,
                            "strategy": strategy,
                        },
                        cta=NudgeCta(type="open_discover", target="/discover"),
                    )
                )

        # N8 PENDING_BACKLOG (P3) — analysed but not yet applied, disabled for
        # focused / interview_first.
        if rules.pending_backlog_threshold is not None:
            pending = [
                job
                for job in jobs
                if job.status in EARLY_STATUSES and job.analysis is not None
            ]
            if len(pending) >= rules.pending_backlog_threshold:
                out.append(
                    Nudge(
                        type="pending_backlog",
                        priority=3,
                        job_id=None,
                        title="集中处理待投岗位",
                        message=f"有 {len(pending)} 个岗位已分析但还没投，集中清一批。",
                        reason={
                            "pending_count": len(pending),
                            "threshold": rules.pending_backlog_threshold,
                            "strategy": strategy,
                        },
                        cta=NudgeCta(type="open_my_jobs", target="/my-jobs"),
                    )
                )
        return out


def _sort_key(nudge: Nudge) -> tuple[int, int, int]:
    return (
        nudge.priority,
        TYPE_RANK.get(nudge.type, 99),
        nudge.job_id if nudge.job_id is not None else -1,
    )


def _as_date(value: datetime | date | None) -> date:
    if value is None:
        return date.min
    if isinstance(value, datetime):
        return value.date()
    return value


def _days_since(value: datetime | date | None, today: date) -> int:
    if value is None:
        return 0
    return max((today - _as_date(value)).days, 0)
