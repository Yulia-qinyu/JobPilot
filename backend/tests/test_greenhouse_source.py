import httpx
import pytest

from app.config import Settings
from app.services.job_sources.bytedance import JobSourceError, UnsupportedJobSourceUrlError
from app.services.job_sources.catalog import SourceCatalog
from app.services.job_sources.greenhouse import GreenhouseJobSource
from app.services.source_acquisition import SourceAcquisitionService


def payload() -> dict:
    return {
        "jobs": [
            {
                "id": 123,
                "title": "Senior AI Product Manager, Agents",
                "absolute_url": "https://job-boards.greenhouse.io/scaleai/jobs/123",
                "location": {"name": "San Francisco, CA"},
                "content": "<h2>What you will do</h2><ul><li>Build AI agent products with engineering.</li></ul><h2>Qualifications</h2><ul><li>At least 5 years of product experience.</li><li>LLM experience preferred.</li></ul>",
                "departments": [{"name": "Gen AI Product"}],
                "offices": [{"name": "San Francisco"}],
                "updated_at": "2026-08-25T01:00:00Z",
            }
        ]
    }


def adapter(handler) -> GreenhouseJobSource:
    return GreenhouseJobSource(
        Settings(job_import_max_retries=1),
        catalog=SourceCatalog(include_disabled_greenhouse=True),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _seconds: None,
    )


def test_detects_verified_board_and_rejects_unknown_tenant() -> None:
    source = adapter(lambda _request: httpx.Response(200, json=payload()))
    assert source.supports("https://job-boards.greenhouse.io/scaleai")
    assert source.supports("https://boards.greenhouse.io/greenhouse/jobs/123")
    assert not source.supports("https://job-boards.greenhouse.io/unverified-company")
    with pytest.raises(UnsupportedJobSourceUrlError):
        source.parse_search_url("https://job-boards.greenhouse.io/unverified-company")


def test_listing_identity_and_deterministic_normalization() -> None:
    source = adapter(lambda request: httpx.Response(200, json=payload(), request=request))
    query = source.parse_search_url("https://job-boards.greenhouse.io/scaleai")
    pages = list(source.discover(query))
    record = pages[0].records[0]
    draft = source.normalize(record)
    assert query.tenant == "scaleai"
    assert record.source == draft.source == "greenhouse:scaleai"
    assert record.external_job_id == "123"
    assert draft.company == "Scale AI"
    assert "Build AI agent products" in draft.original_jd
    assert draft.source_metadata["tenant"] == "scaleai"


def test_empty_malformed_timeout_and_duplicate_payload_behavior() -> None:
    empty = adapter(lambda request: httpx.Response(200, json={"jobs": []}, request=request))
    assert next(iter(empty.discover(empty.query_for_tenant("scaleai")))).records == ()
    malformed = adapter(lambda request: httpx.Response(200, json={"jobs": {}}, request=request))
    with pytest.raises(JobSourceError):
        list(malformed.discover(malformed.query_for_tenant("scaleai")))

    def timeout(request):
        raise httpx.ConnectTimeout("timeout", request=request)

    failing = adapter(timeout)
    with pytest.raises(JobSourceError):
        list(failing.discover(failing.query_for_tenant("scaleai")))

    duplicated = payload()
    duplicated["jobs"].append(dict(duplicated["jobs"][0]))
    duplicate_source = adapter(
        lambda request: httpx.Response(200, json=duplicated, request=request)
    )
    records, duplicates = SourceAcquisitionService().discover(
        duplicate_source, duplicate_source.query_for_tenant("scaleai")
    )
    assert len(records) == 1 and duplicates == 1
