from __future__ import annotations

from datetime import date as DateValue
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

JobSearchStrategy = Literal["high_volume", "focused", "balanced", "interview_first"]
PlanType = Literal["application", "resume", "interview_prep", "job_search", "follow_up", "other"]
PlanStatus = Literal["todo", "done"]


class StrategyRead(BaseModel):
    job_search_strategy: JobSearchStrategy


class StrategyUpdate(BaseModel):
    job_search_strategy: JobSearchStrategy


class ApplicationStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    label: str
    sort_order: int
    is_system_default: bool
    is_active: bool
    legacy_status: str | None


class ApplicationStatusCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)


class ApplicationStatusUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)


class ApplicationStatusDeleteRequest(BaseModel):
    migrate_to_status_id: int | None = None


class ApplicationStatusDeleteResult(BaseModel):
    deleted_id: int
    migrated_jobs: int


class PlanItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    date: DateValue
    time_optional: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    job_id: int | None = None
    type: PlanType = "other"
    notes: str | None = Field(default=None, max_length=5_000)


class PlanItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    date: DateValue | None = None
    time_optional: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    job_id: int | None = None
    type: PlanType | None = None
    status: PlanStatus | None = None
    notes: str | None = Field(default=None, max_length=5_000)

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required.")
        return self


class PlanJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company: str
    role: str


class PlanItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    date: DateValue
    time_optional: str | None
    job_id: int | None
    type: PlanType
    status: PlanStatus
    notes: str | None
    created_by: Literal["user", "agent_suggestion"]
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    job: PlanJobRead | None = None
