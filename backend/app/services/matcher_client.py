"""Requirement-matcher transport clients.

The Job Analysis requirement matcher is the one JobPilot LLM step whose model was
selected by a frozen evaluation (qwen3.8-max + job-fit-v3-rubric-refined-v2, with
kimi-k3 + the control prompt as fallback). Every other LLM service keeps using
``ClaudeStructuredClient`` directly; only this matcher needs a provider-aware
transport, so the abstraction lives here and stays matcher-specific.

``QwenMatcherClient`` talks to Alibaba DashScope through its OpenAI-compatible
endpoint. DashScope returns the frozen Section D 4-field contract
(``requirement_id`` / ``match_label`` / ``evidence_ids`` / ``reason`` per match);
this module maps that deterministically onto the production 7-field
``RequirementMatchOutput`` before it reaches the unchanged
``FitAnalysisService._normalize_matches`` / ``MatchScoreService.score`` pipeline.
"""

from __future__ import annotations

import json
import logging
import re
import time
from time import perf_counter
from typing import Protocol, runtime_checkable

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas.fit_analysis import (
    FitAnalysisOutput,
    PreparationOutput,
    RequirementMatchOutput,
)
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient

logger = logging.getLogger(__name__)

# Deterministic importance fill for the Qwen path. The frozen Section D contract
# does not carry an importance field; production importance is the canonical
# requirement importance, which RequirementCatalog exposes only as the
# high/medium/low ``importance_hint``. This inverse map is the same one used in
# the frozen T5 transport normalization.
IMPORTANCE_FROM_HINT: dict[str, str] = {
    "high": "Critical",
    "medium": "Important",
    "low": "Preferred",
}
VALID_MATCH_LABELS: frozenset[str] = frozenset({"Strong", "Partial", "Missing"})

# Qwen-only tail appended after the frozen instruction block and the JOB
# REQUIREMENTS / ELIGIBLE CANDIDATE EVIDENCE payloads. The Anthropic path uses
# native structured outputs and needs no JSON-shape description.
SECTION_D_CONTRACT = """
OUTPUT FORMAT (return a single JSON object, no prose outside it):
{
  "summary": "<Simplified Chinese overview>",
  "requirement_matches": [
    {
      "requirement_id": "<one of the supplied requirement_id values>",
      "match_label": "Strong | Partial | Missing",
      "evidence_ids": ["<exact evidence_source_id values; empty list for Missing>"],
      "reason": "<concise Simplified Chinese explanation>"
    }
  ],
  "suggested_preparation": [
    {
      "title": "<short Simplified Chinese title>",
      "action": "<concrete Simplified Chinese action>",
      "priority": "High | Medium | Low",
      "requirement_ids": ["<related requirement_id values>"]
    }
  ]
}
Return exactly one requirement_matches entry for every supplied requirement_id,
with no duplicates and no unknown IDs.

Return the response as JSON.
"""

_SECRET_RE = re.compile(
    r"(?i)(dashscope[-_ ]?api[-_ ]?key|api[-_ ]?key|authorization|bearer)"
    r"\s*[:=]?\s*(?:bearer\s+)?[^\s,;\"']+"
)
_TRANSIENT_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def _redact(text: str) -> str:
    return _SECRET_RE.sub(r"\1=<redacted>", text or "")


@runtime_checkable
class StructuredMatcherClient(Protocol):
    """Transport contract the RequirementMatcher depends on."""

    model: str

    def generate_fit_analysis(
        self,
        *,
        prompt: str,
        importance_by_requirement_id: dict[str, str],
        tool_name: str,
    ) -> FitAnalysisOutput: ...


class AnthropicMatcherClient:
    """Fallback / legacy path. Delegates to the shared Claude structured client.

    Claude is asked for the full 7-field match object via native structured
    outputs exactly as before, so ``importance_by_requirement_id`` is unused here.
    """

    def __init__(self, client: ClaudeStructuredClient):
        self._client = client

    @property
    def model(self) -> str:
        return self._client.model

    @property
    def last_call_metrics(self) -> dict[str, object]:
        return self._client.last_call_metrics

    def generate_fit_analysis(
        self,
        *,
        prompt: str,
        importance_by_requirement_id: dict[str, str],
        tool_name: str,
    ) -> FitAnalysisOutput:
        return self._client.generate(
            prompt=prompt,
            output_model=FitAnalysisOutput,
            tool_name=tool_name,
        )


class QwenMatcherClient:
    """DashScope (OpenAI-compatible) transport for the frozen matcher finalist."""

    def __init__(
        self,
        settings: Settings,
        *,
        max_retries: int = 2,
        timeout_seconds: float = 60.0,
    ):
        self.model = settings.matcher_model
        self._base_url = settings.qwen_base_url.rstrip("/")
        self._api_key = settings.dashscope_api_key
        self._max_retries = max_retries
        self._timeout = timeout_seconds
        self.last_call_metrics: dict[str, object] = {}

    def generate_fit_analysis(
        self,
        *,
        prompt: str,
        importance_by_requirement_id: dict[str, str],
        tool_name: str,
    ) -> FitAnalysisOutput:
        if not self._api_key:
            raise ClaudeServiceError(
                "DASHSCOPE_API_KEY is not configured. Add it to .env to use the "
                "qwen matcher provider.",
                code="AI_REQUEST_INVALID",
            )
        body = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": f"{prompt}\n{SECTION_D_CONTRACT}"}
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            # DashScope reads this top-level flag (OpenAI SDK sends it via
            # extra_body); qwen3 commercial models must not emit a thinking trace
            # for a deterministic structured call.
            "enable_thinking": False,
        }
        content = self._post_with_retry(body, tool_name)
        return self._map_to_fit_analysis(
            content, importance_by_requirement_id, tool_name
        )

    # -- transport -----------------------------------------------------------
    def _post_with_retry(self, body: dict, tool_name: str) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        started_at = perf_counter()
        attempt = 0
        while True:
            try:
                response = httpx.post(
                    url, headers=headers, json=body, timeout=self._timeout
                )
                if response.status_code in _TRANSIENT_STATUS:
                    raise _TransientMatcherError(
                        f"HTTP {response.status_code}", retryable=True
                    )
                response.raise_for_status()
                data = response.json()
                message = data["choices"][0]["message"]["content"]
                usage = data.get("usage") or {}
                elapsed = perf_counter() - started_at
                self.last_call_metrics = {
                    "model": self.model,
                    "elapsed_seconds": round(elapsed, 4),
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                }
                logger.info(
                    "Matcher stage completed stage=%s provider=qwen model=%s "
                    "elapsed_seconds=%.3f input_tokens=%s output_tokens=%s "
                    "retries=%s status=success",
                    tool_name,
                    self.model,
                    elapsed,
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                    attempt,
                )
                if not isinstance(message, str) or not message.strip():
                    raise ClaudeServiceError(
                        "Qwen returned an empty matcher response.",
                        code="JOB_CONTENT_UNPARSEABLE",
                    )
                return message
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt >= self._max_retries:
                    logger.warning(
                        "Matcher transport failed stage=%s provider=qwen model=%s "
                        "exception_type=%s retries=%s",
                        tool_name,
                        self.model,
                        type(exc).__name__,
                        attempt,
                    )
                    raise ClaudeServiceError(
                        "The matcher service is temporarily unavailable.",
                        code="AI_SERVICE_UNAVAILABLE",
                    ) from exc
            except _TransientMatcherError as exc:
                if attempt >= self._max_retries:
                    logger.warning(
                        "Matcher provider transient error stage=%s provider=qwen "
                        "model=%s detail=%s retries=%s",
                        tool_name,
                        self.model,
                        exc,
                        attempt,
                    )
                    raise ClaudeServiceError(
                        "The matcher service is temporarily unavailable.",
                        code="AI_SERVICE_UNAVAILABLE",
                    ) from exc
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "Matcher request rejected stage=%s provider=qwen model=%s "
                    "status_code=%s detail=%s",
                    tool_name,
                    self.model,
                    exc.response.status_code,
                    _redact(exc.response.text[:300]),
                )
                raise ClaudeServiceError(
                    "The matcher provider rejected the request.",
                    code="AI_REQUEST_INVALID",
                ) from exc
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Matcher response unparseable stage=%s provider=qwen model=%s "
                    "exception_type=%s",
                    tool_name,
                    self.model,
                    type(exc).__name__,
                )
                raise ClaudeServiceError(
                    "The matcher provider returned an unreadable response.",
                    code="JOB_CONTENT_UNPARSEABLE",
                ) from exc
            attempt += 1
            time.sleep(min(2.0 * attempt, 4.0))

    # -- 4-field -> 7-field mapping ----------------------------------------
    def _map_to_fit_analysis(
        self,
        raw_content: str,
        importance_by_requirement_id: dict[str, str],
        tool_name: str,
    ) -> FitAnalysisOutput:
        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ClaudeServiceError(
                "The matcher provider did not return valid JSON.",
                code="JOB_CONTENT_UNPARSEABLE",
            ) from exc
        if not isinstance(payload, dict):
            raise ClaudeServiceError(
                "The matcher provider returned a non-object JSON response.",
                code="JOB_CONTENT_UNPARSEABLE",
            )

        raw_matches = payload.get("requirement_matches")
        if not isinstance(raw_matches, list):
            raise ClaudeServiceError(
                "The matcher response is missing requirement_matches.",
                code="JOB_CONTENT_UNPARSEABLE",
            )

        matches: list[RequirementMatchOutput] = []
        for entry in raw_matches:
            if not isinstance(entry, dict):
                raise ClaudeServiceError(
                    "A requirement match entry was not an object.",
                    code="JOB_CONTENT_UNPARSEABLE",
                )
            requirement_id = entry.get("requirement_id")
            match_label = entry.get("match_label") or entry.get("match_status")
            evidence_ids = entry.get("evidence_ids")
            if evidence_ids is None:
                evidence_ids = entry.get("evidence_source_ids", [])
            reason = entry.get("reason", "")
            if not isinstance(requirement_id, str) or not requirement_id:
                raise ClaudeServiceError(
                    "A requirement match is missing a requirement_id.",
                    code="JOB_CONTENT_UNPARSEABLE",
                )
            if match_label not in VALID_MATCH_LABELS:
                raise ClaudeServiceError(
                    f"Unknown match label {match_label!r} in matcher response.",
                    code="JOB_CONTENT_UNPARSEABLE",
                )
            if not isinstance(evidence_ids, list) or not all(
                isinstance(item, str) for item in evidence_ids
            ):
                raise ClaudeServiceError(
                    "evidence_ids must be a list of strings.",
                    code="JOB_CONTENT_UNPARSEABLE",
                )
            importance = importance_by_requirement_id.get(requirement_id, "Important")
            matches.append(
                RequirementMatchOutput(
                    requirement_id=requirement_id,
                    importance=importance,
                    # v2_matchable requirements have already cleared the taxonomy
                    # boundary; they are never eligibility gates.
                    is_hard_requirement=False,
                    hard_requirement_category="none",
                    match_status=match_label,
                    reason=str(reason),
                    confidence="Medium",
                    evidence_source_ids=(
                        [] if match_label == "Missing" else list(evidence_ids)
                    ),
                )
            )

        preparation: list[PreparationOutput] = []
        for entry in payload.get("suggested_preparation") or []:
            if not isinstance(entry, dict):
                continue
            try:
                preparation.append(
                    PreparationOutput(
                        title=str(entry.get("title", "")).strip() or "准备建议",
                        action=str(entry.get("action", "")).strip()
                        or "补充相关经历证据。",
                        priority=entry.get("priority", "Medium"),
                        requirement_ids=[
                            item
                            for item in entry.get("requirement_ids", [])
                            if isinstance(item, str)
                        ],
                    )
                )
            except ValidationError:
                # A malformed preparation hint is non-fatal; the match set is
                # what feeds the score.
                continue

        try:
            return FitAnalysisOutput(
                summary=str(payload.get("summary", "")).strip()
                or "已完成岗位要求与经历证据匹配。",
                requirement_matches=matches,
                suggested_preparation=preparation,
            )
        except ValidationError as exc:
            logger.warning(
                "Matcher output failed schema validation stage=%s provider=qwen "
                "model=%s errors=%s",
                tool_name,
                self.model,
                [
                    {"location": [str(p) for p in err["loc"]], "type": err["type"]}
                    for err in exc.errors(include_input=False, include_url=False)
                ],
            )
            raise ClaudeServiceError(
                "The matcher provider returned data in an unexpected format.",
                code="JOB_CONTENT_UNPARSEABLE",
            ) from exc


class _TransientMatcherError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


def build_matcher_client(settings: Settings) -> StructuredMatcherClient:
    """Select the matcher transport from settings.matcher_provider."""

    if settings.matcher_provider == "qwen":
        return QwenMatcherClient(settings)
    return AnthropicMatcherClient(ClaudeStructuredClient(settings))


def active_matcher_model(settings: Settings) -> str:
    """The model id the configured matcher provider will actually use.

    Staleness checks compare a stored analysis against this rather than against
    ``settings.claude_model``, so a Claude + Prompt-A analysis is correctly
    flagged stale once the matcher is switched to qwen + Prompt C.
    """

    if settings.matcher_provider == "qwen":
        return settings.matcher_model
    return settings.claude_model
