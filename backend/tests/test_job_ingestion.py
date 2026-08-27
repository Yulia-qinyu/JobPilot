import socket

import httpx
import pytest

from app.config import Settings
from app.services.job_ingestion import (
    JobIngestionError,
    JobPageFetcher,
    UnsafeJobUrlError,
    validate_public_job_url,
)


def public_resolver(host: str, port: int):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/job",
        "http://localhost/job",
        "http://127.0.0.1/job",
        "http://10.0.0.1/job",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/job",
        "https://user:password@example.com/job",
        "https://example.com:8443/job",
    ],
)
def test_url_validation_blocks_unsafe_targets(url: str) -> None:
    with pytest.raises(UnsafeJobUrlError):
        validate_public_job_url(url)


def test_url_validation_accepts_public_http_url() -> None:
    assert (
        validate_public_job_url("https://jobs.example.com/opening#details", public_resolver)
        == "https://jobs.example.com/opening"
    )


def test_redirect_target_is_validated_before_following() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    fetcher = JobPageFetcher(
        Settings(),
        resolver=public_resolver,
        client=httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False),
    )
    with pytest.raises(UnsafeJobUrlError):
        fetcher.fetch("https://jobs.example.com/opening")
    assert requests == ["https://jobs.example.com/opening"]


def test_fetch_extracts_readable_content_with_size_limit() -> None:
    html = (
        "<html><body><nav>Menu</nav><main><h1>Product Manager</h1><p>"
        + ("Lead product discovery and delivery with engineering partners. " * 6)
        + "</p></main></body></html>"
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text=html)

    fetcher = JobPageFetcher(
        Settings(job_fetch_max_bytes=10_000),
        resolver=public_resolver,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    final_url, text = fetcher.fetch("https://jobs.example.com/opening")
    assert final_url == "https://jobs.example.com/opening"
    assert "Product Manager" in text
    assert "Menu" not in text


def test_http_failure_returns_ingestion_fallback_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    fetcher = JobPageFetcher(
        Settings(),
        resolver=public_resolver,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(JobIngestionError) as captured:
        fetcher.fetch("https://jobs.example.com/protected")
    assert captured.value.code == "JOB_URL_UNREADABLE"
