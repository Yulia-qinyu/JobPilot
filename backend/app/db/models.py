from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "candidate_type IS NULL OR candidate_type IN ('graduate', 'experienced', 'both')",
            name="ck_user_profiles_candidate_type",
        ),
        CheckConstraint(
            "graduation_year IS NULL OR (graduation_year >= 1900 AND graduation_year <= 2200)",
            name="ck_user_profiles_graduation_year",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    preferred_location: Mapped[str | None] = mapped_column(String(120))
    job_search_strategy: Mapped[str] = mapped_column(String(24), default="balanced")
    candidate_type: Mapped[str | None] = mapped_column(String(24))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    resume: Mapped["Resume | None"] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan", uselist=False
    )
    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="user_profile",
        cascade="all, delete-orphan",
        order_by="Experience.sort_order",
    )
    target_companies: Mapped[list["TargetCompany"]] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan", order_by="TargetCompany.id"
    )
    target_roles: Mapped[list["TargetRole"]] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan", order_by="TargetRole.id"
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan"
    )
    job_import_sessions: Mapped[list["JobImportSession"]] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan"
    )
    application_status_definitions: Mapped[list["ApplicationStatusDefinition"]] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan"
    )
    plan_items: Mapped[list["PlanItem"]] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan"
    )
    daily_advice_snapshots: Mapped[list["DailyAdviceSnapshot"]] = relationship(
        back_populates="user_profile", cascade="all, delete-orphan"
    )


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), unique=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    extracted_text: Mapped[str] = mapped_column(Text)
    structured_profile: Mapped[dict] = mapped_column(JSON)
    user_profile: Mapped[UserProfile] = relationship(back_populates="resume")
    experiences: Mapped[list["Experience"]] = relationship(back_populates="source_resume")


class Experience(TimestampMixin, Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    source_resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), index=True
    )
    organization: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    experience_type: Mapped[str] = mapped_column(String(20))
    date_range: Mapped[str | None] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(default=0)
    user_profile: Mapped[UserProfile] = relationship(back_populates="experiences")
    source_resume: Mapped[Resume | None] = relationship(back_populates="experiences")
    facts: Mapped[list["ExperienceFact"]] = relationship(
        back_populates="experience", cascade="all, delete-orphan", order_by="ExperienceFact.id"
    )


class ExperienceFact(TimestampMixin, Base):
    __tablename__ = "experience_facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    experience: Mapped[Experience] = relationship(back_populates="facts")


class TargetCompany(TimestampMixin, Base):
    __tablename__ = "target_companies"
    __table_args__ = (UniqueConstraint("user_profile_id", "name", name="uq_company_profile_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    user_profile: Mapped[UserProfile] = relationship(back_populates="target_companies")


class TargetRole(TimestampMixin, Base):
    __tablename__ = "target_roles"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "name", name="uq_role_profile_name"),
        CheckConstraint(
            "priority IN ('primary', 'secondary', 'exploratory')",
            name="ck_target_roles_priority",
        ),
        CheckConstraint(
            "role_family IN ('ai_product', 'fintech_product', 'data_product', "
            "'strategy_product', 'platform_product', 'growth_product', 'general_product', "
            "'product_operations', 'solution', 'engineering', 'algorithm', 'design', "
            "'other', 'unknown')",
            name="ck_target_roles_role_family",
        ),
        CheckConstraint(
            "auto_role_family IN ('ai_product', 'fintech_product', 'data_product', "
            "'strategy_product', 'platform_product', 'growth_product', 'general_product', "
            "'product_operations', 'solution', 'engineering', 'algorithm', 'design', "
            "'other', 'unknown')",
            name="ck_target_roles_auto_role_family",
        ),
        CheckConstraint(
            "role_family_override IS NULL OR role_family_override IN ('ai_product', "
            "'fintech_product', 'data_product', 'strategy_product', 'platform_product', "
            "'growth_product', 'general_product', 'product_operations', 'solution', "
            "'engineering', 'algorithm', 'design', 'other', 'unknown')",
            name="ck_target_roles_role_family_override",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(20), default="primary")
    auto_role_family: Mapped[str] = mapped_column(String(40), default="unknown")
    role_family_override: Mapped[str | None] = mapped_column(String(40))
    role_family: Mapped[str] = mapped_column(String(40), default="unknown")
    user_profile: Mapped[UserProfile] = relationship(back_populates="target_roles")

    @property
    def effective_role_family(self) -> str:
        return self.role_family


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Interested', 'Preparing', 'Applied', 'OA', 'Interview', "
            "'Final Interview', 'Offer', 'Rejected', 'Withdrawn')",
            name="ck_jobs_status",
        ),
        CheckConstraint(
            "match_score IS NULL OR (match_score >= 0 AND match_score <= 100)",
            name="ck_jobs_match_score",
        ),
        UniqueConstraint(
            "user_profile_id",
            "source",
            "external_job_id",
            name="uq_jobs_profile_source_external_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    company: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    recruitment_type: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(Text)
    original_jd: Mapped[str] = mapped_column(Text)
    structured_jd: Mapped[dict] = mapped_column(JSON)
    published_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="Interested", index=True)
    application_status_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_status_definitions.id", ondelete="RESTRICT"), index=True
    )
    match_score: Mapped[int | None] = mapped_column(Integer)
    recommendation: Mapped[str | None] = mapped_column(String(32))
    application_date: Mapped[date | None] = mapped_column(Date)
    next_stage: Mapped[str | None] = mapped_column(String(255))
    interview_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    parser_model: Mapped[str | None] = mapped_column(String(120))
    parser_prompt_version: Mapped[str | None] = mapped_column(String(40))
    parser_schema_version: Mapped[str | None] = mapped_column(String(40))
    source_content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str | None] = mapped_column(String(32), index=True)
    external_job_id: Mapped[str | None] = mapped_column(String(128))
    external_job_code: Mapped[str | None] = mapped_column(String(64))
    source_metadata: Mapped[dict | None] = mapped_column(JSON)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_profile: Mapped[UserProfile] = relationship(back_populates="jobs")
    analysis: Mapped["JobAnalysis | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    decision: Mapped["JobDecision | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    resume_tailoring: Mapped["ResumeTailoring | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    application_status: Mapped["ApplicationStatusDefinition | None"] = relationship(
        back_populates="jobs"
    )
    plan_items: Mapped[list["PlanItem"]] = relationship(back_populates="job")

    @property
    def application_status_label(self) -> str | None:
        return self.application_status.label if self.application_status else None


class ApplicationStatusDefinition(TimestampMixin, Base):
    __tablename__ = "application_status_definitions"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "key", name="uq_application_status_profile_key"),
        UniqueConstraint("user_profile_id", "label", name="uq_application_status_profile_label"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(80))
    sort_order: Mapped[int] = mapped_column(Integer)
    is_system_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    legacy_status: Mapped[str | None] = mapped_column(String(32))
    user_profile: Mapped[UserProfile] = relationship(back_populates="application_status_definitions")
    jobs: Mapped[list[Job]] = relationship(back_populates="application_status")


class PlanItem(TimestampMixin, Base):
    __tablename__ = "plan_items"
    __table_args__ = (
        CheckConstraint(
            "type IN ('application', 'resume', 'interview_prep', 'job_search', "
            "'follow_up', 'other')",
            name="ck_plan_items_type",
        ),
        CheckConstraint("status IN ('todo', 'done')", name="ck_plan_items_status"),
        CheckConstraint(
            "created_by IN ('user', 'agent_suggestion')", name="ck_plan_items_created_by"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, index=True)
    time_optional: Mapped[str | None] = mapped_column(String(5))
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[str] = mapped_column(String(24), default="other")
    status: Mapped[str] = mapped_column(String(12), default="todo", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(24), default="user")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_profile: Mapped[UserProfile] = relationship(back_populates="plan_items")
    job: Mapped[Job | None] = relationship(back_populates="plan_items")


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )
    plan_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan_items.id", ondelete="SET NULL"), index=True
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DailyAdviceSnapshot(Base):
    __tablename__ = "daily_advice_snapshots"
    __table_args__ = (
        CheckConstraint(
            "strategy IN ('high_volume', 'focused', 'balanced', 'interview_first')",
            name="ck_daily_advice_snapshots_strategy",
        ),
        CheckConstraint(
            "status IN ('Generated', 'Fallback')",
            name="ck_daily_advice_snapshots_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    advice_date: Mapped[date] = mapped_column(Date, index=True)
    planning_context_hash: Mapped[str] = mapped_column(String(64), index=True)
    strategy: Mapped[str] = mapped_column(String(24))
    response_json: Mapped[dict] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    model: Mapped[str] = mapped_column(String(120))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="Generated")
    user_profile: Mapped[UserProfile] = relationship(
        back_populates="daily_advice_snapshots"
    )


class JobImportSession(TimestampMixin, Base):
    __tablename__ = "job_import_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Queued', 'Running', 'Completed', 'Partial', 'Failed')",
            name="ck_job_import_sessions_status",
        ),
        CheckConstraint(
            "stage IN ('Discovering', 'Importing', 'Completed')",
            name="ck_job_import_sessions_stage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32), index=True)
    search_url: Mapped[str] = mapped_column(Text)
    search_url_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="Queued", index=True)
    stage: Mapped[str] = mapped_column(String(20), default="Discovering")
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    result_job_ids: Mapped[list] = mapped_column(JSON, default=list)
    failure_details: Mapped[list] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_profile: Mapped[UserProfile] = relationship(back_populates="job_import_sessions")


class JobAnalysis(TimestampMixin, Base):
    __tablename__ = "job_analyses"
    __table_args__ = (
        CheckConstraint(
            "match_score >= 0 AND match_score <= 100",
            name="ck_job_analyses_match_score",
        ),
        CheckConstraint(
            "recommendation IN ('Strong Apply', 'Apply', 'Stretch', 'Skip')",
            name="ck_job_analyses_recommendation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, index=True
    )
    resume_hash: Mapped[str] = mapped_column(String(64))
    experience_bank_hash: Mapped[str] = mapped_column(String(64))
    structured_jd_hash: Mapped[str] = mapped_column(String(64))
    matcher_model: Mapped[str] = mapped_column(String(120))
    matcher_prompt_version: Mapped[str] = mapped_column(String(40))
    matcher_schema_version: Mapped[str] = mapped_column(String(40))
    match_score: Mapped[int | None] = mapped_column(Integer)
    recommendation: Mapped[str | None] = mapped_column(String(32))

    @property
    def score_status(self) -> str:
        return (
            "available"
            if self.match_score is not None
            else "unavailable_no_matchable_requirements"
        )
    summary: Mapped[str] = mapped_column(Text)
    requirement_matches: Mapped[list] = mapped_column(JSON)
    strengths: Mapped[list] = mapped_column(JSON)
    gaps: Mapped[list] = mapped_column(JSON)
    suggested_preparation: Mapped[list] = mapped_column(JSON)
    job: Mapped[Job] = relationship(back_populates="analysis")


class ResumeTailoring(TimestampMixin, Base):
    __tablename__ = "resume_tailorings"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_resume_tailorings_job_id"),
        CheckConstraint(
            "status IN ('PlanReady', 'DraftReady', 'Edited', 'PendingValidation', "
            "'ValidationFailed', 'Accepted')",
            name="ck_resume_tailorings_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    source_resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="PlanReady", index=True)
    tailoring_plan: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_draft: Mapped[dict] = mapped_column(JSON, default=dict)
    user_edited_draft: Mapped[dict | None] = mapped_column(JSON)
    validation_results: Mapped[dict] = mapped_column(JSON, default=dict)
    plan_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resume_hash: Mapped[str] = mapped_column(String(64), index=True)
    experience_bank_hash: Mapped[str] = mapped_column(String(64), index=True)
    structured_jd_hash: Mapped[str] = mapped_column(String(64), index=True)
    analysis_hash: Mapped[str] = mapped_column(String(64), index=True)
    plan_hash: Mapped[str] = mapped_column(String(64), index=True)
    generator_model: Mapped[str | None] = mapped_column(String(120))
    generator_prompt_version: Mapped[str | None] = mapped_column(String(40))
    generator_schema_version: Mapped[str | None] = mapped_column(String(40))
    validator_model: Mapped[str | None] = mapped_column(String(120))
    validator_prompt_version: Mapped[str | None] = mapped_column(String(40))
    validator_schema_version: Mapped[str | None] = mapped_column(String(40))
    guardrail_version: Mapped[str] = mapped_column(String(40), default="resume-claims-v1")
    generation_count: Mapped[int] = mapped_column(Integer, default=0)
    job: Mapped[Job] = relationship(back_populates="resume_tailoring")


class JobDecision(TimestampMixin, Base):
    __tablename__ = "job_decisions"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_job_decisions_job_id"),
        CheckConstraint(
            "role_classification_confidence IN ('High', 'Medium', 'Low')",
            name="ck_job_decisions_role_confidence",
        ),
        CheckConstraint(
            "auto_eligibility_status IN ('Eligible', 'PossiblyEligible', 'Ineligible', 'Unknown')",
            name="ck_job_decisions_auto_eligibility",
        ),
        CheckConstraint(
            "effective_eligibility_status IN ('Eligible', 'PossiblyEligible', 'Ineligible', 'Unknown')",
            name="ck_job_decisions_effective_eligibility",
        ),
        CheckConstraint(
            "eligibility_override IS NULL OR eligibility_override IN "
            "('Eligible', 'PossiblyEligible', 'Ineligible', 'Unknown')",
            name="ck_job_decisions_eligibility_override",
        ),
        CheckConstraint(
            "target_role_fit IN ('Primary', 'Secondary', 'Exploratory', 'Low', 'NotTarget', 'Unknown')",
            name="ck_job_decisions_target_role_fit",
        ),
        CheckConstraint(
            "pre_match_decision IN ('WorthAnalyzing', 'LowPriority', 'Exclude')",
            name="ck_job_decisions_pre_match",
        ),
        CheckConstraint(
            "final_decision IS NULL OR final_decision IN ('Priority', 'Apply', 'Consider', 'Skip')",
            name="ck_job_decisions_final",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    auto_role_family: Mapped[str] = mapped_column(String(40), index=True)
    role_family_override: Mapped[str | None] = mapped_column(String(40), index=True)
    effective_role_family: Mapped[str] = mapped_column(String(40), index=True)
    role_classification_confidence: Mapped[str] = mapped_column(String(10))
    role_classification_reasons: Mapped[list] = mapped_column(JSON, default=list)
    classifier_version: Mapped[str] = mapped_column(String(40))

    auto_eligibility_status: Mapped[str] = mapped_column(String(24), index=True)
    eligibility_override: Mapped[str | None] = mapped_column(String(24), index=True)
    effective_eligibility_status: Mapped[str] = mapped_column(String(24), index=True)
    eligibility_reasons: Mapped[list] = mapped_column(JSON, default=list)
    blocking_requirements: Mapped[list] = mapped_column(JSON, default=list)
    unknown_requirements: Mapped[list] = mapped_column(JSON, default=list)
    eligibility_override_reason: Mapped[str | None] = mapped_column(Text)

    target_role_fit: Mapped[str] = mapped_column(String(20), index=True)
    pre_match_decision: Mapped[str] = mapped_column(String(24), index=True)
    final_decision: Mapped[str | None] = mapped_column(String(16), index=True)
    decision_reasons: Mapped[list] = mapped_column(JSON, default=list)

    candidate_hash: Mapped[str] = mapped_column(String(64), index=True)
    target_roles_hash: Mapped[str] = mapped_column(String(64), index=True)
    job_input_hash: Mapped[str] = mapped_column(String(64), index=True)
    analysis_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    engine_version: Mapped[str] = mapped_column(String(40))
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    job: Mapped[Job] = relationship(back_populates="decision")
