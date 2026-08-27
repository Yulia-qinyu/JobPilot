from __future__ import annotations

from datetime import date as DateValue
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.workspace import JobSearchStrategy, PlanType

AdvicePriority = Literal["high", "medium", "low"]
AdviceActionType = Literal[
    "apply",
    "resume",
    "interview_prep",
    "job_search",
    "follow_up",
    "review",
    "plan",
    "other",
]


class CandidateIdentitySummary(BaseModel):
    candidate_type: Literal["graduate", "experienced", "both"] | None
    graduation_year: int | None


class ApplicationStatusSummary(BaseModel):
    key: str
    label: str
    semantic_category: str
    count: int


class ApplicationSummary(BaseModel):
    interested_count: int = 0
    to_apply_count: int = 0
    applied_count: int = 0
    interview_count: int = 0
    offer_count: int = 0
    ended_count: int = 0
    custom_statuses: list[ApplicationStatusSummary] = Field(default_factory=list)


class PlanningJobSummary(BaseModel):
    job_id: int
    company: str
    title: str
    status_key: str
    status_label: str
    status_category: str
    match_score: int | None
    has_valid_analysis: bool
    tailored_resume_status: str | None
    application_date: DateValue | None
    interview_date: DateValue | None
    days_in_current_status: int
    next_known_date: DateValue | None


class PlanningPlanItem(BaseModel):
    id: int
    title: str
    date: DateValue
    time: str | None
    type: PlanType
    status: Literal["todo", "done"]
    related_job_id: int | None
    related_job: str | None


class PlanSummary(BaseModel):
    today_todo_count: int = 0
    today_done_count: int = 0
    overdue_count: int = 0
    upcoming_count: int = 0
    upcoming_interviews: int = 0


class PlanningActivitySummary(BaseModel):
    event_type: str
    occurred_at: datetime
    job_id: int | None
    plan_item_id: int | None
    detail: str | None


class PlanningSignals(BaseModel):
    days_since_last_job_added: int | None
    days_since_last_application: int | None
    pending_application_count: int
    jobs_ready_to_apply_count: int
    jobs_without_tailored_resume_count: int
    upcoming_interview_count: int
    overdue_plan_count: int
    today_plan_load: int
    recent_completed_plan_count: int


class PlanningContext(BaseModel):
    as_of: DateValue
    timezone: str
    job_search_strategy: JobSearchStrategy
    candidate_identity: CandidateIdentitySummary
    application_summary: ApplicationSummary
    active_jobs: list[PlanningJobSummary]
    plan_summary: PlanSummary
    plan_items: list[PlanningPlanItem]
    recent_activity: list[PlanningActivitySummary]
    derived_signals: PlanningSignals
    freshness_metadata: dict[str, str | int]


class PlanningCandidate(BaseModel):
    id: str
    action_type: AdviceActionType
    related_job_id: int | None
    suggested_plan_type: PlanType | None
    suggested_date: DateValue | None
    title: str
    signal: str
    urgency: int = Field(ge=0, le=100)
    readiness: Literal["ready", "needs_preparation", "informational"]
    rationale_facts: list[str]


class DailyAdviceItemOutput(BaseModel):
    id: str
    priority: AdvicePriority
    action_type: AdviceActionType
    title: str
    reason: str
    related_job_id: int | None
    suggested_plan_type: PlanType | None
    suggested_date: DateValue | None


class DailyAdviceOutput(BaseModel):
    summary: str
    items: list[DailyAdviceItemOutput] = Field(min_length=1, max_length=8)


class DailyAdviceItemRead(DailyAdviceItemOutput):
    added_plan_item_id: int | None = None


class DailyAdviceSnapshotRead(BaseModel):
    id: int
    advice_date: DateValue
    summary: str
    items: list[DailyAdviceItemRead]
    generated_at: datetime
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    status: Literal["Generated", "Fallback"]


class PlanningTodayRead(BaseModel):
    snapshot: DailyAdviceSnapshotRead | None
    is_stale: bool
    empty_context: bool
    empty_message: str | None
    timezone: str
    as_of: DateValue
    signals: PlanningSignals


class PlanningGenerateRequest(BaseModel):
    force_regenerate: bool = False


class AddAdviceToPlanRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    date: DateValue | None = None
