# Cross-Provider Credential Checklist (Round 1B)

**Do not print secret values. Do not modify or commit `.env`. Do not request `OPENAI_API_KEY`.**

## Environment audit performed (local only, values redacted)

| check | result |
|---|---|
| installed SDKs | `anthropic 0.125.0`, `httpx 0.28.1`, `pydantic 2.13.4`, `pydantic-settings` — **no** `google-genai` / `google-generativeai`, `dashscope`, `openai`, `deepseek`, `litellm`, `vertexai`, `boto3` |
| `requirements.txt` / `requirements-dev.txt` | Anthropic + httpx only among LLM/HTTP libs |
| env var NAME scan | `ANTHROPIC_API_KEY` (via `.env`), `ANTHROPIC_BASE_URL` (set) — no `GEMINI_*` / `GOOGLE_*` / `DASHSCOPE_*` / `QWEN_*` / `DEEPSEEK_*` / `OPENAI_*` |
| `.env` key NAME scan | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `DATABASE_URL`, `FRONTEND_ORIGINS`, `VITE_API_BASE_URL` |
| network probes | **none** (no credentials to probe with; not permitted) |

## Provider status

### ✅ Anthropic — READY (reference only, 0 new calls)
- Credential: `ANTHROPIC_API_KEY` — **present**.
- SDK: `anthropic` — **installed**.
- Action: **none.** Round 1B reuses Baseline V1 / Round 1A metrics for `claude-sonnet-4-5-20250929`.

### ⛔ Google Gemini — NEEDS USER SETUP
| item | needed |
|---|---|
| credential env var | **`GEMINI_API_KEY`** (Google AI Studio / `google-genai` default). *Verify:* some setups use `GOOGLE_API_KEY`; a Vertex AI path instead needs `GOOGLE_APPLICATION_CREDENTIALS` (service-account JSON) + `GOOGLE_CLOUD_PROJECT` + location. Confirm which path before declaring final. |
| SDK | optional: `pip install google-genai` (recommended). Not required — `httpx` REST path works. |
| billing / account | a Gemini API key from Google AI Studio may work on a free tier; higher-capability models and higher rate limits may require **billing enabled** on the Google Cloud project. Confirm. |
| exact model ids | **PENDING** — resolve from the model-list endpoint (`GET /v1beta/models` or `google-genai` `client.models.list()`) after the key is set. Pick one HIGH_CAPABILITY id and one COST_QUALITY (flash-class, non-thinking) id. |
| structured output | supported (`responseMimeType=application/json` + `responseSchema`, or OpenAI-compat `response_format`). |

### ⛔ Alibaba Cloud / Qwen (Model Studio / DashScope) — NEEDS USER SETUP
| item | needed |
|---|---|
| credential env var | **`DASHSCOPE_API_KEY`** (Alibaba Cloud Model Studio). *Verify* the exact name for the account's console. |
| base URL / region | **PENDING** — DashScope has region-specific OpenAI-compatible base URLs (international vs mainland China). The correct base URL must be confirmed with the account. |
| SDK | optional: `pip install dashscope`. Not required — `httpx` against the OpenAI-compatible endpoint works. |
| billing / account | Model Studio requires an activated Alibaba Cloud account; some models require **service activation** and may be region-gated. Confirm activation + region. |
| exact model ids | **PENDING** — resolve from the Model Studio catalogue / OpenAI-compatible `/models` endpoint. Pick one CHINESE_HIGH_CAPABILITY id and one CHINESE_COST_QUALITY id. |
| structured output | supported via OpenAI-compatible `response_format` (`json_schema` preferred, `json_object` fallback). |

### ⛔ DeepSeek — NEEDS USER SETUP
| item | needed |
|---|---|
| credential env var | **`DEEPSEEK_API_KEY`**. |
| base URL | `https://api.deepseek.com` (OpenAI-compatible). |
| SDK | **none** — use `httpx` against the OpenAI-compatible endpoint. (Do **not** install the `openai` SDK for this.) |
| billing / account | DeepSeek API requires a funded account (pay-as-you-go). Confirm balance. |
| exact model id | **PENDING** — resolve from the OpenAI-compatible `/models` endpoint. Pick ONE high-value chat model. If it is a mandatory chain-of-thought "reasoner" model, record `reasoning_mode=mandatory`. |
| structured output | OpenAI-compatible `response_format={"type":"json_object"}` confirmed; strict `json_schema` support **to verify**. Json mode may require the literal token `json` in the prompt (a transport-only line applied to all providers for parity). |

## ⛔ OpenAI — EXCLUDED (do not configure)
`provider_exclusion_reason = user_operational_policy`. Not a model-quality judgment. No `OPENAI_API_KEY` request, no SDK install, no configuration.

## What the user needs to do before Round 1B execution

1. **Gemini:** set `GEMINI_API_KEY` in `.env` (or confirm the Vertex path); enable billing if a high-capability model needs it; say which model tier names to target (or let Step 1/2 pick from the model list).
2. **Qwen:** set `DASHSCOPE_API_KEY`; confirm the region and its OpenAI-compatible base URL; confirm model-service activation.
3. **DeepSeek:** set `DEEPSEEK_API_KEY`; confirm account balance.
4. Optional: `pip install google-genai dashscope` into the eval venv (httpx fallback works without them).
5. Confirm that exact model identifiers will be resolved by the execution plan's Step 2 (model-list endpoints) and approved at Step 7 before any 30-call run.

**No credential values are ever printed, logged, or committed. `.env` is not modified by the evaluation tooling.**

---

## RESOLUTION UPDATE (2026-09-01) — credentials configured, models resolved

| provider | credential | status | model-list probe | region |
|---|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | **present** | (Round 1A) | — |
| Google Gemini | `GEMINI_API_KEY` | **present** | `GET /v1beta/models` -> **200** (52 models) | Google AI (generativelanguage) |
| Alibaba Qwen | `DASHSCOPE_API_KEY` | **present** | intl -> **401**; mainland -> **200** (249 models) | **mainland China** — base `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| DeepSeek | `DEEPSEEK_API_KEY` | **present** | `GET /models` -> **200** (3 models) | `https://api.deepseek.com` |
| OpenAI | — | **not configured (excluded by user operational policy)** | — | — |

Resolved candidates (pending approval): `gemini-3.7-flash`, `gemini-3.5-flash-lite`, `qwen3.8-max`,
`qwen3.8-flash`, `deepseek-v4-pro`. Detail: `cross_provider_resolved_models.json`.

Remaining before execution: implement the eval-only adapters; verify Qwen/DeepSeek strict-schema
support and DeepSeek reasoning mode at execution Step 3; obtain pricing (all 5 =
`PENDING_OFFICIAL_PRICING_VERIFICATION`); **approve the exact five model ids**.

Optional SDK installs (httpx fallback works without them): `google-genai`, `dashscope`.
No credential values are printed, logged, or committed. `.env` not modified.
