import hashlib
import json
import re
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import httpx

from app.config import Settings
from app.schemas.analysis import JDRequirements, KeyRequirement
from app.services.job_sources.base import (
    ImportedJobDraft,
    SourceJobPage,
    SourceJobRecord,
    SourceSearchQuery,
)


class JobSourceError(ValueError):
    def __init__(self, message: str, code: str = "JOB_SOURCE_UNAVAILABLE"):
        super().__init__(message)
        self.code = code


class UnsupportedJobSourceUrlError(JobSourceError):
    def __init__(self, message: str = "Unsupported job search URL."):
        super().__init__(message, "UNSUPPORTED_JOB_SOURCE_URL")


class SourceResultTooLargeError(JobSourceError):
    def __init__(self):
        super().__init__(
            "Search result is too large. Refine the filters on the recruitment website.",
            "JOB_SOURCE_RESULT_TOO_LARGE",
        )


class SourceRecordError(JobSourceError):
    def __init__(self, message: str, code: str = "INVALID_SOURCE_JOB"):
        super().__init__(message, code)


class ByteDanceJobSource:
    source = "bytedance"
    API_URL = "https://jobs.bytedance.com/api/v1/search/job/posts"
    NORMALIZER_VERSION = "bytedance-v1"
    ALLOWED_PATHS: ClassVar[dict[str, str]] = {
        "/experienced/position": "society",
        "/campus/position": "campus",
    }

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.settings = settings
        self.sleep = sleep
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(settings.job_import_timeout_seconds),
            follow_redirects=False,
            trust_env=False,
        )

    def supports(self, search_url: str) -> bool:
        try:
            parsed = urlsplit(search_url.strip())
        except ValueError:
            return False
        return (
            parsed.scheme.lower() == "https"
            and (parsed.hostname or "").rstrip(".").lower() == "jobs.bytedance.com"
            and parsed.port in (None, 443)
            and parsed.path.rstrip("/") in self.ALLOWED_PATHS
            and not parsed.username
            and not parsed.password
        )

    def parse_search_url(self, search_url: str) -> SourceSearchQuery:
        if not self.supports(search_url):
            raise UnsupportedJobSourceUrlError(
                "Only ByteDance experienced or campus search-result URLs are supported."
            )
        parsed = urlsplit(search_url.strip())
        path = parsed.path.rstrip("/")
        channel = self.ALLOWED_PATHS[path]
        params = parse_qs(parsed.query, keep_blank_values=False)
        recruitment_ids = self._recruitment_ids(channel, self._first(params, "type"))
        semantic_params = {
            "keywords": self._first(params, "keywords"),
            "category": self._first(params, "category"),
            "location": self._first(params, "location"),
            "project": self._first(params, "project"),
            "type": self._first(params, "type"),
            "job_hot_flag": self._first(params, "job_hot_flag"),
            "functionCategory": self._first(params, "functionCategory"),
            "tag": self._first(params, "tag"),
        }
        normalized_query = urlencode(
            [(key, value) for key, value in semantic_params.items() if value]
        )
        normalized_url = urlunsplit(("https", "jobs.bytedance.com", path, normalized_query, ""))
        return SourceSearchQuery(
            source=self.source,
            normalized_url=normalized_url,
            channel=channel,
            keyword=semantic_params["keywords"],
            category_ids=self._csv(semantic_params["category"]),
            location_codes=self._csv(semantic_params["location"]),
            subject_ids=self._csv(semantic_params["project"]),
            recruitment_ids=recruitment_ids,
            function_ids=self._csv(semantic_params["functionCategory"]),
            tag_ids=self._csv(semantic_params["tag"]),
        )

    def discover(self, query: SourceSearchQuery) -> Iterable[SourceJobPage]:
        seen_pages: set[tuple[str, ...]] = set()
        offset = 0
        total = 0
        for page_number in range(self.settings.job_import_max_pages):
            payload = self._fetch_page(query, offset)
            data = payload.get("data")
            if payload.get("code") != 0 or not isinstance(data, dict):
                raise JobSourceError("ByteDance returned an invalid search response.")
            total = self._integer(data.get("count"))
            if total > self.settings.job_import_max_jobs and query.result_limit is None:
                raise SourceResultTooLargeError()
            raw_records = data.get("job_post_list")
            if not isinstance(raw_records, list):
                raise JobSourceError("ByteDance returned a malformed job list.")
            records = tuple(self._record(item, query.channel) for item in raw_records)
            identity = tuple(item.external_job_id for item in records)
            if identity and identity in seen_pages:
                break
            if identity:
                seen_pages.add(identity)
            yield SourceJobPage(records=records, total_count=total, offset=offset)
            if not records or len(records) < self.settings.job_import_page_size:
                break
            offset += len(records)
            if offset >= total:
                break
            if page_number + 1 < self.settings.job_import_max_pages:
                self.sleep(self.settings.job_import_page_delay_seconds)
        else:
            if offset < total:
                raise SourceResultTooLargeError()

    def close(self) -> None:
        self.client.close()

    def normalize(self, record: SourceJobRecord) -> ImportedJobDraft:
        external_id = record.external_job_id.strip()
        role = " ".join(record.title.split())
        description = record.description.strip()
        requirements_text = record.requirements.strip()
        if not external_id:
            raise SourceRecordError("The source job has no external ID.", "MISSING_EXTERNAL_ID")
        if not role:
            raise SourceRecordError("The source job has no title.", "MISSING_TITLE")
        if not description or not requirements_text:
            raise SourceRecordError(
                "The source job is missing description or requirements.",
                "MISSING_JOB_CONTENT",
            )

        responsibilities = self._split_items(description)
        all_requirements = self._split_items(requirements_text)
        preferred = [item for item in all_requirements if self._is_preferred(item)]
        required = [item for item in all_requirements if item not in preferred]
        role_summary = self._source_summary(description)
        knowledge_topics = self._metadata_topics(record.source_metadata)
        structured = JDRequirements(
            role=role,
            company="字节跳动",
            location="、".join(record.locations) or None,
            recruitment_type=record.recruitment_type,
            published_date=record.published_date,
            role_summary=role_summary,
            key_requirements=[
                KeyRequirement(
                    title=self._requirement_title(item),
                    explanation=item,
                    category=None,
                    priority="medium",
                )
                for item in all_requirements[:7]
            ],
            knowledge_topics=knowledge_topics,
            responsibilities=responsibilities,
            required_skills=required,
            preferred_skills=preferred,
        )
        original_jd = f"职位描述\n{description}\n\n职位要求\n{requirements_text}"
        metadata = {**record.source_metadata, "normalizer_version": self.NORMALIZER_VERSION}
        return ImportedJobDraft(
            source=self.source,
            external_job_id=external_id,
            external_job_code=record.external_job_code,
            company="字节跳动",
            role=role,
            location="、".join(record.locations) or None,
            recruitment_type=record.recruitment_type,
            source_url=record.detail_url,
            original_jd=original_jd,
            structured_jd=structured,
            published_date=record.published_date,
            source_metadata=metadata,
            source_content_hash=hashlib.sha256(original_jd.encode("utf-8")).hexdigest(),
        )

    def _fetch_page(self, query: SourceSearchQuery, offset: int) -> dict:
        body = {
            "keyword": query.keyword,
            "limit": self.settings.job_import_page_size,
            "offset": offset,
            "portal_type": 3,
            "portal_entrance": 1,
            "language": "zh",
            "recruitment_id_list": list(query.recruitment_ids),
            "job_category_id_list": list(query.category_ids),
            "location_code_list": list(query.location_codes),
            "subject_id_list": list(query.subject_ids),
            "tag_id_list": list(query.tag_ids),
            "storefront_id_list": [],
            "job_function_id_list": list(query.function_ids),
        }
        headers = self._headers(query.channel)
        last_error: Exception | None = None
        for attempt in range(self.settings.job_import_max_retries + 1):
            try:
                with self.client.stream(
                    "POST", self.API_URL, headers=headers, json=body
                ) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt >= self.settings.job_import_max_retries:
                            raise JobSourceError(
                                f"ByteDance search failed with HTTP {response.status_code}."
                            )
                        retry_after = response.headers.get("retry-after")
                        delay = self._retry_delay(retry_after, attempt)
                        self.sleep(delay)
                        continue
                    if response.status_code != 200:
                        raise JobSourceError(
                            f"ByteDance search failed with HTTP {response.status_code}."
                        )
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/json" not in content_type:
                        raise JobSourceError("ByteDance returned a non-JSON response.")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.settings.job_import_max_response_bytes:
                            raise JobSourceError("ByteDance response exceeded the safe size limit.")
                        chunks.append(chunk)
                result = json.loads(b"".join(chunks))
                if not isinstance(result, dict):
                    raise JobSourceError("ByteDance returned malformed JSON.")
                return result
            except JobSourceError:
                raise
            except (httpx.HTTPError, UnicodeError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self.settings.job_import_max_retries:
                    break
                self.sleep(2**attempt)
        raise JobSourceError("ByteDance search is temporarily unavailable.") from last_error

    @staticmethod
    def _headers(channel: str) -> dict[str, str]:
        path = "society" if channel == "society" else "campus"
        referer_path = "experienced" if channel == "society" else "campus"
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://jobs.bytedance.com",
            "Referer": f"https://jobs.bytedance.com/{referer_path}/position",
            "portal-channel": path,
            "portal-platform": "pc",
            "website-path": path,
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        }

    @staticmethod
    def _record(raw: object, channel: str) -> SourceJobRecord:
        if not isinstance(raw, dict):
            return SourceJobRecord("bytedance", "", None, "", (), None, "", "", "", None)
        external_id = str(raw.get("id") or "").strip()
        cities = ByteDanceJobSource._names(raw.get("city_list"))
        if not cities and isinstance(raw.get("city_info"), dict):
            cities = ByteDanceJobSource._names([raw["city_info"]])
        recruit_type = raw.get("recruit_type")
        source_recruitment_type = (
            str(recruit_type.get("name") or "").strip() if isinstance(recruit_type, dict) else None
        ) or None
        recruitment_type = "experienced" if channel == "society" else "campus"
        detail_channel = "experienced" if channel == "society" else "campus"
        metadata = {
            "job_category": ByteDanceJobSource._named_metadata(raw.get("job_category")),
            "job_function": ByteDanceJobSource._named_metadata(raw.get("job_function")),
            "job_subject": ByteDanceJobSource._named_metadata(raw.get("job_subject")),
            "department_id": str(raw.get("department_id") or "") or None,
            "source_recruitment_type": source_recruitment_type,
            "recruitment_channel": recruitment_type,
        }
        return SourceJobRecord(
            source="bytedance",
            external_job_id=external_id,
            external_job_code=str(raw.get("code") or "").strip() or None,
            title=str(raw.get("title") or ""),
            locations=tuple(cities),
            recruitment_type=recruitment_type,
            detail_url=(
                f"https://jobs.bytedance.com/{detail_channel}/position/{external_id}/detail"
                if external_id
                else ""
            ),
            description=str(raw.get("description") or ""),
            requirements=str(raw.get("requirement") or ""),
            published_date=ByteDanceJobSource._published_date(raw.get("publish_time")),
            source_metadata=metadata,
        )

    @staticmethod
    def _split_items(text: str) -> list[str]:
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        parts = re.split(
            r"(?:^|\n|(?<=[；。]))\s*(?=(?:\d{1,2}|[一二三四五六七八九十]+)[、.．]\s*)",
            cleaned,
        )
        result: list[str] = []
        for part in parts:
            value = re.sub(r"^(?:\d{1,2}|[一二三四五六七八九十]+)[、.．]\s*", "", part)
            value = " ".join(value.split())
            if value:
                result.append(value)
        return result or ([" ".join(cleaned.split())] if cleaned else [])

    @staticmethod
    def _is_preferred(text: str) -> bool:
        lowered = text.casefold()
        return any(
            marker in lowered for marker in ("优先", "加分", "preferred", "nice to have", "plus")
        )

    @staticmethod
    def _source_summary(description: str) -> str | None:
        first = ByteDanceJobSource._split_items(description)[0]
        if not first:
            return None
        first_sentence = re.split(r"(?<=[。；;])", first, maxsplit=1)[0].strip()
        return first_sentence[:300] or None

    @staticmethod
    def _requirement_title(text: str) -> str:
        title = re.split(r"[，；。,:：]", text, maxsplit=1)[0].strip()
        return (title or text)[:120]

    @staticmethod
    def _metadata_topics(metadata: dict) -> list[str]:
        topics: list[str] = []
        for key in ("job_category", "job_function", "job_subject"):
            value = metadata.get(key)
            if isinstance(value, dict):
                name = str(value.get("name") or "").strip()
                if name and name not in topics:
                    topics.append(name)
        return topics

    @staticmethod
    def _names(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if name and name not in result:
                    result.append(name)
        return result

    @staticmethod
    def _named_metadata(value: object) -> dict | None:
        if not isinstance(value, dict):
            return None
        return {
            "id": str(value.get("id") or "") or None,
            "name": str(value.get("name") or "") or None,
        }

    @staticmethod
    def _published_date(value: object):
        try:
            timestamp = int(value)
            if timestamp <= 0:
                return None
            return datetime.fromtimestamp(timestamp / 1000, tz=UTC).date()
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _integer(value: object) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            raise JobSourceError("ByteDance returned an invalid result count.") from None

    @staticmethod
    def _first(params: dict[str, list[str]], key: str) -> str:
        return params.get(key, [""])[0].strip()

    @staticmethod
    def _csv(value: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))

    @staticmethod
    def _recruitment_ids(channel: str, type_value: str) -> tuple[str, ...]:
        if channel == "society":
            return ("101",)
        if type_value == "3":
            return ("202", "301")
        return ("201",)

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), 5.0))
            except ValueError:
                pass
        return float(min(2**attempt, 5))
