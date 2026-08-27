import ipaddress
import logging
import socket
from collections.abc import Callable
from time import perf_counter
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from app.config import Settings

logger = logging.getLogger(__name__)
Resolver = Callable[..., list[tuple]]


class JobIngestionError(ValueError):
    def __init__(self, message: str, code: str = "JOB_URL_UNREADABLE"):
        super().__init__(message)
        self.code = code


class UnsafeJobUrlError(JobIngestionError):
    def __init__(self, message: str = "This job URL is not allowed."):
        super().__init__(message, "UNSAFE_JOB_URL")


def validate_public_job_url(url: str, resolver: Resolver = socket.getaddrinfo) -> str:
    candidate = url.strip()
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeJobUrlError("The job URL is invalid.") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeJobUrlError("Only public HTTP or HTTPS job URLs are supported.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeJobUrlError("The job URL is invalid.")
    if port is not None and port not in {80, 443}:
        raise UnsafeJobUrlError("The job URL uses an unsupported port.")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise UnsafeJobUrlError()
    try:
        literal_ip = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        resolved_ips = [literal_ip]
    else:
        try:
            addresses = resolver(
                hostname, port or (443 if parsed.scheme.lower() == "https" else 80)
            )
        except OSError as exc:
            raise JobIngestionError("The job page hostname could not be resolved.") from exc
        if not addresses:
            raise JobIngestionError("The job page hostname could not be resolved.")
        try:
            resolved_ips = [
                ipaddress.ip_address(address[4][0].split("%", 1)[0]) for address in addresses
            ]
        except (ValueError, IndexError) as exc:
            raise UnsafeJobUrlError() from exc
    for ip in resolved_ips:
        if not ip.is_global:
            raise UnsafeJobUrlError()

    normalized_netloc = hostname
    if ":" in hostname:
        normalized_netloc = f"[{hostname}]"
    if port is not None:
        normalized_netloc = f"{normalized_netloc}:{port}"
    return urlunsplit(
        (parsed.scheme.lower(), normalized_netloc, parsed.path or "/", parsed.query, "")
    )


def extract_readable_job_text(body: str, content_type: str) -> str:
    if content_type.startswith("text/plain"):
        lines = body.splitlines()
    else:
        soup = BeautifulSoup(body, "html.parser")
        for element in soup.select("script, style, noscript, svg, nav, header, footer"):
            element.decompose()
        root = soup.find("main") or soup.find("article") or soup.body or soup
        lines = root.get_text("\n").splitlines()
    cleaned: list[str] = []
    previous = ""
    for line in lines:
        value = " ".join(line.split())
        if value and value != previous:
            cleaned.append(value)
            previous = value
    text = "\n".join(cleaned)
    if len(text) < 200:
        raise JobIngestionError("The job page did not contain enough readable content.")
    return text


class JobPageFetcher:
    def __init__(
        self,
        settings: Settings,
        *,
        resolver: Resolver = socket.getaddrinfo,
        client: httpx.Client | None = None,
    ):
        self.settings = settings
        self.resolver = resolver
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(settings.job_fetch_timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "JobPilot/1.0 (+public-job-preview)"},
        )

    def fetch(self, url: str) -> tuple[str, str]:
        started_at = perf_counter()
        current = validate_public_job_url(url, self.resolver)
        try:
            for redirect_count in range(self.settings.job_fetch_max_redirects + 1):
                with self.client.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location or redirect_count >= self.settings.job_fetch_max_redirects:
                            raise JobIngestionError("The job page redirected too many times.")
                        current = validate_public_job_url(urljoin(current, location), self.resolver)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if content_type and not content_type.startswith(("text/html", "text/plain")):
                        raise JobIngestionError("The job page returned an unsupported format.")
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.settings.job_fetch_max_bytes:
                        raise JobIngestionError("The job page is too large to read safely.")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.settings.job_fetch_max_bytes:
                            raise JobIngestionError("The job page is too large to read safely.")
                        chunks.append(chunk)
                    encoding = response.encoding or "utf-8"
                    body = b"".join(chunks).decode(encoding, errors="replace")
                    text = extract_readable_job_text(body, content_type)
                    logger.info(
                        "Job URL fetch completed elapsed_seconds=%.3f bytes=%s status=success",
                        perf_counter() - started_at,
                        size,
                    )
                    return current, text
            raise JobIngestionError("The job page redirected too many times.")
        except UnsafeJobUrlError:
            raise
        except JobIngestionError:
            raise
        except (httpx.HTTPError, UnicodeError, ValueError) as exc:
            logger.info(
                "Job URL fetch failed elapsed_seconds=%.3f exception_type=%s status=error",
                perf_counter() - started_at,
                type(exc).__name__,
            )
            raise JobIngestionError("The job page could not be read.") from exc
