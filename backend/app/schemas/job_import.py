from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobListItem

ImportStatus = Literal["Queued", "Running", "Completed", "Partial", "Failed"]
ImportStage = Literal["Discovering", "Importing", "Completed"]


class JobImportCreate(BaseModel):
    search_url: str = Field(min_length=16, max_length=4_000)


class JobImportFailure(BaseModel):
    external_job_id: str | None = None
    stage: str
    error_code: str


class JobImportSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    search_url: str
    status: ImportStatus
    stage: ImportStage
    discovered_count: int
    processed_count: int
    imported_count: int
    updated_count: int
    duplicate_count: int
    failed_count: int
    result_job_ids: list[int]
    failure_details: list[JobImportFailure]
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobImportJobsRead(BaseModel):
    session_id: int
    jobs: list[JobListItem]
