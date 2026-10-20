from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobNoteAuthor = Literal["human", "agent"]


class JobNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class JobNoteUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class JobNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    content: str
    author_type: JobNoteAuthor
    metadata_json: dict
    created_at: datetime
    updated_at: datetime
