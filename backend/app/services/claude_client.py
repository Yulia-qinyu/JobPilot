import logging
import re
from time import perf_counter
from typing import TypeVar

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
)
from pydantic import BaseModel, ValidationError

from app.config import Settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class ClaudeServiceError(RuntimeError):
    def __init__(self, message: str, *, code: str = "AI_SERVICE_UNAVAILABLE"):
        super().__init__(message)
        self.code = code


def sanitized_anthropic_error(exc: APIStatusError) -> tuple[str | None, str | None, str]:
    body = exc.body if isinstance(exc.body, dict) else {}
    error = body.get("error") if isinstance(body.get("error"), dict) else body
    error_type = error.get("type") if isinstance(error, dict) else None
    error_code = error.get("code") if isinstance(error, dict) else None
    raw_message = error.get("message") if isinstance(error, dict) else None
    message = " ".join(str(raw_message or "Anthropic rejected the request.").split())
    message = re.sub(
        r"(?i)(api[-_ ]?key|authorization|bearer)\s*[:=]?\s*[^\s,;]+",
        r"\1=<redacted>",
        message,
    )
    return (
        str(error_type) if error_type is not None else None,
        str(error_code) if error_code is not None else None,
        message[:300],
    )


class ClaudeStructuredClient:
    def __init__(self, settings: Settings):
        self.api_key = settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None
        self.model = settings.claude_model
        self.last_call_metrics: dict[str, object] = {}

    def generate(self, *, prompt: str, output_model: type[T], tool_name: str) -> T:
        if self.client is None:
            raise ClaudeServiceError(
                "ANTHROPIC_API_KEY is not configured. Copy .env.example to .env and add your key.",
                code="AI_REQUEST_INVALID",
            )
        started_at = perf_counter()
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=4096,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
                output_format=output_model,
            )
            parsed_output = response.parsed_output
            if parsed_output is None:
                logger.warning(
                    "Claude returned no parsed output stage=%s model=%s stop_reason=%s "
                    "content_types=%s",
                    tool_name,
                    self.model,
                    response.stop_reason,
                    [getattr(item, "type", "unknown") for item in response.content],
                )
                raise ClaudeServiceError(
                    "Claude did not return structured output.",
                    code="JOB_CONTENT_UNPARSEABLE",
                )
            usage = getattr(response, "usage", None)
            elapsed_seconds = perf_counter() - started_at
            self.last_call_metrics = {
                "model": self.model,
                "elapsed_seconds": round(elapsed_seconds, 4),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            }
            logger.info(
                "Claude stage completed stage=%s elapsed_seconds=%.3f model=%s "
                "input_tokens=%s output_tokens=%s status=success",
                tool_name,
                elapsed_seconds,
                self.model,
                getattr(usage, "input_tokens", None),
                getattr(usage, "output_tokens", None),
            )
            return parsed_output
        except ClaudeServiceError:
            raise
        except ValidationError as exc:
            logger.warning(
                "Claude structured output validation failed stage=%s model=%s output_model=%s "
                "elapsed_seconds=%.3f errors=%s",
                tool_name,
                self.model,
                output_model.__name__,
                perf_counter() - started_at,
                [
                    {
                        "location": [str(part) for part in error["loc"]],
                        "type": error["type"],
                    }
                    for error in exc.errors(include_input=False, include_url=False)
                ],
            )
            raise ClaudeServiceError(
                "Claude returned data in an unexpected format.",
                code="JOB_CONTENT_UNPARSEABLE",
            ) from exc
        except BadRequestError as exc:
            error_type, error_code, safe_message = sanitized_anthropic_error(exc)
            logger.warning(
                "Claude request rejected stage=%s elapsed_seconds=%.3f model=%s "
                "output_model=%s exception_type=%s status_code=%s anthropic_error_type=%s "
                "anthropic_error_code=%s request_id=%s sanitized_message=%s",
                tool_name,
                perf_counter() - started_at,
                self.model,
                output_model.__name__,
                type(exc).__name__,
                exc.status_code,
                error_type,
                error_code,
                getattr(exc, "request_id", None),
                safe_message,
            )
            raise ClaudeServiceError(
                "Claude rejected the structured-output request.",
                code="AI_REQUEST_INVALID",
            ) from exc
        except (APIConnectionError, APITimeoutError) as exc:
            logger.warning(
                "Claude service unavailable stage=%s elapsed_seconds=%.3f model=%s "
                "output_model=%s exception_type=%s",
                tool_name,
                perf_counter() - started_at,
                self.model,
                output_model.__name__,
                type(exc).__name__,
            )
            raise ClaudeServiceError(
                "Claude service is temporarily unavailable.",
                code="AI_SERVICE_UNAVAILABLE",
            ) from exc
        except APIStatusError as exc:
            error_type, error_code, safe_message = sanitized_anthropic_error(exc)
            logger.warning(
                "Claude API status error stage=%s elapsed_seconds=%.3f model=%s "
                "output_model=%s exception_type=%s status_code=%s anthropic_error_type=%s "
                "anthropic_error_code=%s request_id=%s sanitized_message=%s",
                tool_name,
                perf_counter() - started_at,
                self.model,
                output_model.__name__,
                type(exc).__name__,
                exc.status_code,
                error_type,
                error_code,
                getattr(exc, "request_id", None),
                safe_message,
            )
            raise ClaudeServiceError(
                "Claude service is temporarily unavailable.",
                code="AI_SERVICE_UNAVAILABLE",
            ) from exc
        except Exception as exc:
            logger.warning(
                "Claude API request failed stage=%s elapsed_seconds=%.3f model=%s "
                "output_model=%s exception_type=%s status_code=%s",
                tool_name,
                perf_counter() - started_at,
                self.model,
                output_model.__name__,
                type(exc).__name__,
                getattr(exc, "status_code", None),
            )
            raise ClaudeServiceError(
                "Claude API request failed. Please try again.",
                code="AI_SERVICE_UNAVAILABLE",
            ) from exc
