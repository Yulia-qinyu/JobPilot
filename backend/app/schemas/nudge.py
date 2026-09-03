from typing import Literal

from pydantic import BaseModel, Field

NudgeType = Literal[
    "interview_soon",
    "high_match_stale",
    "eligibility_review",
    "stale_decision",
    "ready_to_apply",
    "no_new_jobs",
    "pending_backlog",
]

NudgeCtaType = Literal["open_job", "open_my_jobs", "open_analysis", "open_discover"]


class NudgeCta(BaseModel):
    type: NudgeCtaType
    target: str | None = None


class Nudge(BaseModel):
    """A single deterministic, explainable recommendation.

    Computed at request time from stored job / analysis / decision state and the
    user's job-search strategy. No LLM call is involved and nothing is persisted.
    """

    type: NudgeType
    priority: int = Field(ge=0, le=3, description="P0 (most urgent) .. P3 (cadence)")
    job_id: int | None = None
    title: str
    message: str
    reason: dict = Field(
        default_factory=dict,
        description="Structured, human-auditable explanation of why this fired.",
    )
    cta: NudgeCta
