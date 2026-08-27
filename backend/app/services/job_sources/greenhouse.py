import hashlib
import html
import json
import re
import time
from collections.abc import Callable, Iterable
from html.parser import HTMLParser
from typing import ClassVar
from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.schemas.analysis import JDRequirements, KeyRequirement
from app.services.job_sources.base import (
    ImportedJobDraft,
    SourceJobPage,
    SourceJobRecord,
    SourceSearchQuery,
)
from app.services.job_sources.bytedance import (
    JobSourceError,
    SourceRecordError,
    SourceResultTooLargeError,
    UnsupportedJobSourceUrlError,
)
from app.services.job_sources.catalog import SourceCatalog


class _ReadableHTML(HTMLParser):
    BLOCKS: ClassVar[set[str]] = {"p", "li", "div", "h1", "h2", "h3", "h4", "br"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, _attrs) -> None:
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


class GreenhouseJobSource:
    provider = "greenhouse"
    NORMALIZER_VERSION = "greenhouse-v1"
    ALLOWED_HOSTS: ClassVar[set[str]] = {
        "job-boards.greenhouse.io",
        "boards.greenhouse.io",
    }

    def __init__(
        self,
        settings: Settings,
        *,
        catalog: SourceCatalog | None = None,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.settings = settings
        self.catalog = catalog or SourceCatalog()
        self.sleep = sleep
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(settings.job_import_timeout_seconds),
            follow_redirects=False,
            trust_env=False,
        )
        self.source = "greenhouse"

    def supports(self, search_url: str) -> bool:
        try:
            parsed = urlsplit(search_url.strip())
        except ValueError:
            return False
        if (
            parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower() not in self.ALLOWED_HOSTS
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
        ):
            return False
        tenant = self._tenant_from_path(parsed.path)
        return bool(tenant and self.catalog.by_tenant(tenant))

    def parse_search_url(self, search_url: str) -> SourceSearchQuery:
        if not self.supports(search_url):
            raise UnsupportedJobSourceUrlError(
                "Only verified public Greenhouse boards are supported."
            )
        parsed = urlsplit(search_url.strip())
        tenant = self._tenant_from_path(parsed.path)
        assert tenant is not None
        entry = self.catalog.by_tenant(tenant)
        assert entry is not None
        return SourceSearchQuery(
            source=entry.source_key,
            normalized_url=f"https://job-boards.greenhouse.io/{tenant}",
            channel="public_board",
            provider=self.provider,
            tenant=tenant,
        )

    def query_for_tenant(self, tenant: str, keyword: str = "") -> SourceSearchQuery:
        entry = self.catalog.by_tenant(tenant)
        if entry is None:
            raise UnsupportedJobSourceUrlError("Unknown Greenhouse tenant.")
        return SourceSearchQuery(
            source=entry.source_key,
            normalized_url=f"https://job-boards.greenhouse.io/{tenant}",
            channel="public_board",
            keyword=keyword,
            provider=self.provider,
            tenant=tenant,
        )

    def discover(self, query: SourceSearchQuery) -> Iterable[SourceJobPage]:
        if not query.tenant or self.catalog.by_tenant(query.tenant) is None:
            raise UnsupportedJobSourceUrlError("Unknown Greenhouse tenant.")
        payload = self._fetch(query.tenant)
        raw_jobs = payload.get("jobs")
        if not isinstance(raw_jobs, list):
            raise JobSourceError("Greenhouse returned a malformed job list.")
        if len(raw_jobs) > self.settings.job_import_max_jobs:
            raise SourceResultTooLargeError()
        records = tuple(self._record(item, query.tenant) for item in raw_jobs)
        yield SourceJobPage(records=records, total_count=len(records), offset=0)

    def normalize(self, record: SourceJobRecord) -> ImportedJobDraft:
        tenant = record.tenant or self._tenant_from_source(record.source)
        entry = self.catalog.by_tenant(tenant)
        if entry is None:
            raise SourceRecordError("Unknown Greenhouse tenant.", "UNKNOWN_SOURCE_TENANT")
        external_id = record.external_job_id.strip()
        role = " ".join(record.title.split())
        if not external_id or not role:
            raise SourceRecordError("Greenhouse job is missing identity or title.")
        description = record.description.strip()
        requirements = record.requirements.strip()
        if not description:
            raise SourceRecordError(
                "Greenhouse job has no readable content.", "MISSING_JOB_CONTENT"
            )
        responsibilities = self._items(description)
        required = self._items(requirements) if requirements else []
        original_jd = (
            f"Job Description\n{description}\n\nRequirements\n{requirements}"
            if requirements and requirements != description
            else description
        )
        structured = JDRequirements(
            role=role,
            company=entry.company_name,
            location="、".join(record.locations) or None,
            recruitment_type=record.recruitment_type,
            role_summary=responsibilities[0][:300] if responsibilities else None,
            key_requirements=[
                KeyRequirement(title=item[:80], explanation=item, priority="medium")
                for item in required[:7]
            ],
            responsibilities=responsibilities,
            required_skills=required,
            preferred_skills=[item for item in required if self._preferred(item)],
        )
        metadata = {
            **record.source_metadata,
            "provider": self.provider,
            "tenant": tenant,
            "normalizer_version": self.NORMALIZER_VERSION,
        }
        return ImportedJobDraft(
            source=entry.source_key,
            external_job_id=external_id,
            external_job_code=record.external_job_code,
            company=entry.company_name,
            role=role,
            location="、".join(record.locations) or None,
            recruitment_type=record.recruitment_type,
            source_url=record.detail_url,
            original_jd=original_jd,
            structured_jd=structured,
            published_date=None,
            source_metadata=metadata,
            source_content_hash=hashlib.sha256(original_jd.encode()).hexdigest(),
            provider=self.provider,
            tenant=tenant,
        )

    def close(self) -> None:
        self.client.close()

    def _fetch(self, tenant: str) -> dict:
        url = f"https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs"
        last_error: Exception | None = None
        for attempt in range(self.settings.job_import_max_retries + 1):
            try:
                with self.client.stream("GET", url, params={"content": "true"}) as response:
                    if (
                        response.status_code in {429, 500, 502, 503, 504}
                        and attempt < self.settings.job_import_max_retries
                    ):
                        self.sleep(2**attempt)
                        continue
                    if response.status_code != 200:
                        raise JobSourceError(
                            f"Greenhouse search failed with HTTP {response.status_code}."
                        )
                    if "application/json" not in response.headers.get("content-type", "").lower():
                        raise JobSourceError("Greenhouse returned a non-JSON response.")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.settings.job_import_max_response_bytes:
                            raise JobSourceError(
                                "Greenhouse response exceeded the safe size limit."
                            )
                        chunks.append(chunk)
                payload = json.loads(b"".join(chunks))
                if not isinstance(payload, dict):
                    raise JobSourceError("Greenhouse returned malformed JSON.")
                return payload
            except JobSourceError:
                raise
            except (httpx.HTTPError, UnicodeError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self.settings.job_import_max_retries:
                    break
                self.sleep(2**attempt)
        raise JobSourceError("Greenhouse search is temporarily unavailable.") from last_error

    def _record(self, raw: object, tenant: str) -> SourceJobRecord:
        if not isinstance(raw, dict):
            return SourceJobRecord(f"greenhouse:{tenant}", "", None, "", (), None, "", "", "", None)
        content = self._html_text(str(raw.get("content") or ""))
        description, requirements = self._sections(content)
        location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
        metadata = {
            "departments": self._names(raw.get("departments")),
            "offices": self._names(raw.get("offices")),
            "updated_at": raw.get("updated_at"),
        }
        return SourceJobRecord(
            source=f"greenhouse:{tenant}",
            external_job_id=str(raw.get("id") or ""),
            external_job_code=None,
            title=str(raw.get("title") or ""),
            locations=(str(location.get("name")),) if location.get("name") else (),
            recruitment_type=None,
            detail_url=str(raw.get("absolute_url") or f"https://job-boards.greenhouse.io/{tenant}"),
            description=description,
            requirements=requirements,
            published_date=None,
            source_metadata=metadata,
            provider=self.provider,
            tenant=tenant,
        )

    @staticmethod
    def _html_text(value: str) -> str:
        parser = _ReadableHTML()
        parser.feed(html.unescape(value))
        return parser.text()

    @staticmethod
    def _sections(text: str) -> tuple[str, str]:
        lines = [line for line in text.splitlines() if line]
        marker = next(
            (
                index
                for index, line in enumerate(lines)
                if re.search(
                    r"requirements|qualifications|what you(?:'|’)ll need|who you are",
                    line,
                    re.IGNORECASE,
                )
            ),
            None,
        )
        if marker is None:
            return text, text
        description = "\n".join(lines[:marker]).strip() or text
        requirements = "\n".join(lines[marker:]).strip()
        return description, requirements

    @staticmethod
    def _items(value: str) -> list[str]:
        return list(
            dict.fromkeys(
                line.strip(" -•\t") for line in value.splitlines() if len(line.strip()) >= 8
            )
        )

    @staticmethod
    def _preferred(value: str) -> bool:
        return bool(re.search(r"preferred|nice to have|plus|优先|加分", value, re.IGNORECASE))

    @staticmethod
    def _names(raw: object) -> list[str]:
        return (
            [str(item.get("name")) for item in raw if isinstance(item, dict) and item.get("name")]
            if isinstance(raw, list)
            else []
        )

    @staticmethod
    def _tenant_from_path(path: str) -> str | None:
        parts = [part for part in path.split("/") if part]
        return parts[0].casefold() if parts else None

    @staticmethod
    def _tenant_from_source(source: str) -> str:
        return source.split(":", 1)[1] if ":" in source else ""
