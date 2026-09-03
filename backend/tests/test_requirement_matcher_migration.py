"""Production matcher migration: Claude + Prompt A -> qwen3.8-max + Prompt C.

These tests pin the migration contract without running a live model benchmark.
The DashScope transport is mocked; the frozen evaluation (dataset_v2 held-out)
is the source of truth for model/prompt selection and is not re-litigated here.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.schemas.fit_analysis import FitAnalysisOutput
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient
from app.services.matcher_client import (
    AnthropicMatcherClient,
    QwenMatcherClient,
    active_matcher_model,
    build_matcher_client,
)
from app.services.requirement_matcher import PROMPT_C_INSTRUCTIONS, RequirementMatcher

FROZEN_PROMPT_C = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "prompt_refinement_round2b"
    / "prompt_refinement_treatment_instructions.txt"
)


def qwen_settings(**overrides) -> Settings:
    base = {
        "matcher_provider": "qwen",
        "matcher_model": "qwen3.8-max",
        "dashscope_api_key": "test-key-not-real",
        "qwen_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    base.update(overrides)
    return Settings(**base)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("error", request=Mock(), response=self)


def content_response(obj: dict) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "choices": [{"message": {"content": json.dumps(obj, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        },
    )


SECTION_D = {
    "summary": "候选人整体具备相关经历。",
    "requirement_matches": [
        {
            "requirement_id": "reqv2_a",
            "match_label": "Strong",
            "evidence_ids": ["resume_extracted:1"],
            "reason": "项目经历直接匹配。",
        },
        {
            "requirement_id": "reqv2_b",
            "match_label": "Missing",
            "evidence_ids": [],
            "reason": "暂无相关证据。",
        },
    ],
    "suggested_preparation": [
        {
            "title": "补充数据分析经历",
            "action": "整理一段可核验的分析项目。",
            "priority": "High",
            "requirement_ids": ["reqv2_b"],
        }
    ],
}

IMPORTANCE_BY_ID = {"reqv2_a": "Critical", "reqv2_b": "Preferred"}


# --- factory / provider selection -------------------------------------------
def test_factory_selects_qwen_when_provider_is_qwen():
    client = build_matcher_client(qwen_settings())
    assert isinstance(client, QwenMatcherClient)
    assert client.model == "qwen3.8-max"


def test_factory_selects_anthropic_otherwise():
    client = build_matcher_client(Settings(matcher_provider="anthropic"))
    assert isinstance(client, AnthropicMatcherClient)


def test_active_matcher_model_tracks_provider():
    assert active_matcher_model(qwen_settings()) == "qwen3.8-max"
    assert (
        active_matcher_model(Settings(matcher_provider="anthropic"))
        == Settings().claude_model
    )
    # The migration must make an old Claude + Prompt-A analysis stale.
    assert active_matcher_model(qwen_settings()) != Settings().claude_model


# --- frozen prompt ---------------------------------------------------------
def test_prompt_version_is_the_rubric_refined_finalist():
    assert RequirementMatcher.PROMPT_VERSION == "job-fit-v3-rubric-refined-v2"
    assert RequirementMatcher.SCHEMA_VERSION == "fit-analysis-wire-v2"


def test_embedded_prompt_c_matches_frozen_artifact_byte_for_byte():
    assert PROMPT_C_INSTRUCTIONS == FROZEN_PROMPT_C.read_text().rstrip("\n")
    # Rubric-refined v2 calibration clarifications are present...
    assert "ADJUDICATION RULES (rubric-refined v2" in PROMPT_C_INSTRUCTIONS
    assert "TECHNOLOGY ADJACENCY" in PROMPT_C_INSTRUCTIONS
    # ...and the removed rules stay removed.
    assert "OR-list" in PROMPT_C_INSTRUCTIONS  # only as an explicit exclusion note
    assert "weakest-subclaim" not in PROMPT_C_INSTRUCTIONS


# --- Qwen request shape ---------------------------------------------------
def test_qwen_request_is_deterministic_and_non_thinking(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        return content_response(SECTION_D)

    monkeypatch.setattr("app.services.matcher_client.httpx.post", fake_post)
    client = QwenMatcherClient(qwen_settings())
    client.generate_fit_analysis(
        prompt="INSTRUCTIONS\n\nJOB REQUIREMENTS:\n[]\n\nELIGIBLE CANDIDATE EVIDENCE:\n[]\n",
        importance_by_requirement_id=IMPORTANCE_BY_ID,
        tool_name="submit_requirement_matches",
    )
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-key-not-real"
    body = captured["body"]
    assert body["model"] == "qwen3.8-max"
    assert body["temperature"] == 0
    assert body["enable_thinking"] is False
    assert body["response_format"] == {"type": "json_object"}
    assert "Return the response as JSON." in body["messages"][0]["content"]


# --- 4-field -> 7-field mapping -----------------------------------------
def test_section_d_maps_onto_production_fit_analysis_output(monkeypatch):
    monkeypatch.setattr(
        "app.services.matcher_client.httpx.post",
        lambda *a, **k: content_response(SECTION_D),
    )
    client = QwenMatcherClient(qwen_settings())
    out = client.generate_fit_analysis(
        prompt="p",
        importance_by_requirement_id=IMPORTANCE_BY_ID,
        tool_name="submit_requirement_matches",
    )
    assert isinstance(out, FitAnalysisOutput)
    by_id = {m.requirement_id: m for m in out.requirement_matches}
    strong = by_id["reqv2_a"]
    assert strong.match_status == "Strong"
    assert strong.importance == "Critical"  # from importance_hint inverse map
    assert strong.is_hard_requirement is False
    assert strong.hard_requirement_category == "none"
    assert strong.confidence == "Medium"
    assert strong.evidence_source_ids == ["resume_extracted:1"]
    missing = by_id["reqv2_b"]
    assert missing.match_status == "Missing"
    assert missing.evidence_source_ids == []
    assert out.suggested_preparation[0].priority == "High"


def test_malformed_match_label_is_rejected_not_silently_passed(monkeypatch):
    bad = json.loads(json.dumps(SECTION_D))
    bad["requirement_matches"][0]["match_label"] = "PROBABLY"
    monkeypatch.setattr(
        "app.services.matcher_client.httpx.post",
        lambda *a, **k: content_response(bad),
    )
    client = QwenMatcherClient(qwen_settings())
    with pytest.raises(ClaudeServiceError) as exc:
        client.generate_fit_analysis(
            prompt="p",
            importance_by_requirement_id=IMPORTANCE_BY_ID,
            tool_name="t",
        )
    assert exc.value.code == "JOB_CONTENT_UNPARSEABLE"


def test_non_list_evidence_ids_is_rejected(monkeypatch):
    bad = json.loads(json.dumps(SECTION_D))
    bad["requirement_matches"][0]["evidence_ids"] = "resume_extracted:1"
    monkeypatch.setattr(
        "app.services.matcher_client.httpx.post",
        lambda *a, **k: content_response(bad),
    )
    client = QwenMatcherClient(qwen_settings())
    with pytest.raises(ClaudeServiceError):
        client.generate_fit_analysis(
            prompt="p", importance_by_requirement_id=IMPORTANCE_BY_ID, tool_name="t"
        )


def test_non_json_content_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.services.matcher_client.httpx.post",
        lambda *a, **k: FakeResponse(
            200, {"choices": [{"message": {"content": "not json at all"}}]}
        ),
    )
    client = QwenMatcherClient(qwen_settings())
    with pytest.raises(ClaudeServiceError) as exc:
        client.generate_fit_analysis(
            prompt="p", importance_by_requirement_id={}, tool_name="t"
        )
    assert exc.value.code == "JOB_CONTENT_UNPARSEABLE"


# --- retry policy: transient only, bounded --------------------------------
def test_transient_429_is_retried_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky_post(*a, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            return FakeResponse(429, text="rate limited")
        return content_response(SECTION_D)

    monkeypatch.setattr("app.services.matcher_client.httpx.post", flaky_post)
    monkeypatch.setattr("app.services.matcher_client.time.sleep", lambda *_: None)
    client = QwenMatcherClient(qwen_settings())
    out = client.generate_fit_analysis(
        prompt="p", importance_by_requirement_id=IMPORTANCE_BY_ID, tool_name="t"
    )
    assert isinstance(out, FitAnalysisOutput)
    assert calls["n"] == 3


def test_persistent_transient_failure_is_bounded(monkeypatch):
    calls = {"n": 0}

    def always_429(*a, **k):
        calls["n"] += 1
        return FakeResponse(429, text="rate limited")

    monkeypatch.setattr("app.services.matcher_client.httpx.post", always_429)
    monkeypatch.setattr("app.services.matcher_client.time.sleep", lambda *_: None)
    client = QwenMatcherClient(qwen_settings())
    with pytest.raises(ClaudeServiceError) as exc:
        client.generate_fit_analysis(
            prompt="p", importance_by_requirement_id=IMPORTANCE_BY_ID, tool_name="t"
        )
    assert exc.value.code == "AI_SERVICE_UNAVAILABLE"
    assert calls["n"] == 3  # 1 + 2 retries, no unbounded loop


def test_missing_api_key_is_a_clear_configuration_error(monkeypatch):
    monkeypatch.setattr(
        "app.services.matcher_client.httpx.post",
        lambda *a, **k: pytest.fail("must not call provider without a key"),
    )
    client = QwenMatcherClient(qwen_settings(dashscope_api_key=""))
    with pytest.raises(ClaudeServiceError) as exc:
        client.generate_fit_analysis(
            prompt="p", importance_by_requirement_id={}, tool_name="t"
        )
    assert exc.value.code == "AI_REQUEST_INVALID"


def test_provider_error_text_is_redacted_before_logging(monkeypatch, caplog):
    leaky = "invalid api-key: sk-abcdef123456 authorization: Bearer sk-zzz"

    def rejecting_post(*a, **k):
        return FakeResponse(400, text=leaky)

    monkeypatch.setattr("app.services.matcher_client.httpx.post", rejecting_post)
    client = QwenMatcherClient(qwen_settings())
    with caplog.at_level("WARNING"), pytest.raises(ClaudeServiceError):
        client.generate_fit_analysis(
            prompt="p", importance_by_requirement_id={}, tool_name="t"
        )
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "sk-abcdef123456" not in joined
    assert "sk-zzz" not in joined


# --- other services stay Claude-backed ---------------------------------
def test_other_llm_services_are_not_touched_by_the_migration():
    from app.routes.jobs import get_job_parser
    from app.routes.profile import get_resume_parser
    from app.routes.resume_tailoring import get_rewriter, get_semantic_validator

    assert isinstance(get_job_parser().client, ClaudeStructuredClient)
    assert isinstance(get_resume_parser().client, ClaudeStructuredClient)
    assert isinstance(get_rewriter().client, ClaudeStructuredClient)
    validator = get_semantic_validator()
    assert validator.client is None or isinstance(
        validator.client, ClaudeStructuredClient
    )


def test_anthropic_matcher_client_delegates_to_claude_structured_client():
    fake = Mock()
    fake.model = "claude-sonnet-4-5-20250929"
    fake.generate.return_value = FitAnalysisOutput(
        summary="s", requirement_matches=[], suggested_preparation=[]
    )
    client = AnthropicMatcherClient(fake)
    assert client.model == "claude-sonnet-4-5-20250929"
    client.generate_fit_analysis(
        prompt="p", importance_by_requirement_id={"x": "Critical"}, tool_name="t"
    )
    # importance map is ignored for Claude (native structured output asks for it)
    assert fake.generate.call_args.kwargs["output_model"] is FitAnalysisOutput
