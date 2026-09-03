export type Recommendation = "Strong Apply" | "Apply" | "Stretch" | "Skip";

export type RequirementImportance = "Critical" | "Important" | "Preferred";
export type RequirementMatchStatus = "Strong" | "Partial" | "Missing";
export type HardRequirementCategory =
  | "eligibility"
  | "experience"
  | "qualification"
  | "other"
  | "none";

export interface FitEvidenceSource {
  source_type: "resume_extracted" | "manual_confirmed";
  source_id: string;
  text: string;
  context: string;
}

export interface RequirementMatch {
  requirement_id: string;
  requirement_text: string;
  importance: RequirementImportance;
  is_hard_requirement: boolean;
  hard_requirement_category: HardRequirementCategory;
  match_status: RequirementMatchStatus;
  reason: string;
  confidence: "High" | "Medium" | "Low";
  evidence_sources: FitEvidenceSource[];
}

export interface FitStrength {
  title: string;
  explanation: string;
  requirement_ids: string[];
  evidence: FitEvidenceSource[];
}

export interface FitGap {
  title: string;
  severity: "critical" | "high" | "medium";
  requirement_id: string;
  requirement: string;
  explanation: string;
  evidence_status: "partial" | "none";
  next_step: string | null;
  is_hard_requirement: boolean;
  hard_requirement_category: HardRequirementCategory;
}

export interface PreparationItem {
  title: string;
  action: string;
  priority: "High" | "Medium" | "Low";
  requirement_ids: string[];
}

export interface FitAnalysis {
  id: number;
  job_id: number;
  match_score: number | null;
  score_status: "available" | "unavailable_no_matchable_requirements";
  recommendation: Recommendation | null;
  summary: string;
  requirement_matches: RequirementMatch[];
  strengths: FitStrength[];
  gaps: FitGap[];
  suggested_preparation: PreparationItem[];
  // Read-time Requirement Taxonomy V2 overlays. The current backend always
  // serializes these (defaulting to [] / a zeroed ScoreBasis), but a legacy or
  // partial analysis payload can omit them — consumers must tolerate absence.
  eligibility_requirements?: EligibilityRequirement[];
  knowledge_requirements?: KnowledgeRequirement[];
  score_basis?: ScoreBasis;
  created_at: string;
  updated_at: string;
}

export interface FitAnalysisState {
  analysis: FitAnalysis | null;
  is_stale: boolean;
  stale_reasons: ("resume" | "experience_bank" | "job_description" | "analysis_version")[];
}

export type FitAnalysisPreview = Omit<FitAnalysis, "id" | "job_id" | "created_at" | "updated_at"> & { artifact_token: string | null; artifact_expires_at: string | null };

export type TailoringAction = "Keep" | "Rewrite" | "Add" | "DeEmphasize" | "Omit";
export type TailoringStatus = "PlanReady" | "DraftReady" | "Edited" | "PendingValidation" | "ValidationFailed" | "Accepted";

export interface TailoringRequirement { requirement_id: string; text: string; importance: RequirementImportance; match_status: RequirementMatchStatus; }
export interface TailoringEvidence { catalog_id: string; source_type: "resume_extracted" | "manual_confirmed"; source_id: string; text: string; context: string; }
export interface TailoringContextMetadata { experience_title: string; organization: string; project_name: string; date_range: string; }
export interface TailoringEvidenceSegment { segment_id: string; parent_source_id: string; text: string; }
export interface TailoringBulletPlan { plan_item_id: string; experience_id: number; source_fact_id: number; original_text: string; recommended_action: TailoringAction; effective_action: TailoringAction; omit_confirmed: boolean; target_requirement_ids: string[]; allowed_evidence_ids: string[]; allowed_segment_ids: string[]; context_metadata: TailoringContextMetadata; reason: string; }
export interface TailoringExperiencePlan { experience_id: number; organization: string; title: string; date_range: string; emphasis: "Highlight" | "Keep" | "DeEmphasize"; coverage_summary: string; bullet_items: TailoringBulletPlan[]; }
export interface TailoringPlan { plan_version: string; relevant_requirements: TailoringRequirement[]; experiences: TailoringExperiencePlan[]; evidence: TailoringEvidence[]; evidence_segments: TailoringEvidenceSegment[]; section_order: string[]; skills_to_include: string[]; unsupported_requirements: TailoringRequirement[]; confirmed: boolean; }
export interface BulletValidation { references_valid: boolean; numbers_valid: boolean; skills_valid: boolean; ownership_valid: boolean; entities_valid: boolean; semantic_supported: boolean; violations: string[]; }
export type TailoringChangeKind = "MeaningfulRewrite" | "ModelKeep" | "FormattingOnlyKeep" | "PlanKeep" | "FallbackOriginal" | "AddedConfirmedFact";
export interface TailoredBullet { plan_item_id: string; experience_id: number; original_text: string; tailored_text: string; effective_text: string; action: TailoringAction; evidence_source_ids: string[]; requirement_ids: string[]; change_summary: string; validation: BulletValidation; state: "Validated" | "FallbackOriginal" | "Unverified" | "KeptOriginal"; change_kind: TailoringChangeKind; }
export interface TailoredExperience { experience_id: number; organization: string; title: string; date_range: string; bullets: TailoredBullet[]; }
export interface TailoredDraft { summary: string; education: Record<string, unknown>[]; skills: string[]; experiences: TailoredExperience[]; }
export interface ResumeTailoring { id: number; job_id: number; source_resume_id: number; status: TailoringStatus; tailoring_plan: TailoringPlan; generated_draft: TailoredDraft | Record<string, never>; user_edited_draft: TailoredDraft | null; validation_results: Record<string, number>; plan_confirmed_at: string | null; accepted_at: string | null; generation_count: number; is_stale: boolean; stale_reasons: string[]; created_at: string; updated_at: string; }
export interface ResumeTailoringState { tailoring: ResumeTailoring | null; prerequisite: "Ready" | "AnalysisRequired" | "AnalysisStale" | "NoMatchableRequirements"; }

export interface EvidenceItem {
  requirement: string;
  resume_evidence: string;
  assessment: "strong" | "partial" | "missing";
}

export interface MatchAnalysis {
  match_score: number;
  recommendation: Recommendation;
  top_strengths: string[];
  key_gaps: string[];
  evidence: EvidenceItem[];
  suggested_preparation: string[];
}

export interface AnalysisResponse {
  resume_profile: Record<string, unknown>;
  jd_requirements: Record<string, unknown>;
  match_analysis: MatchAnalysis;
}

export type JobStatus =
  | "Interested"
  | "Preparing"
  | "Applied"
  | "OA"
  | "Interview"
  | "Final Interview"
  | "Offer"
  | "Rejected"
  | "Withdrawn";

export interface KeyRequirement {
  title: string;
  explanation: string;
  category: string | null;
  priority: "high" | "medium" | "low";
}

export type RequirementType = "eligibility" | "matchable" | "knowledge";

export interface StructuredRequirement {
  requirement_id: string;
  source_text: string;
  normalized_requirement: string;
  source_section: "requirements" | "preferred" | "responsibilities" | "education" | "experience" | "other";
  requirement_type: RequirementType;
  importance: RequirementImportance;
  eligibility_category: "degree" | "education_field" | "graduation_cohort" | "experience_years" | "certification" | "work_authorization" | "language" | "other" | null;
  knowledge_topics: string[];
}

export interface EligibilityRequirement {
  requirement_id: string;
  requirement_text: string;
  status: "Supported" | "PotentialGap" | "Unknown";
  evidence_ids: string[];
  reason: string;
}

export interface KnowledgeRequirement {
  requirement_id: string;
  requirement_text: string;
  source_text: string;
  importance: RequirementImportance;
  knowledge_topics: string[];
  score_included: false;
}

export interface ScoreBasis {
  included_requirement_ids: string[];
  excluded_eligibility_count: number;
  excluded_knowledge_count: number;
}

export interface StructuredJD {
  role: string | null;
  company: string | null;
  location: string | null;
  recruitment_type: string | null;
  published_date: string | null;
  role_summary: string | null;
  key_requirements: KeyRequirement[];
  knowledge_topics: string[];
  responsibilities: string[];
  required_skills: string[];
  preferred_skills: string[];
  ai_requirements: string[];
  product_requirements: string[];
  technical_requirements: string[];
  domain_requirements: string[];
  requirement_taxonomy_version: "legacy-v1" | "v2";
  requirements: StructuredRequirement[];
  subjective_expectations: string[];
}

export interface JobListItem {
  id: number;
  company: string;
  role: string;
  location: string | null;
  status: JobStatus;
  match_score: number | null;
  source: string | null;
  external_job_code: string | null;
  created_at: string;
  updated_at: string;
  application_status_id?: number | null;
}

export interface Job extends JobListItem {
  recruitment_type: string | null;
  source_url: string | null;
  original_jd: string;
  structured_jd: StructuredJD;
  published_date: string | null;
  recommendation: string | null;
  application_date: string | null;
  next_stage: string | null;
  interview_date: string | null;
  notes: string | null;
  external_job_id: string | null;
  source_metadata: Record<string, unknown> | null;
  last_seen_at: string | null;
  analysis_promoted?: boolean;
  application_status_label?: string | null;
}

export type JobImportStatus = "Queued" | "Running" | "Completed" | "Partial" | "Failed";
export type JobImportStage = "Discovering" | "Importing" | "Completed";

export interface JobImportFailure {
  external_job_id: string | null;
  stage: string;
  error_code: string;
}

export interface JobImportSession {
  id: number;
  source: string;
  search_url: string;
  status: JobImportStatus;
  stage: JobImportStage;
  discovered_count: number;
  processed_count: number;
  imported_count: number;
  updated_count: number;
  duplicate_count: number;
  failed_count: number;
  result_job_ids: number[];
  failure_details: JobImportFailure[];
  error_code: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobPreview {
  company: string | null;
  role: string | null;
  location: string | null;
  recruitment_type: string | null;
  published_date: string | null;
  source_url: string | null;
  original_jd: string;
  structured_jd: StructuredJD;
  parser_model: string;
  parser_prompt_version: string;
  parser_schema_version: string;
  source_content_hash: string;
}

export interface JobCreatePayload extends JobPreview {
  company: string;
  role: string;
  status?: JobStatus;
  preview_artifact_token?: string;
}

export interface DashboardData {
  counts: { total: number; applied: number; interviews: number; offers: number };
  profile: {
    preferred_location: string | null;
    target_companies: NamedTarget[];
    target_roles: TargetRole[];
  };
  jobs: JobListItem[];
}

export interface MasterResume {
  id: number;
  original_filename: string;
  structured_profile: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface NamedTarget {
  id: number;
  name: string;
}

export type RolePriority = "primary" | "secondary" | "exploratory";
export type RoleFamily =
  | "ai_product" | "fintech_product" | "data_product" | "strategy_product"
  | "platform_product" | "growth_product" | "general_product"
  | "product_operations" | "solution" | "engineering" | "algorithm"
  | "design" | "other" | "unknown";

export interface TargetRole extends NamedTarget {
  priority: RolePriority;
  auto_role_family: RoleFamily;
  role_family_override: RoleFamily | null;
  effective_role_family: RoleFamily;
  role_family: RoleFamily;
}

export type EligibilityStatus = "Eligible" | "PossiblyEligible" | "Ineligible" | "Unknown";
export type TargetRoleFit = "Primary" | "Secondary" | "Exploratory" | "Low" | "NotTarget" | "Unknown";
export type PreMatchDecision = "WorthAnalyzing" | "LowPriority" | "Exclude";
export type FinalDecision = "Priority" | "Apply" | "Consider" | "Skip";

export interface JobDecision {
  job_id: number;
  auto_role_family: RoleFamily;
  role_family_override: RoleFamily | null;
  effective_role_family: RoleFamily;
  role_classification_confidence: "High" | "Medium" | "Low";
  role_classification_reasons: string[];
  auto_eligibility_status: EligibilityStatus;
  eligibility_override: EligibilityStatus | null;
  effective_eligibility_status: EligibilityStatus;
  eligibility_reasons: string[];
  blocking_requirements: string[];
  unknown_requirements: string[];
  eligibility_override_reason: string | null;
  target_role_fit: TargetRoleFit;
  pre_match_decision: PreMatchDecision;
  final_decision: FinalDecision | null;
  decision_reasons: string[];
  is_stale: boolean;
  evaluated_at: string;
  created_at: string;
  updated_at: string;
}

export interface DecisionJobItem {
  id: number;
  company: string;
  role: string;
  location: string | null;
  source: string | null;
  status: JobStatus;
  application_status_id?: number | null;
  application_status_label?: string | null;
  created_at: string;
  updated_at: string;
  match_score: number | null;
  match_is_stale: boolean;
  decision: JobDecision | null;
}

export interface DecisionJobPage {
  items: DecisionJobItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DecisionSummary {
  total: number;
  no_explicit_blocker: number;
  target_fit: number;
  analyzed: number;
  priority: number;
}

export interface ExperienceFact {
  id: number;
  text: string;
  source_type: "resume" | "manual";
  confirmed: boolean;
  created_at: string;
  updated_at: string;
}

export interface Experience {
  id: number;
  organization: string;
  title: string;
  experience_type: "work" | "project";
  date_range: string | null;
  facts: ExperienceFact[];
}

export interface UserProfile {
  id: number;
  preferred_location: string | null;
  resume: MasterResume | null;
  target_companies: NamedTarget[];
  target_roles: TargetRole[];
  experiences: Experience[];
  job_search_strategy: JobSearchStrategy;
  candidate_type: CandidateType | null;
  graduation_year: number | null;
}

export type JobSearchStrategy = "high_volume" | "focused" | "balanced" | "interview_first";
export type CandidateType = "graduate" | "experienced" | "both";
export interface ApplicationStatusDefinition { id: number; key: string; label: string; sort_order: number; is_system_default: boolean; is_active: boolean; legacy_status: JobStatus | null; }
export type PlanType = "application" | "resume" | "interview_prep" | "job_search" | "follow_up" | "other";
export interface PlanItem { id: number; title: string; date: string; time_optional: string | null; job_id: number | null; type: PlanType; status: "todo" | "done"; notes: string | null; created_by: "user" | "agent_suggestion"; completed_at: string | null; created_at: string; updated_at: string; job: { id: number; company: string; role: string } | null; }

export type NudgeType =
  | "interview_soon"
  | "high_match_stale"
  | "eligibility_review"
  | "stale_decision"
  | "ready_to_apply"
  | "no_new_jobs"
  | "pending_backlog";
export interface Nudge {
  type: NudgeType;
  priority: number;
  job_id: number | null;
  title: string;
  message: string;
  reason: Record<string, unknown>;
  cta: { type: "open_job" | "open_my_jobs" | "open_analysis" | "open_discover"; target: string | null };
}

export type DiscoveryState = "NeedsClarification" | "NeedsRefinement" | "Ready" | "Searching" | "Completed" | "Partial" | "Failed" | "Expired";
export type DiscoveryRelevance = "High" | "Medium" | "Low";

export interface DiscoverySearchContext {
  session_id: string;
  input_kind: "natural_language" | "bytedance_search_url" | "greenhouse_board_url";
  raw_input: string;
  explicit_constraints: {
    role_terms: string[];
    role_families: RoleFamily[];
    locations: string[];
    companies: string[];
    company_groups: string[];
    job_functions: string[];
    industries: string[];
    domains: string[];
    seniority: string[];
    recruitment_types: string[];
  };
  include_terms: string[];
  exclusions: string[];
  freeform_terms: string[];
  explicit_concepts: {
    raw_text: string;
    normalized_id: string | null;
    dimension: "location" | "company" | "job_function" | "role_family" | "industry" | "domain" | "recruitment_type" | "seniority" | "other";
    polarity: "include" | "exclude";
    source: "user_explicit" | "deterministic_parser" | "semantic_planner" | "refinement_selection";
  }[];
  explicit_concept_tag_ids: string[];
  refinement_tag_ids: string[];
  selected_tag_ids: string[];
  refinement_catalog_version: string;
  refinement_round: number;
  ambiguities: string[];
  clarification_required: boolean;
  parsing_method: "deterministic" | "hybrid" | "claude";
  semantic_coverage_status: "complete" | "partial" | "ambiguous";
  personalization_enabled: boolean;
  source_hints: string[];
  created_at: string;
  expires_at: string;
}

export interface DiscoveryRefinementTag {
  id: string;
  label: string;
  dimension: string;
  parent_id: string | null;
  mutually_exclusive_group: string | null;
  normalized_value?: string | null;
  freeform_value?: string | null;
  sort_order: number;
}

export interface DiscoveryRefinementGroup {
  id: string;
  label: string;
  multi_select: boolean;
  required?: boolean;
  source?: "catalog" | "semantic_planner";
  tags: DiscoveryRefinementTag[];
}

export interface DiscoverySession {
  id: string;
  state: DiscoveryState;
  search_context: DiscoverySearchContext;
  source: string;
  selected_sources: string[];
  selected_source_plans: string[];
  source_plan: {
    requested_companies: string[];
    selected_sources: {
      source_key: string;
      company_id: string;
      company_name: string;
      provider: string;
      channel: string;
      adapter_key: string;
      tenant: string | null;
    }[];
    unsupported_companies: string[];
    coverage_status: "supported" | "full" | "partial" | "unsupported";
    coverage_message: string;
  } | null;
  source_progress: {
    source: string;
    provider: string;
    tenant: string | null;
    company: string;
    channel: string | null;
    status: "Pending" | "Searching" | "Completed" | "Failed";
    discovered_count: number;
    duration_seconds: number | null;
    error_code: string | null;
  }[];
  refinement_groups: DiscoveryRefinementGroup[];
  required_refinement_groups: DiscoveryRefinementGroup[];
  optional_refinement_groups: DiscoveryRefinementGroup[];
  discovered_count: number;
  processed_count: number;
  result_count: number;
  duplicate_count: number;
  failed_count: number;
  source_failures: { source: string; error_code: string }[];
  error_code: string | null;
  result_cap_reached: boolean;
  claude_api_calls: number;
  intent_input_tokens: number | null;
  intent_output_tokens: number | null;
  phase3_calls: 0;
  personalization_status: "Off" | "Ready" | "Limited" | "Unavailable";
  personalization_message: string | null;
  personalization_latency_ms: number | null;
  source_refetch_count: 0;
  created_at: string;
  expires_at: string;
  completed_at: string | null;
}

export interface DiscoveryResult {
  result_id: string;
  identity: {
    source: string;
    provider: string;
    tenant: string | null;
    external_job_id: string;
    external_job_code: string | null;
    canonical_url: string;
  };
  normalized: {
    company: string;
    role: string;
    location: string | null;
    recruitment_type: string | null;
    source_url: string;
    original_jd: string;
    structured_jd: StructuredJD;
    published_date: string | null;
  };
  deterministic_derived: {
    role_family: RoleFamily;
    role_confidence: "High" | "Medium" | "Low";
    explicit_hard_signals: { type: string; operator: string | null; value: string | number | null; display: string; source_text: string }[];
    content_hash: string;
    dedupe_key: string;
  };
  search_derived: {
    relevance_band: DiscoveryRelevance;
    matched_constraints: string[];
    unresolved_constraints: string[];
    excluded_matches: string[];
    reasons: string[];
    reason_items: { kind: "matched" | "unknown" | "warning" | "excluded"; code: string; label: string }[];
    excluded_by_current_search: boolean;
  };
  personalization_derived: {
    band: "Strong" | "Relevant" | "Neutral";
    candidate_reasons: {
      reason_type: "candidate_evidence_match" | "target_role_alignment";
      display: string;
      evidence_refs: string[];
      status: "supported";
    }[];
    candidate_constraint_signals: {
      type: "experience_years" | "degree";
      status: "Supported" | "PotentialGap" | "Unknown";
      display: string;
      evidence_refs: string[];
    }[];
    evidence: {
      evidence_ref: string;
      source_type: "resume_extracted" | "manual_confirmed" | "target_role" | "preference";
      text_summary: string;
      context: string;
    }[];
  } | null;
  in_my_jobs: boolean;
  persistent_job_id: number | null;
}

export interface DiscoveryResultPage {
  items: DiscoveryResult[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
