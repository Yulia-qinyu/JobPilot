import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from anthropic import BadRequestError, transform_schema
from pydantic import ValidationError

from app.config import Settings
from app.schemas.analysis import JDRequirementsOutput, MatchAnalysis, ResumeProfile
from app.schemas.fit_analysis import FitAnalysisOutput
from app.schemas.resume_tailoring import SemanticValidationOutput, TailoredDraftOutput
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient


def make_client() -> tuple[ClaudeStructuredClient, Mock]:
    structured_client = ClaudeStructuredClient(
        Settings(anthropic_api_key="test-key", claude_model="test-model")
    )
    sdk_client = Mock()
    structured_client.client = sdk_client
    return structured_client, sdk_client


def test_generate_uses_messages_parse_and_returns_parsed_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, sdk_client = make_client()
    expected = MatchAnalysis(match_score=72, recommendation="Apply")
    sdk_client.messages.parse.return_value = SimpleNamespace(
        parsed_output=expected,
        content=[SimpleNamespace(type="text")],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=123, output_tokens=45),
    )

    with caplog.at_level(logging.INFO):
        result = client.generate(
            prompt="fictional input", output_model=MatchAnalysis, tool_name="submit_match_analysis"
        )

    assert result is expected
    sdk_client.messages.parse.assert_called_once_with(
        model="test-model",
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": "fictional input"}],
        output_format=MatchAnalysis,
    )
    sdk_client.messages.create.assert_not_called()
    assert "input_tokens=123" in caplog.text
    assert "output_tokens=45" in caplog.text
    assert "fictional input" not in caplog.text


def test_generate_does_not_treat_content_block_as_parsed_output() -> None:
    client, sdk_client = make_client()
    sdk_client.messages.parse.return_value = SimpleNamespace(
        parsed_output=None,
        content=[SimpleNamespace(type="text")],
        stop_reason="max_tokens",
    )

    with pytest.raises(ClaudeServiceError, match="did not return structured output"):
        client.generate(
            prompt="fictional input", output_model=ResumeProfile, tool_name="submit_resume_profile"
        )


def test_validation_log_contains_schema_path_but_not_prompt(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, sdk_client = make_client()
    try:
        MatchAnalysis.model_validate({"match_score": 50, "recommendation": "Maybe"})
    except ValidationError as validation_error:
        sdk_client.messages.parse.side_effect = validation_error

    with caplog.at_level("WARNING"), pytest.raises(ClaudeServiceError, match="unexpected format"):
        client.generate(
            prompt="fictional sensitive input",
            output_model=MatchAnalysis,
            tool_name="submit_match_analysis",
        )

    assert "recommendation" in caplog.text
    assert "literal_error" in caplog.text
    assert "fictional sensitive input" not in caplog.text


def test_phase_2_jd_wire_schema_is_low_complexity_and_strict() -> None:
    schema = transform_schema(JDRequirementsOutput)
    serialized = json.dumps(schema)
    assert "anyOf" not in serialized
    assert set(schema["required"]) == set(schema["properties"])
    nested = schema["$defs"]["JDKeyRequirementOutput"]
    assert set(nested["required"]) == set(nested["properties"])
    assert nested["additionalProperties"] is False


def test_phase_3_fit_wire_schema_is_low_complexity_and_strict() -> None:
    schema = transform_schema(FitAnalysisOutput)
    serialized = json.dumps(schema)
    assert "anyOf" not in serialized
    assert set(schema["required"]) == set(schema["properties"])
    for definition in schema["$defs"].values():
        assert set(definition["required"]) == set(definition["properties"])
        assert definition["additionalProperties"] is False


@pytest.mark.parametrize("output_model", [TailoredDraftOutput, SemanticValidationOutput])
def test_phase_6_wire_schemas_are_low_complexity_and_strict(output_model) -> None:
    schema = transform_schema(output_model)
    serialized = json.dumps(schema)
    assert "anyOf" not in serialized
    assert set(schema["required"]) == set(schema["properties"])
    for definition in schema["$defs"].values():
        assert set(definition["required"]) == set(definition["properties"])
        assert definition["additionalProperties"] is False


def test_bad_request_is_logged_safely_and_not_retried(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, sdk_client = make_client()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(400, request=request, headers={"request-id": "req_safe_test"})
    sdk_client.messages.parse.side_effect = BadRequestError(
        "Request rejected",
        response=response,
        body={
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "Schema is too complex.",
            },
        },
    )

    with caplog.at_level(logging.WARNING), pytest.raises(ClaudeServiceError) as captured:
        client.generate(
            prompt="高度敏感的虚构 JD 内容不应出现在日志中",
            output_model=JDRequirementsOutput,
            tool_name="submit_jd_requirements",
        )

    assert captured.value.code == "AI_REQUEST_INVALID"
    assert sdk_client.messages.parse.call_count == 1
    assert "exception_type=BadRequestError" in caplog.text
    assert "status_code=400" in caplog.text
    assert "anthropic_error_type=invalid_request_error" in caplog.text
    assert "sanitized_message=Schema is too complex." in caplog.text
    assert "output_model=JDRequirementsOutput" in caplog.text
    assert "高度敏感" not in caplog.text
