from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RolePriority = Literal["primary", "secondary", "exploratory"]
RoleFamily = Literal[
    "ai_product",
    "fintech_product",
    "data_product",
    "strategy_product",
    "platform_product",
    "growth_product",
    "general_product",
    "product_operations",
    "solution",
    "engineering",
    "algorithm",
    "design",
    "other",
    "unknown",
]


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    structured_profile: dict
    created_at: datetime
    updated_at: datetime


class TargetCompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TargetRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    priority: RolePriority
    auto_role_family: RoleFamily
    role_family_override: RoleFamily | None
    effective_role_family: RoleFamily
    # Backward-compatible effective value for existing Phase 5 clients.
    role_family: RoleFamily


class ExperienceFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    source_type: Literal["resume", "manual"]
    confirmed: bool
    created_at: datetime
    updated_at: datetime


class ExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization: str
    title: str
    experience_type: Literal["work", "project"]
    date_range: str | None
    facts: list[ExperienceFactRead]


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    preferred_location: str | None
    resume: ResumeRead | None
    target_companies: list[TargetCompanyRead]
    target_roles: list[TargetRoleRead]
    experiences: list[ExperienceRead]
    job_search_strategy: Literal["high_volume", "focused", "balanced", "interview_first"]
    candidate_type: Literal["graduate", "experienced", "both"] | None
    graduation_year: int | None


class NameCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TargetRoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    priority: RolePriority = "primary"


class TargetRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    priority: RolePriority | None = None
    role_family_override: RoleFamily | None = None


class LocationUpdate(BaseModel):
    preferred_location: str | None = Field(default=None, max_length=120)


class CandidateIdentityUpdate(BaseModel):
    candidate_type: Literal["graduate", "experienced", "both"] | None
    graduation_year: int | None = Field(default=None, ge=1900, le=2200)


class FactCreate(BaseModel):
    text: str = Field(min_length=2, max_length=2_000)
    confirmed: bool = False


class FactUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=2, max_length=2_000)
    confirmed: bool | None = None
