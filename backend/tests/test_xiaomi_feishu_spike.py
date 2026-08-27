import json

import httpx
import pytest

from scripts.spike_xiaomi_feishu_recruitment import (
    api_headers,
    parse_public_api_response,
    parse_website_info,
)


def test_parses_public_tenant_and_website_metadata() -> None:
    html = (
        '<script id="js-websiteInfo" type="text/json">'
        '{"tenant_info":{"tenant_name":"小米科技","tenant_id_md5":"tenant-hash"},'
        '"website_info":{"id":"website-1","path":"index"}}'
        "</script>"
    )
    parsed = parse_website_info(html)
    assert parsed["tenant_info"]["tenant_name"] == "小米科技"
    assert parsed["website_info"]["path"] == "index"
    with pytest.raises(ValueError):
        parse_website_info("<html></html>")


def test_api_headers_and_json_contract_are_deterministic() -> None:
    headers = api_headers("index")
    assert headers["website-path"] == "index"
    assert headers["Portal-Channel"] == "saas-career"
    assert headers["Portal-Platform"] == "pc"
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=json.dumps({"data": {"count": 1, "job_post_list": [{"id": "123"}]}}),
    )
    assert parse_public_api_response(response)["data"]["count"] == 1


def test_rejects_html_misdirection_and_oversized_response() -> None:
    html = httpx.Response(200, headers={"content-type": "text/html"}, text="<html />")
    with pytest.raises(ValueError, match="Expected JSON"):
        parse_public_api_response(html)
    oversized = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=b"x" * (5 * 1024 * 1024 + 1),
    )
    with pytest.raises(ValueError, match="size limit"):
        parse_public_api_response(oversized)
