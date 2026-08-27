from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.schemas.analysis import JDRequirements


@dataclass(frozen=True)
class SourceSearchQuery:
    source: str
    normalized_url: str
    channel: str
    keyword: str = ""
    category_ids: tuple[str, ...] = ()
    location_codes: tuple[str, ...] = ()
    subject_ids: tuple[str, ...] = ()
    recruitment_ids: tuple[str, ...] = ()
    function_ids: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    provider: str = ""
    tenant: str | None = None
    result_limit: int | None = None


@dataclass(frozen=True)
class SourceJobRecord:
    source: str
    external_job_id: str
    external_job_code: str | None
    title: str
    locations: tuple[str, ...]
    recruitment_type: str | None
    detail_url: str
    description: str
    requirements: str
    published_date: date | None
    source_metadata: dict = field(default_factory=dict)
    provider: str = ""
    tenant: str | None = None


@dataclass(frozen=True)
class SourceJobPage:
    records: tuple[SourceJobRecord, ...]
    total_count: int
    offset: int


@dataclass(frozen=True)
class ImportedJobDraft:
    source: str
    external_job_id: str
    external_job_code: str | None
    company: str
    role: str
    location: str | None
    recruitment_type: str | None
    source_url: str
    original_jd: str
    structured_jd: JDRequirements
    published_date: date | None
    source_metadata: dict
    source_content_hash: str
    provider: str = ""
    tenant: str | None = None


class JobSourceAdapter(Protocol):
    source: str

    def supports(self, search_url: str) -> bool: ...

    def parse_search_url(self, search_url: str) -> SourceSearchQuery: ...

    def discover(self, query: SourceSearchQuery) -> Iterable[SourceJobPage]: ...

    def normalize(self, record: SourceJobRecord) -> ImportedJobDraft: ...
