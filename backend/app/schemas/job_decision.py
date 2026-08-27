from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobStatus
from app.schemas.profile import RoleFamily

EligibilityStatus = Literal["Eligible", "PossiblyEligible", "Ineligible", "Unknown"]
RoleConfidence = Literal["High", "Medium", "Low"]
TargetRoleFit = Literal["Primary", "Secondary", "Exploratory", "Low", "NotTarget", "Unknown"]
PreMatchDecision = Literal["WorthAnalyzing", "LowPriority", "Exclude"]
FinalDecision = Literal["Priority", "Apply", "Consider", "Skip"]


class EligibilityResult(BaseModel):
    status: EligibilityStatus
    reasons: list[str] = Field(default_factory=list)
    blocking_requirements: list[str] = Field(default_factory=list)
    unknown_requirements: list[str] = Field(default_factory=list)


class RoleClassification(BaseModel):
    role_family: RoleFamily
    confidence: RoleConfidence
    reasons: list[str]


class JobDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    auto_role_family: RoleFamily
    role_family_override: RoleFamily | None
    effective_role_family: RoleFamily
    role_classification_confidence: RoleConfidence
    role_classification_reasons: list[str]
    auto_eligibility_status: EligibilityStatus
    eligibility_override: EligibilityStatus | None
    effective_eligibility_status: EligibilityStatus
    eligibility_reasons: list[str]
    blocking_requirements: list[str]
    unknown_requirements: list[str]
    eligibility_override_reason: str | None
    target_role_fit: TargetRoleFit
    pre_match_decision: PreMatchDecision
    final_decision: FinalDecision | None
    decision_reasons: list[str]
    is_stale: bool
    evaluated_at: datetime
    created_at: datetime
    updated_at: datetime


class JobDecisionOverride(BaseModel):
    role_family_override: RoleFamily | None = None
    eligibility_override: EligibilityStatus | None = None
    eligibility_override_reason: str | None = Field(default=None, max_length=1_000)


class DecisionJobItem(BaseModel):
    id: int
    company: str
    role: str
    location: str | None
    source: str | None
    status: JobStatus
    application_status_id: int | None = None
    application_status_label: str | None = None
    created_at: datetime
    updated_at: datetime
    match_score: int | None
    match_is_stale: bool
    decision: JobDecisionRead | None


class DecisionJobPage(BaseModel):
    items: list[DecisionJobItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class DecisionSummary(BaseModel):
    total: int
    no_explicit_blocker: int
    target_fit: int
    analyzed: int
    priority: int


class DecisionRecomputeRequest(BaseModel):
    job_ids: list[int] | None = Field(default=None, max_length=2_000)


class DecisionRecomputeResult(BaseModel):
    requested: int
    processed: int
    failed: int
    elapsed_seconds: float
    claude_api_calls: Literal[0] = 0
