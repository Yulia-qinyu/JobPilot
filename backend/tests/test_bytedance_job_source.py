import json
from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest

from app.config import Settings
from app.services.job_sources.bytedance import (
    ByteDanceJobSource,
    JobSourceError,
    SourceRecordError,
    SourceResultTooLargeError,
    UnsupportedJobSourceUrlError,
)


def raw_job(index: int, *, description: str | None = None, requirement: str | None = None):
    return {
        "id": str(7000 + index),
        "code": f"A{index:05d}",
        "title": f"产品经理 {index}",
        "description": description or "1、负责产品规划；2、推动跨团队交付。",
        "requirement": requirement or "1、具备产品经验；2、熟悉 SQL 者优先。",
        "city_list": [{"code": "CT_11", "name": "北京"}],
        "recruit_type": {"id": "101", "name": "正式"},
        "job_category": {"id": "product", "name": "产品"},
        "job_function": {"id": "pm", "name": "产品经理"},
        "job_subject": None,
        "publish_time": 1_777_000_000_000,
    }


def adapter_with(handler, **settings):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ByteDanceJobSource(
        Settings(job_import_page_delay_seconds=0, **settings),
        client=client,
        sleep=lambda _: None,
    )


def test_experienced_and_campus_urls_map_semantic_filters() -> None:
    adapter = ByteDanceJobSource(Settings())
    experienced = adapter.parse_search_url(
        "https://jobs.bytedance.com/experienced/position?keywords=AI%20PM"
        "&category=cat1,cat2&location=CT_11&current=9&limit=10&_signature=secret"
    )
    assert experienced.channel == "society"
    assert experienced.keyword == "AI PM"
    assert experienced.category_ids == ("cat1", "cat2")
    assert experienced.location_codes == ("CT_11",)
    assert experienced.recruitment_ids == ("101",)
    assert "current=" not in experienced.normalized_url
    assert "_signature" not in experienced.normalized_url

    campus = adapter.parse_search_url(
        "https://jobs.bytedance.com/campus/position?type=3&project=project1"
    )
    assert campus.channel == "campus"
    assert campus.recruitment_ids == ("202", "301")
    assert campus.subject_ids == ("project1",)


@pytest.mark.parametrize(
    "url",
    [
        "http://jobs.bytedance.com/experienced/position",
        "https://evil.example/experienced/position",
        "https://jobs.bytedance.com/referral/position",
        "https://user:password@jobs.bytedance.com/experienced/position",
    ],
)
def test_invalid_search_urls_are_rejected(url: str) -> None:
    with pytest.raises(UnsupportedJobSourceUrlError):
        ByteDanceJobSource(Settings()).parse_search_url(url)


def test_pagination_fetches_120_jobs_in_two_requests() -> None:
    offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        offsets.append(body["offset"])
        start = body["offset"]
        rows = [raw_job(index) for index in range(start, min(start + 100, 120))]
        return httpx.Response(200, json={"code": 0, "data": {"count": 120, "job_post_list": rows}})

    adapter = adapter_with(handler)
    pages = list(
        adapter.discover(
            adapter.parse_search_url("https://jobs.bytedance.com/experienced/position")
        )
    )
    assert offsets == [0, 100]
    assert [len(page.records) for page in pages] == [100, 20]


def test_short_empty_and_repeated_pages_terminate_safely() -> None:
    calls = 0

    def short_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"code": 0, "data": {"count": 20, "job_post_list": [raw_job(1)]}}
        )

    assert (
        len(
            list(
                adapter_with(short_handler).discover(
                    ByteDanceJobSource(Settings()).parse_search_url(
                        "https://jobs.bytedance.com/experienced/position"
                    )
                )
            )
        )
        == 1
    )

    def repeated_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"count": 250, "job_post_list": [raw_job(i) for i in range(100)]},
            },
        )

    repeated = adapter_with(repeated_handler)
    assert (
        len(
            list(
                repeated.discover(
                    repeated.parse_search_url("https://jobs.bytedance.com/experienced/position")
                )
            )
        )
        == 1
    )
    assert calls == 2


def test_result_cap_malformed_response_and_nonzero_code_fail() -> None:
    too_many = adapter_with(
        lambda _: httpx.Response(
            200, json={"code": 0, "data": {"count": 2001, "job_post_list": []}}
        )
    )
    with pytest.raises(SourceResultTooLargeError):
        list(
            too_many.discover(
                too_many.parse_search_url("https://jobs.bytedance.com/experienced/position")
            )
        )

    bounded_discovery = adapter_with(
        lambda _: httpx.Response(
            200, json={"code": 0, "data": {"count": 2500, "job_post_list": []}}
        )
    )
    bounded_query = bounded_discovery.parse_search_url(
        "https://jobs.bytedance.com/experienced/position"
    )
    bounded_query = replace(bounded_query, result_limit=500)
    assert next(iter(bounded_discovery.discover(bounded_query))).total_count == 2500

    malformed = adapter_with(
        lambda _: httpx.Response(200, text="not-json", headers={"content-type": "application/json"})
    )
    with pytest.raises(JobSourceError):
        list(
            malformed.discover(
                malformed.parse_search_url("https://jobs.bytedance.com/experienced/position")
            )
        )

    nonzero = adapter_with(lambda _: httpx.Response(200, json={"code": -1, "message": "bad"}))
    with pytest.raises(JobSourceError):
        list(
            nonzero.discover(
                nonzero.parse_search_url("https://jobs.bytedance.com/experienced/position")
            )
        )


def test_page_safety_cap_does_not_silently_truncate() -> None:
    adapter = adapter_with(
        lambda _: httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"count": 150, "job_post_list": [raw_job(i) for i in range(100)]},
            },
        ),
        job_import_max_pages=1,
    )
    with pytest.raises(SourceResultTooLargeError):
        list(
            adapter.discover(
                adapter.parse_search_url("https://jobs.bytedance.com/experienced/position")
            )
        )


def test_retryable_status_retries_but_deterministic_400_does_not() -> None:
    attempts = 0
    sleeps: list[float] = []

    def transient(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"code": 0, "data": {"count": 0, "job_post_list": []}})

    adapter = ByteDanceJobSource(
        Settings(job_import_page_delay_seconds=0),
        client=httpx.Client(transport=httpx.MockTransport(transient)),
        sleep=sleeps.append,
    )
    list(
        adapter.discover(
            adapter.parse_search_url("https://jobs.bytedance.com/experienced/position")
        )
    )
    assert attempts == 2
    assert sleeps == [1]

    bad_attempts = 0

    def bad(_request: httpx.Request) -> httpx.Response:
        nonlocal bad_attempts
        bad_attempts += 1
        return httpx.Response(400)

    bad_adapter = adapter_with(bad)
    with pytest.raises(JobSourceError):
        list(
            bad_adapter.discover(
                bad_adapter.parse_search_url("https://jobs.bytedance.com/experienced/position")
            )
        )
    assert bad_attempts == 1
    assert ByteDanceJobSource._retry_delay("not-a-number", 2) == 4
    assert ByteDanceJobSource._retry_delay("30", 0) == 5


def test_deterministic_normalization_preserves_raw_and_separates_preferred() -> None:
    adapter = ByteDanceJobSource(Settings())
    record = adapter._record(raw_job(1), "society")
    draft = adapter.normalize(record)
    assert draft.company == "字节跳动"
    assert draft.published_date == datetime.fromtimestamp(1_777_000_000, tz=UTC).date()
    assert draft.original_jd == (
        "职位描述\n1、负责产品规划；2、推动跨团队交付。\n\n"
        "职位要求\n1、具备产品经验；2、熟悉 SQL 者优先。"
    )
    assert draft.structured_jd.responsibilities == ["负责产品规划；", "推动跨团队交付。"]
    assert draft.structured_jd.required_skills == ["具备产品经验；"]
    assert draft.structured_jd.preferred_skills == ["熟悉 SQL 者优先。"]
    assert all(item.priority == "medium" for item in draft.structured_jd.key_requirements)
    assert draft.structured_jd.knowledge_topics == ["产品", "产品经理"]
    assert draft.source_metadata["normalizer_version"] == "bytedance-v1"
    assert len(draft.source_content_hash) == 64


def test_recruitment_channel_is_canonical_and_preserves_source_label() -> None:
    adapter = ByteDanceJobSource(Settings())
    experienced = adapter._record(raw_job(1), "society")
    campus = adapter._record(raw_job(2), "campus")

    assert experienced.recruitment_type == "experienced"
    assert experienced.source_metadata["source_recruitment_type"] == "正式"
    assert experienced.source_metadata["recruitment_channel"] == "experienced"
    assert campus.recruitment_type == "campus"
    assert campus.source_metadata["recruitment_channel"] == "campus"


def test_missing_source_fields_fail_without_invention() -> None:
    adapter = ByteDanceJobSource(Settings())
    record = adapter._record({"id": "1", "title": "PM", "description": "职责"}, "campus")
    with pytest.raises(SourceRecordError) as captured:
        adapter.normalize(record)
    assert captured.value.code == "MISSING_JOB_CONTENT"
