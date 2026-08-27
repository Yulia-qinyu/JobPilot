"""Anonymous HTTP-only feasibility spike for Xiaomi's Feishu Recruitment portal.

This is a developer diagnostic, not a registered JobSourceAdapter. It never logs in,
submits an application, executes browser JavaScript, or bypasses risk controls.
"""

import argparse
import json
import re
from time import perf_counter
from typing import Any

import httpx

BASE_URL = "https://xiaomi.jobs.f.mioffice.cn"
CAREERS_PATH = "/index/"
PORTAL_TYPE = 6  # Feishu ATSX SaasCareer, verified from the public frontend bundle.
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
WEBSITE_INFO_PATTERN = re.compile(
    r'<script\s+id="js-websiteInfo"\s+type="text/json">(.*?)</script>', re.DOTALL
)


def parse_website_info(html: str) -> dict[str, Any]:
    match = WEBSITE_INFO_PATTERN.search(html)
    if not match:
        raise ValueError("Public careers page did not expose js-websiteInfo.")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise TypeError("js-websiteInfo was not an object.")
    return payload


def parse_public_api_response(response: httpx.Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "").lower()
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ValueError("Response exceeded the spike size limit.")
    if "application/json" not in content_type:
        raise ValueError(f"Expected JSON but received {content_type or 'unknown content type'}.")
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError("API response was not an object.")
    return payload


def api_headers(website_path: str) -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": f"{BASE_URL}/{website_path}/",
        "Origin": BASE_URL,
        "Portal-Channel": "saas-career",
        "Portal-Platform": "pc",
        "X-Requested-With": "XMLHttpRequest",
        "website-path": website_path,
    }


def _timed_get(client: httpx.Client, path: str, **kwargs) -> tuple[httpx.Response, float]:
    started = perf_counter()
    response = client.get(path, **kwargs)
    return response, round(perf_counter() - started, 3)


def _summary(response: httpx.Response, duration: float) -> dict[str, Any]:
    return {
        "request_url": str(response.request.url),
        "method": response.request.method,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "response_bytes": len(response.content),
        "duration_seconds": duration,
    }


def _find_beijing_code(filters: dict[str, Any]) -> str | None:
    cities = filters.get("data", {}).get("city_list", [])

    def walk(items: list[dict[str, Any]]) -> str | None:
        for item in items:
            name = item.get("name")
            labels = name.values() if isinstance(name, dict) else [name]
            if any("北京" in str(label) for label in labels if label):
                return str(item.get("code") or item.get("id") or "") or None
            child = walk(item.get("children") or [])
            if child:
                return child
        return None

    return walk(cities)


def run_spike(keyword: str = "AI 产品经理") -> dict[str, Any]:
    report: dict[str, Any] = {
        "target": "Xiaomi Feishu Recruitment / mioffice ATSX",
        "safety": {
            "anonymous_only": True,
            "browser_automation": False,
            "login": False,
            "application_endpoints": False,
        },
        "public_frontend_contract": {
            "portal_type": PORTAL_TYPE,
            "signed_endpoints": [
                "/api/v1/search/job/posts",
                "/api/v1/job/posts/{id}",
                "/api/v1/config/job/filters/{portal_type}",
            ],
            "signature_parameter": "_signature",
            "signature_generated_by_public_frontend_bundle": True,
            "signature_generation_attempted": False,
            "reason": "The spike does not reproduce or bypass frontend anti-automation signing.",
        },
    }
    with httpx.Client(
        base_url=BASE_URL,
        timeout=httpx.Timeout(20.0),
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "JobPilot-Feishu-HTTP-Contract-Spike/1.0"},
    ) as client:
        homepage, duration = _timed_get(client, CAREERS_PATH)
        report["homepage"] = _summary(homepage, duration)
        info = parse_website_info(homepage.text)
        tenant = info.get("tenant_info", {})
        website = info.get("website_info", {})
        website_path = str(website.get("path") or "index")
        report["portal"] = {
            "tenant_name": tenant.get("tenant_name"),
            "tenant_id_md5": tenant.get("tenant_id_md5"),
            "website_id": website.get("id"),
            "website_path": website_path,
            "portal_type": PORTAL_TYPE,
            "homepage_set_cookie_count": len(client.cookies),
        }
        headers = api_headers(website_path)
        filters_response, duration = _timed_get(
            client, f"/api/v1/config/job/filters/{PORTAL_TYPE}", headers=headers
        )
        report["filters"] = _summary(filters_response, duration)
        try:
            filters = parse_public_api_response(filters_response)
            report["filters"]["json_contract"] = True
            beijing_code = _find_beijing_code(filters)
        except (ValueError, json.JSONDecodeError) as exc:
            filters = {}
            beijing_code = None
            report["filters"].update(json_contract=False, contract_error=str(exc))

        params: dict[str, Any] = {
            "portal_type": PORTAL_TYPE,
            "keyword": keyword,
            "limit": 10,
            "offset": 0,
        }
        if beijing_code:
            params["location_code_list"] = beijing_code
        search_response, duration = _timed_get(
            client, "/api/v1/search/job/posts", headers=headers, params=params
        )
        report["search"] = _summary(search_response, duration)
        report["search"]["beijing_location_code"] = beijing_code
        try:
            search = parse_public_api_response(search_response)
            data = search.get("data") or {}
            jobs = data.get("job_post_list") or []
            report["search"].update(
                json_contract=True,
                result_count=data.get("count"),
                returned_count=len(jobs),
                pagination={"limit": 10, "offset": 0},
            )
            first = jobs[0] if jobs else None
            external_id = first.get("id") if isinstance(first, dict) else None
            report["search"]["sample_external_job_id"] = external_id
        except (ValueError, json.JSONDecodeError) as exc:
            external_id = None
            report["search"].update(json_contract=False, contract_error=str(exc))

        if external_id:
            detail_response, duration = _timed_get(
                client,
                f"/api/v1/job/posts/{external_id}",
                headers=headers,
                params={
                    "portal_type": PORTAL_TYPE,
                    "source_job_post_id": external_id,
                    "with_recommend": "false",
                },
            )
            report["detail"] = _summary(detail_response, duration)
            try:
                detail = parse_public_api_response(detail_response)
                report["detail"]["json_contract"] = bool(
                    (detail.get("data") or {}).get("job_post_detail")
                )
            except (ValueError, json.JSONDecodeError) as exc:
                report["detail"].update(json_contract=False, contract_error=str(exc))
        else:
            report["detail"] = {"attempted": False, "reason": "No trusted job ID returned."}

    contract_ok = bool(
        report["filters"].get("json_contract")
        and report["search"].get("json_contract")
        and report["detail"].get("json_contract")
    )
    report["feasibility"] = (
        "A_RECOMMENDED" if contract_ok else "C_NOT_RECOMMENDED_UNTIL_HTTP_CONTRACT_IS_STABLE"
    )
    report["captcha_or_anti_bot"] = (
        "No CAPTCHA was bypassed. Public HTML loaded anonymously; JSON API routing did not "
        "return the expected contract in this run." if not contract_ok else
        "No CAPTCHA observed for anonymous listing/detail requests."
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyword", default="AI 产品经理")
    args = parser.parse_args()
    report = run_spike(args.keyword)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["feasibility"] == "A_RECOMMENDED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
