from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RequirementImportance = Literal["Critical", "Important", "Preferred"]
RequirementMatchStatus = Literal["Strong", "Partial", "Missing"]
MatchConfidence = Literal["High", "Medium", "Low"]
HardRequirementCategory = Literal[
    "eligibility",
    "experience",
    "qualification",
    "other",
    "none",
]
FitRecommendation = Literal["Strong Apply", "Apply", "Stretch", "Skip"]
EvidenceSourceType = Literal["resume_extracted", "manual_confirmed"]


class RequirementMatchOutput(BaseModel):
    """Intentionally simple Claude transport object; every field is required."""

    requirement_id: str
    importance: RequirementImportance
    is_hard_requirement: bool
    hard_requirement_category: HardRequirementCategory
    match_status: RequirementMatchStatus
    reason: str
    confidence: MatchConfidence
    evidence_source_ids: list[str]


class PreparationOutput(BaseModel):
    """Intentionally simple Claude transport object; every field is required."""

    title: str
    action: str
    priority: Literal["High", "Medium", "Low"]
    requirement_ids: list[str]


class FitAnalysisOutput(BaseModel):
    """Low-complexity schema passed to Anthropic structured outputs."""

    summary: str
    requirement_matches: list[RequirementMatchOutput]
    suggested_preparation: list[PreparationOutput]


class EvidenceSourceRead(BaseModel):
    source_type: EvidenceSourceType
    source_id: str
    text: str
    context: str


class RequirementMatch(BaseModel):
    requirement_id: str
    requirement_text: str
    importance: RequirementImportance
    is_hard_requirement: bool
    hard_requirement_category: HardRequirementCategory
    match_status: RequirementMatchStatus
    reason: str
    confidence: MatchConfidence
    evidence_sources: list[EvidenceSourceRead] = Field(default_factory=list)


class FitStrength(BaseModel):
    title: str
    explanation: str
    requirement_ids: list[str]
    evidence: list[EvidenceSourceRead]


class FitGap(BaseModel):
    title: str
    severity: Literal["critical", "high", "medium"]
    requirement_id: str
    requirement: str
    explanation: str
    evidence_status: Literal["partial", "none"]
    next_step: str | None = None
    is_hard_requirement: bool
    hard_requirement_category: HardRequirementCategory


class PreparationItem(BaseModel):
    title: str
    action: str
    priority: Literal["High", "Medium", "Low"]
    requirement_ids: list[str]


class FitAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    match_score: int
    recommendation: FitRecommendation
    summary: str
    requirement_matches: list[RequirementMatch]
    strengths: list[FitStrength]
    gaps: list[FitGap]
    suggested_preparation: list[PreparationItem]
    created_at: datetime
    updated_at: datetime


class FitAnalysisPreview(BaseModel):
    """A non-persistent analysis of a confirmed structured JD."""

    match_score: int
    recommendation: FitRecommendation
    summary: str
    requirement_matches: list[RequirementMatch]
    strengths: list[FitStrength]
    gaps: list[FitGap]
    suggested_preparation: list[PreparationItem]
    artifact_token: str | None = None
    artifact_expires_at: datetime | None = None


class FitAnalysisState(BaseModel):
    analysis: FitAnalysisRead | None
    is_stale: bool = False
    stale_reasons: list[Literal["resume", "experience_bank", "job_description"]] = Field(
        default_factory=list
    )
