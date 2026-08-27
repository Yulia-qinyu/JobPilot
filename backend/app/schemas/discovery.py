from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import JDRequirements
from app.schemas.profile import RoleFamily

DiscoveryState = Literal[
    "NeedsClarification",
    "NeedsRefinement",
    "Ready",
    "Searching",
    "Completed",
    "Partial",
    "Failed",
    "Expired",
]
InputKind = Literal["natural_language", "bytedance_search_url", "greenhouse_board_url"]
RelevanceBand = Literal["High", "Medium", "Low"]
PersonalizationStatus = Literal["Off", "Ready", "Limited", "Unavailable"]
SemanticCoverageStatus = Literal["complete", "partial", "ambiguous"]
ConceptDimension = Literal[
    "location",
    "company",
    "job_function",
    "role_family",
    "industry",
    "domain",
    "recruitment_type",
    "seniority",
    "other",
]


class DiscoveryExplicitConstraints(BaseModel):
    role_terms: list[str] = Field(default_factory=list)
    role_families: list[RoleFamily] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    company_groups: list[str] = Field(default_factory=list)
    job_functions: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    seniority: list[str] = Field(default_factory=list)
    recruitment_types: list[str] = Field(default_factory=list)


class DiscoveryExplicitConcept(BaseModel):
    raw_text: str = Field(min_length=1, max_length=120)
    normalized_id: str | None = Field(default=None, max_length=80)
    dimension: ConceptDimension
    polarity: Literal["include", "exclude"] = "include"
    source: Literal[
        "user_explicit",
        "deterministic_parser",
        "semantic_planner",
        "refinement_selection",
    ]


class DiscoverySearchContext(BaseModel):
    session_id: str
    input_kind: InputKind
    raw_input: str
    explicit_constraints: DiscoveryExplicitConstraints
    include_terms: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    freeform_terms: list[str] = Field(default_factory=list)
    explicit_concepts: list[DiscoveryExplicitConcept] = Field(default_factory=list)
    explicit_concept_tag_ids: list[str] = Field(default_factory=list)
    refinement_tag_ids: list[str] = Field(default_factory=list)
    selected_tag_ids: list[str] = Field(default_factory=list)
    refinement_catalog_version: str = "discovery-tags-v1"
    refinement_round: int = 0
    ambiguities: list[str] = Field(default_factory=list)
    clarification_required: bool = False
    parsing_method: Literal["deterministic", "hybrid", "claude"] = "deterministic"
    semantic_coverage_status: SemanticCoverageStatus = "complete"
    personalization_enabled: bool = False
    source_hints: list[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime


class DiscoveryIdentity(BaseModel):
    source: str
    provider: str
    tenant: str | None = None
    external_job_id: str
    external_job_code: str | None = None
    canonical_url: str


class DiscoverySourceRaw(BaseModel):
    title: str
    locations: list[str]
    recruitment_type: str | None
    description: str
    requirements: str
    published_date: date | None
    source_metadata: dict = Field(default_factory=dict)


class DiscoveryNormalizedJob(BaseModel):
    company: str
    role: str
    location: str | None
    recruitment_type: str | None
    source_url: str
    original_jd: str
    structured_jd: JDRequirements
    published_date: date | None


class DiscoveryDeterministicDerived(BaseModel):
    role_family: RoleFamily
    role_confidence: Literal["High", "Medium", "Low"]
    explicit_hard_signals: list["DiscoveryHardSignal"] = Field(default_factory=list)
    content_hash: str
    dedupe_key: str


class DiscoverySearchDerived(BaseModel):
    relevance_band: RelevanceBand
    matched_constraints: list[str] = Field(default_factory=list)
    unresolved_constraints: list[str] = Field(default_factory=list)
    excluded_matches: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    reason_items: list["DiscoveryReason"] = Field(default_factory=list)
    excluded_by_current_search: bool = False


class CandidateEvidenceTrace(BaseModel):
    evidence_ref: str
    source_type: Literal["resume_extracted", "manual_confirmed", "target_role", "preference"]
    text_summary: str
    context: str


class CandidatePersonalizationReason(BaseModel):
    reason_type: Literal["candidate_evidence_match", "target_role_alignment"]
    display: str
    evidence_refs: list[str] = Field(default_factory=list)
    status: Literal["supported"] = "supported"


class CandidateConstraintSignal(BaseModel):
    type: Literal["experience_years", "degree"]
    status: Literal["Supported", "PotentialGap", "Unknown"]
    display: str
    evidence_refs: list[str] = Field(default_factory=list)


class DiscoveryPersonalizationDerived(BaseModel):
    band: Literal["Strong", "Relevant", "Neutral"]
    candidate_reasons: list[CandidatePersonalizationReason] = Field(default_factory=list)
    candidate_constraint_signals: list[CandidateConstraintSignal] = Field(default_factory=list)
    evidence: list[CandidateEvidenceTrace] = Field(default_factory=list)


class DiscoveryHardSignal(BaseModel):
    type: Literal["experience_years", "degree", "language", "authorization", "mandatory_other"]
    operator: str | None = None
    value: str | int | None = None
    display: str
    source_text: str


class DiscoveryReason(BaseModel):
    kind: Literal["matched", "unknown", "warning", "excluded"]
    code: str
    label: str


class DiscoveryRefinementTag(BaseModel):
    id: str
    label: str
    dimension: str
    parent_id: str | None = None
    mutually_exclusive_group: str | None = None
    normalized_value: str | None = Field(default=None, max_length=80)
    freeform_value: str | None = Field(default=None, max_length=120)
    sort_order: int


class DiscoveryRefinementGroup(BaseModel):
    id: str
    label: str
    multi_select: bool = True
    required: bool = False
    source: Literal["catalog", "semantic_planner"] = "catalog"
    tags: list[DiscoveryRefinementTag]


class DiscoveryPlannedSource(BaseModel):
    source_key: str
    company_id: str
    company_name: str
    provider: str
    channel: str
    adapter_key: str
    tenant: str | None = None


class DiscoverySourcePlan(BaseModel):
    requested_companies: list[str] = Field(default_factory=list)
    selected_sources: list[DiscoveryPlannedSource] = Field(default_factory=list)
    unsupported_companies: list[str] = Field(default_factory=list)
    coverage_status: Literal["supported", "full", "partial", "unsupported"]
    coverage_message: str


class DiscoverySourceProgress(BaseModel):
    source: str
    provider: str
    tenant: str | None = None
    company: str
    channel: str | None = None
    status: Literal["Pending", "Searching", "Completed", "Failed"] = "Pending"
    discovered_count: int = 0
    duration_seconds: float | None = None
    error_code: str | None = None


class DiscoveryResult(BaseModel):
    result_id: str
    identity: DiscoveryIdentity
    source_raw: DiscoverySourceRaw
    normalized: DiscoveryNormalizedJob
    deterministic_derived: DiscoveryDeterministicDerived
    search_derived: DiscoverySearchDerived
    personalization_derived: DiscoveryPersonalizationDerived | None = None
    in_my_jobs: bool = False
    persistent_job_id: int | None = None


class DiscoverySessionCreate(BaseModel):
    input: str = Field(min_length=2, max_length=4_000)
    personalization_enabled: bool = False


class DiscoverySessionRead(BaseModel):
    id: str
    state: DiscoveryState
    search_context: DiscoverySearchContext
    source: str
    selected_sources: list[str] = Field(default_factory=list)
    selected_source_plans: list[str] = Field(default_factory=list)
    source_plan: DiscoverySourcePlan | None = None
    source_progress: list[DiscoverySourceProgress] = Field(default_factory=list)
    refinement_groups: list[DiscoveryRefinementGroup] = Field(default_factory=list)
    required_refinement_groups: list[DiscoveryRefinementGroup] = Field(default_factory=list)
    optional_refinement_groups: list[DiscoveryRefinementGroup] = Field(default_factory=list)
    discovered_count: int = 0
    processed_count: int = 0
    result_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    source_failures: list[dict[str, str]] = Field(default_factory=list)
    error_code: str | None = None
    result_cap_reached: bool = False
    claude_api_calls: int = Field(default=0, ge=0, le=1)
    intent_input_tokens: int | None = None
    intent_output_tokens: int | None = None
    phase3_calls: Literal[0] = 0
    personalization_status: PersonalizationStatus = "Off"
    personalization_message: str | None = None
    personalization_latency_ms: float | None = None
    source_refetch_count: Literal[0] = 0
    created_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None


class DiscoveryResultPage(BaseModel):
    items: list[DiscoveryResult]
    total: int
    page: int
    page_size: int
    total_pages: int


class DiscoveryContextUpdate(BaseModel):
    selected_tag_ids: list[str] | None = Field(default=None, max_length=20)
    exclusions: list[str] | None = Field(default=None, max_length=20)
    skip_refinement: bool = False
    personalization_enabled: bool | None = None


class AddDiscoveryResultResponse(BaseModel):
    outcome: Literal["created", "existing", "updated"]
    persistent_job_id: int
    claude_api_calls: Literal[0] = 0
    phase3_calls: Literal[0] = 0
