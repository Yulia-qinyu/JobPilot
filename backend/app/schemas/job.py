from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import JDRequirements
from app.schemas.profile import TargetCompanyRead, TargetRoleRead

JobStatus = Literal[
    "Interested",
    "Preparing",
    "Applied",
    "OA",
    "Interview",
    "Final Interview",
    "Offer",
    "Rejected",
    "Withdrawn",
]
JobSort = Literal["recent", "company", "match_score"]


class JobUrlPreviewRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2_000)


class JobJdPreviewRequest(BaseModel):
    job_description: str = Field(min_length=50, max_length=100_000)


class JobPreview(BaseModel):
    company: str | None
    role: str | None
    location: str | None
    recruitment_type: str | None
    published_date: date | None
    source_url: str | None
    original_jd: str
    structured_jd: JDRequirements
    parser_model: str
    parser_prompt_version: str
    parser_schema_version: str
    source_content_hash: str


class JobAnalysisPreviewRequest(BaseModel):
    structured_jd: JDRequirements


class JobCreate(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    recruitment_type: str | None = Field(default=None, max_length=120)
    source_url: str | None = Field(default=None, max_length=2_000)
    original_jd: str = Field(min_length=50, max_length=100_000)
    structured_jd: JDRequirements
    published_date: date | None = None
    status: JobStatus = "Interested"
    parser_model: str | None = Field(default=None, max_length=120)
    parser_prompt_version: str | None = Field(default=None, max_length=40)
    parser_schema_version: str | None = Field(default=None, max_length=40)
    source_content_hash: str | None = Field(default=None, min_length=64, max_length=64)
    preview_artifact_token: str | None = Field(default=None, min_length=20, max_length=200)


class JobUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    recruitment_type: str | None = Field(default=None, max_length=120)
    published_date: date | None = None
    status: JobStatus | None = None
    application_date: date | None = None
    next_stage: str | None = Field(default=None, max_length=255)
    interview_date: date | None = None
    notes: str | None = Field(default=None, max_length=10_000)
    structured_jd: JDRequirements | None = None
    application_status_id: int | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    location: str | None
    recruitment_type: str | None
    source_url: str | None
    original_jd: str
    structured_jd: JDRequirements
    published_date: date | None
    status: JobStatus
    match_score: int | None
    recommendation: str | None
    application_date: date | None
    next_stage: str | None
    interview_date: date | None
    notes: str | None
    source: str | None
    external_job_id: str | None
    external_job_code: str | None
    source_metadata: dict | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
    application_status_id: int | None = None
    application_status_label: str | None = None
    analysis_promoted: bool = False


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    location: str | None
    status: JobStatus
    match_score: int | None
    source: str | None
    external_job_code: str | None
    created_at: datetime
    updated_at: datetime
    application_status_id: int | None = None


class DashboardCounts(BaseModel):
    total: int
    applied: int
    interviews: int
    offers: int


class DashboardProfile(BaseModel):
    preferred_location: str | None
    target_companies: list[TargetCompanyRead]
    target_roles: list[TargetRoleRead]


class DashboardRead(BaseModel):
    counts: DashboardCounts
    profile: DashboardProfile
    jobs: list[JobListItem]
