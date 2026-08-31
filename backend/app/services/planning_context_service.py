from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.db.models import ActivityEvent, Job, PlanItem
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.analysis import JDRequirements
from app.schemas.planning import (
    ApplicationStatusSummary,
    ApplicationSummary,
    CandidateIdentitySummary,
    PlanningActivitySummary,
    PlanningContext,
    PlanningJobSummary,
    PlanningPlanItem,
    PlanningSignals,
    PlanSummary,
)
from app.services.analysis_freshness import analysis_identity_is_current
from app.services.evidence_catalog import EvidenceCatalogBuilder, canonical_hash
from app.services.requirement_catalog import RequirementCatalogBuilder

PLANNING_CONTEXT_VERSION = "planning-context-v2"
IGNORED_ACTIVITY_TYPES = {
    "daily_advice_generated",
    "daily_advice_regenerated",
    "advice_added_to_plan",
}
ENDED_STATUSES = {"Rejected", "Withdrawn"}


class PlanningContextService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings

    def build(self) -> PlanningContext:
        profile = ProfileRepository(self.db).ensure_default_profile()
        timezone_name, now = self._local_now()
        as_of = now.date()
        jobs = list(
            self.db.scalars(
                select(Job)
                .where(Job.user_profile_id == DEFAULT_PROFILE_ID)
                .options(
                    selectinload(Job.application_status),
                    selectinload(Job.analysis),
                    selectinload(Job.resume_tailoring),
                )
            ).all()
        )
        plans = list(
            self.db.scalars(
                select(PlanItem)
                .where(PlanItem.user_profile_id == DEFAULT_PROFILE_ID)
                .options(selectinload(PlanItem.job))
            ).all()
        )
        activity_cutoff = datetime.now(UTC) - timedelta(days=7)
        activities = list(
            self.db.scalars(
                select(ActivityEvent)
                .where(
                    ActivityEvent.user_profile_id == DEFAULT_PROFILE_ID,
                    ActivityEvent.created_at >= activity_cutoff,
                    ActivityEvent.event_type.not_in(IGNORED_ACTIVITY_TYPES),
                )
                .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
                .limit(30)
            ).all()
        )
        categories = {job.id: self._status_category(job) for job in jobs}
        application_summary = self._application_summary(jobs, categories)
        active_jobs = self._active_jobs(jobs, categories, as_of, profile)
        planning_items = self._planning_items(plans, as_of)
        plan_summary = self._plan_summary(plans, jobs, as_of)
        recent_activity = [self._activity_summary(item) for item in activities]
        signals = self._signals(
            jobs,
            plans,
            activities,
            categories,
            as_of,
            ZoneInfo(timezone_name),
        )
        return PlanningContext(
            as_of=as_of,
            timezone=timezone_name,
            job_search_strategy=profile.job_search_strategy,
            candidate_identity=CandidateIdentitySummary(
                candidate_type=profile.candidate_type,
                graduation_year=profile.graduation_year,
            ),
            application_summary=application_summary,
            active_jobs=active_jobs,
            plan_summary=plan_summary,
            plan_items=planning_items,
            recent_activity=recent_activity,
            derived_signals=signals,
            freshness_metadata={
                "context_version": PLANNING_CONTEXT_VERSION,
                "active_job_count": len(active_jobs),
                "included_plan_count": len(planning_items),
                "recent_activity_count": len(recent_activity),
            },
        )

    @staticmethod
    def context_hash(context: PlanningContext) -> str:
        return canonical_hash(context.model_dump(mode="json"))

    @staticmethod
    def is_empty(context: PlanningContext) -> bool:
        meaningful_activity = any(
            item.event_type
            in {
                "job_added",
                "application_status_changed",
                "plan_added",
                "plan_completed",
                "resume_tailored",
                "interview_scheduled",
            }
            for item in context.recent_activity
        )
        return not context.active_jobs and not context.plan_items and not meaningful_activity

    def _local_now(self) -> tuple[str, datetime]:
        try:
            zone = ZoneInfo(self.settings.app_timezone)
            return self.settings.app_timezone, datetime.now(zone)
        except ZoneInfoNotFoundError:
            return "UTC", datetime.now(UTC)

    def _active_jobs(
        self,
        jobs: list[Job],
        categories: dict[int, str],
        as_of: date,
        profile,
    ) -> list[PlanningJobSummary]:
        evidence_hashes: tuple[str, str] | None = None
        if profile.resume is not None:
            evidence = EvidenceCatalogBuilder().build(profile)
            evidence_hashes = (evidence.resume_hash, evidence.experience_bank_hash)

        def valid_analysis(job: Job) -> bool:
            if job.analysis is None or evidence_hashes is None:
                return False
            structured_jd = JDRequirements.model_validate(job.structured_jd)
            requirement_hash = RequirementCatalogBuilder().build(structured_jd).structured_jd_hash
            return (
                job.analysis.match_score is not None
                and analysis_identity_is_current(
                    job.analysis,
                    resume_hash=evidence_hashes[0],
                    experience_bank_hash=evidence_hashes[1],
                    structured_jd_hash=requirement_hash,
                    matcher_model=self.settings.claude_model,
                    enforce_matcher_version=(
                        structured_jd.requirement_taxonomy_version == "v2"
                    ),
                )
            )

        active = [
            job
            for job in jobs
            if job.status not in ENDED_STATUSES and categories[job.id] != "ended"
        ]

        def order(job: Job):
            interview_days = (
                (job.interview_date - as_of).days
                if job.interview_date is not None
                else 10_000
            )
            category_order = {
                "interview": 0,
                "to_apply": 1,
                "interested": 2,
                "applied": 3,
                "offer": 4,
                "active_other": 5,
            }
            return (
                max(interview_days, -1),
                category_order.get(categories[job.id], 6),
                -(job.match_score if valid_analysis(job) and job.match_score is not None else -1),
                -job.updated_at.timestamp(),
            )

        result: list[PlanningJobSummary] = []
        for job in sorted(active, key=order)[:15]:
            analysis_valid = valid_analysis(job)
            result.append(
                PlanningJobSummary(
                    job_id=job.id,
                    company=job.company,
                    title=job.role,
                    status_key=(
                        job.application_status.key
                        if job.application_status is not None
                        else job.status
                    ),
                    status_label=(
                        job.application_status.label
                        if job.application_status is not None
                        else job.status
                    ),
                    status_category=categories[job.id],
                    match_score=job.match_score if analysis_valid else None,
                    has_valid_analysis=analysis_valid,
                    tailored_resume_status=(
                        job.resume_tailoring.status
                        if job.resume_tailoring is not None
                        else None
                    ),
                    application_date=job.application_date,
                    interview_date=job.interview_date,
                    days_in_current_status=max((as_of - job.updated_at.date()).days, 0),
                    next_known_date=job.interview_date,
                )
            )
        return result

    def _planning_items(self, plans: list[PlanItem], as_of: date) -> list[PlanningPlanItem]:
        upper = as_of + timedelta(days=7)
        lower = as_of - timedelta(days=7)
        included = [
            item
            for item in plans
            if (
                item.status == "todo" and item.date <= upper
            )
            or (
                item.status == "done"
                and item.completed_at is not None
                and item.completed_at.date() >= lower
            )
        ]
        included.sort(
            key=lambda item: (
                item.status == "done",
                item.date,
                item.time_optional or "99:99",
                item.id,
            )
        )
        return [
            PlanningPlanItem(
                id=item.id,
                title=item.title,
                date=item.date,
                time=item.time_optional,
                type=item.type,
                status=item.status,
                related_job_id=item.job_id,
                related_job=(
                    f"{item.job.company} · {item.job.role}" if item.job is not None else None
                ),
            )
            for item in included[:30]
        ]

    @staticmethod
    def _plan_summary(plans: list[PlanItem], jobs: list[Job], as_of: date) -> PlanSummary:
        return PlanSummary(
            today_todo_count=sum(
                item.status == "todo" and item.date == as_of for item in plans
            ),
            today_done_count=sum(
                item.status == "done" and item.date == as_of for item in plans
            ),
            overdue_count=sum(
                item.status == "todo" and item.date < as_of for item in plans
            ),
            upcoming_count=sum(
                item.status == "todo" and as_of < item.date <= as_of + timedelta(days=7)
                for item in plans
            ),
            upcoming_interviews=sum(
                job.interview_date is not None
                and as_of <= job.interview_date <= as_of + timedelta(days=7)
                for job in jobs
            ),
        )

    def _application_summary(
        self, jobs: list[Job], categories: dict[int, str]
    ) -> ApplicationSummary:
        counts = {
            category: sum(categories[job.id] == category for job in jobs)
            for category in (
                "interested",
                "to_apply",
                "applied",
                "interview",
                "offer",
                "ended",
            )
        }
        custom: dict[tuple[str, str, str], int] = {}
        for job in jobs:
            status = job.application_status
            if status is not None and not status.is_system_default:
                key = (status.key, status.label, categories[job.id])
                custom[key] = custom.get(key, 0) + 1
        return ApplicationSummary(
            interested_count=counts["interested"],
            to_apply_count=counts["to_apply"],
            applied_count=counts["applied"],
            interview_count=counts["interview"],
            offer_count=counts["offer"],
            ended_count=counts["ended"],
            custom_statuses=[
                ApplicationStatusSummary(
                    key=key, label=label, semantic_category=category, count=count
                )
                for (key, label, category), count in sorted(custom.items())
            ],
        )

    def _signals(
        self,
        jobs: list[Job],
        plans: list[PlanItem],
        activities: list[ActivityEvent],
        categories: dict[int, str],
        as_of: date,
        timezone: ZoneInfo,
    ) -> PlanningSignals:
        last_added = self._latest_activity_date(activities, "job_added", timezone)
        application_dates = [job.application_date for job in jobs if job.application_date]
        return PlanningSignals(
            days_since_last_job_added=(as_of - last_added).days if last_added else None,
            days_since_last_application=(
                (as_of - max(application_dates)).days if application_dates else None
            ),
            pending_application_count=sum(
                categories[job.id] in {"interested", "to_apply"} for job in jobs
            ),
            jobs_ready_to_apply_count=sum(
                categories[job.id] == "to_apply" for job in jobs
            ),
            jobs_without_tailored_resume_count=sum(
                categories[job.id] in {"interested", "to_apply"}
                and (
                    job.resume_tailoring is None
                    or job.resume_tailoring.status != "Accepted"
                )
                for job in jobs
            ),
            upcoming_interview_count=sum(
                job.interview_date is not None
                and as_of <= job.interview_date <= as_of + timedelta(days=7)
                for job in jobs
            ),
            overdue_plan_count=sum(
                item.status == "todo" and item.date < as_of for item in plans
            ),
            today_plan_load=sum(
                item.status == "todo" and item.date == as_of for item in plans
            ),
            recent_completed_plan_count=sum(
                item.status == "done"
                and item.completed_at is not None
                and item.completed_at.date() >= as_of - timedelta(days=7)
                for item in plans
            ),
        )

    @staticmethod
    def _latest_activity_date(
        activities: list[ActivityEvent], event_type: str, timezone: ZoneInfo
    ) -> date | None:
        event = next((item for item in activities if item.event_type == event_type), None)
        if event is None:
            return None
        occurred_at = event.created_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        return occurred_at.astimezone(timezone).date()

    @staticmethod
    def _activity_summary(item: ActivityEvent) -> PlanningActivitySummary:
        metadata = item.metadata_json or {}
        detail = None
        if item.event_type == "application_status_changed":
            detail = f"{metadata.get('from_status', '?')} → {metadata.get('to_status', '?')}"
        elif item.event_type in {"plan_added", "plan_completed", "plan_deleted"}:
            detail = str(metadata.get("plan_type") or "plan")
        elif item.event_type == "job_search_strategy_changed":
            detail = f"{metadata.get('from', '?')} → {metadata.get('to', '?')}"
        elif item.event_type == "resume_tailored":
            detail = "岗位简历已更新"
        elif item.event_type == "interview_scheduled":
            detail = str(metadata.get("date") or "时间待确认")
        return PlanningActivitySummary(
            event_type=item.event_type,
            occurred_at=item.created_at,
            job_id=item.job_id,
            plan_item_id=item.plan_item_id,
            detail=detail,
        )

    @staticmethod
    def _status_category(job: Job) -> str:
        status = job.application_status
        legacy = status.legacy_status if status is not None else job.status
        legacy_map = {
            "Interested": "interested",
            "Preparing": "to_apply",
            "Applied": "applied",
            "OA": "interview",
            "Interview": "interview",
            "Final Interview": "interview",
            "Offer": "offer",
            "Rejected": "ended",
            "Withdrawn": "ended",
        }
        if legacy in legacy_map:
            return legacy_map[legacy]
        label = (status.label if status is not None else job.status).casefold()
        if any(marker in label for marker in ("面", "笔试", "测评", "背调")):
            return "interview"
        if "offer" in label:
            return "offer"
        if any(marker in label for marker in ("结束", "未通过", "拒", "撤")):
            return "ended"
        if "已投" in label:
            return "applied"
        if "待投" in label or "准备" in label:
            return "to_apply"
        if "感兴趣" in label:
            return "interested"
        return "active_other"
