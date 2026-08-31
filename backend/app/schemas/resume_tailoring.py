from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PlanAction = Literal["Keep", "Rewrite", "Add", "DeEmphasize", "Omit"]
TailoringStatus = Literal[
    "PlanReady",
    "DraftReady",
    "Edited",
    "PendingValidation",
    "ValidationFailed",
    "Accepted",
]


class PlanRequirement(BaseModel):
    requirement_id: str
    text: str
    importance: Literal["Critical", "Important", "Preferred"]
    match_status: Literal["Strong", "Partial", "Missing"]


class PlanEvidence(BaseModel):
    catalog_id: str
    source_type: Literal["resume_extracted", "manual_confirmed"]
    source_id: str
    text: str
    context: str


class ContextMetadata(BaseModel):
    experience_title: str = ""
    organization: str = ""
    project_name: str = ""
    date_range: str = ""


class DerivedEvidenceSegment(BaseModel):
    segment_id: str
    parent_source_id: str
    text: str


class BulletPlanItem(BaseModel):
    plan_item_id: str
    experience_id: int
    source_fact_id: int
    original_text: str
    recommended_action: PlanAction
    effective_action: PlanAction
    omit_confirmed: bool
    target_requirement_ids: list[str]
    allowed_evidence_ids: list[str]
    allowed_segment_ids: list[str] = Field(default_factory=list)
    context_metadata: ContextMetadata = Field(default_factory=ContextMetadata)
    reason: str


class ExperiencePlan(BaseModel):
    experience_id: int
    organization: str
    title: str
    date_range: str
    emphasis: Literal["Highlight", "Keep", "DeEmphasize"]
    coverage_summary: str
    bullet_items: list[BulletPlanItem]


class TailoringPlan(BaseModel):
    plan_version: str = "tailoring-plan-v1"
    relevant_requirements: list[PlanRequirement]
    experiences: list[ExperiencePlan]
    evidence: list[PlanEvidence]
    evidence_segments: list[DerivedEvidenceSegment] = Field(default_factory=list)
    section_order: list[str]
    skills_to_include: list[str]
    unsupported_requirements: list[PlanRequirement]
    confirmed: bool = False


class PlanItemPatch(BaseModel):
    plan_item_id: str
    action: PlanAction
    omit_confirmed: bool = False


class TailoringPlanPatch(BaseModel):
    items: list[PlanItemPatch] = Field(default_factory=list)
    section_order: list[str] | None = None
    confirmed: bool = False


class GeneratedBulletOutput(BaseModel):
    """Low-complexity Claude transport item; every field is required."""

    plan_item_id: str
    action: Literal["Rewrite", "Keep"]
    rewritten_text: str
    evidence_source_ids: list[str]
    requirement_ids: list[str]
    change_summary: str


class TailoredDraftOutput(BaseModel):
    """Low-complexity Claude transport schema."""

    summary: str
    bullets: list[GeneratedBulletOutput]


class SemanticValidationItemOutput(BaseModel):
    plan_item_id: str
    unsupported_spans: list[str]


class SemanticValidationOutput(BaseModel):
    results: list[SemanticValidationItemOutput]


class BulletValidation(BaseModel):
    references_valid: bool
    numbers_valid: bool
    skills_valid: bool
    ownership_valid: bool
    entities_valid: bool
    semantic_supported: bool
    violations: list[str] = Field(default_factory=list)


class TailoredBullet(BaseModel):
    plan_item_id: str
    experience_id: int
    original_text: str
    tailored_text: str
    effective_text: str
    action: PlanAction
    evidence_source_ids: list[str]
    requirement_ids: list[str]
    change_summary: str
    validation: BulletValidation
    state: Literal["Validated", "FallbackOriginal", "Unverified", "KeptOriginal"]
    change_kind: Literal[
        "MeaningfulRewrite",
        "ModelKeep",
        "FormattingOnlyKeep",
        "PlanKeep",
        "FallbackOriginal",
        "AddedConfirmedFact",
    ] = "MeaningfulRewrite"


class TailoredExperience(BaseModel):
    experience_id: int
    organization: str
    title: str
    date_range: str
    bullets: list[TailoredBullet]


class TailoredDraft(BaseModel):
    summary: str
    education: list[dict]
    skills: list[str]
    experiences: list[TailoredExperience]


class DraftEditItem(BaseModel):
    plan_item_id: str
    text: str = Field(min_length=1, max_length=2000)
    keep_original: bool = False


class TailoredDraftPatch(BaseModel):
    items: list[DraftEditItem]


class ResumeTailoringRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    source_resume_id: int
    status: TailoringStatus
    tailoring_plan: TailoringPlan
    generated_draft: TailoredDraft | dict
    user_edited_draft: TailoredDraft | None
    validation_results: dict
    plan_confirmed_at: datetime | None
    accepted_at: datetime | None
    generation_count: int
    is_stale: bool = False
    stale_reasons: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ResumeTailoringState(BaseModel):
    tailoring: ResumeTailoringRead | None
    prerequisite: Literal[
        "Ready", "AnalysisRequired", "AnalysisStale", "NoMatchableRequirements"
    ]
