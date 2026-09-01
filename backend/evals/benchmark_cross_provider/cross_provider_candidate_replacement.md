# Cross-Provider Round 1B — Candidate Pool Replacement Log

Chronological record of every candidate-pool change. **No historical evidence is deleted** — earlier
transport records stay in `cross_provider_transport_validation.{json,md}` and the manifest
`transport_validation` block.

## Pool evolution

| date | change | reason |
|---|---|---|
| 2026-09-01 | Initial new-candidate pool: Gemini ×2, Qwen ×2, DeepSeek ×1 | Cross-Provider Readiness Audit (OpenAI excluded — `user_operational_policy`) |
| 2026-09-01 | Gemini pool: `gemini-3.7-flash`/`gemini-3.5-flash-lite` → `gemini-2.5-pro` (HIGH) / `gemini-3.7-flash` (COST); `gemini-3.5-flash-lite` dropped | user instruction before transport validation |
| 2026-09-01 | `gemini-2.5-pro` → `gemini-3.1-pro-preview` (HIGH) | transport attempt 1: `gemini-2.5-pro` HTTP 404 "no longer available to new users"; provider recommended `gemini-3.1-pro-preview` |
| 2026-09-01 | **Gemini ×2 → `EXCLUDED_BY_USER_OPERATIONAL_COST_POLICY`** | user instruction. Also historically blocked HTTP 429 (AI Studio prepayment credits depleted) on transport attempt 2. NOT a model-quality judgment. |
| 2026-09-01 | **+ `KIMI_CHINESE_HIGH_CAPABILITY` = `kimi-k3` (Moonshot AI)** | user configured `MOONSHOT_API_KEY`; Kimi added for direct Chinese product-fit (Dataset V1 is 90% Chinese-dominant). This document. |

## Current Round 1B pool (after this task)

| slot | provider | model id | planned calls | state |
|---|---|---|---|---|
| REFERENCE | anthropic | `claude-sonnet-4-5-20250929` | 0 (reuse Round 1A / Baseline V1) | verified |
| QWEN_HIGH_CAPABILITY | alibaba_qwen_dashscope | `qwen3.8-max` | 30 | transport-validated; schema-adherence pending Section D re-validation |
| QWEN_COST_QUALITY | alibaba_qwen_dashscope | `qwen3.8-flash` | 30 | transport-validated; schema-adherence pending Section D re-validation |
| DEEPSEEK_HIGH_VALUE | deepseek | `deepseek-v4-pro` | 30 | transport-validated; schema-adherence pending; `reasoning_mode = mandatory` |
| KIMI_CHINESE_HIGH_CAPABILITY | moonshot | `kimi-k3` | 30 | **candidate resolved; transport UNVALIDATED; 0 inference** |
| ~~GEMINI_HIGH_CAPABILITY~~ | ~~google_gemini~~ | ~~`gemini-3.1-pro-preview`~~ | 0 | **EXCLUDED_BY_USER_OPERATIONAL_COST_POLICY** (records preserved) |
| ~~GEMINI_COST_QUALITY~~ | ~~google_gemini~~ | ~~`gemini-3.7-flash`~~ | 0 | **EXCLUDED_BY_USER_OPERATIONAL_COST_POLICY** (records preserved) |

Screening pool size **5** (1 reference + 4 new candidates). Max new inference for Round 1B:
**4 × 30 = 120** (was 150).

---

## Kimi / Moonshot resolution detail (2026-09-01, 0 inference calls)

### Credential & endpoint
- `MOONSHOT_API_KEY` — **present** (name-only check; value never read/printed).
- Base URL resolved by non-inference model-list probe:
  - `https://api.moonshot.cn/v1/models` → **HTTP 200**, 4 models (mainland China / Moonshot Open Platform).
  - `https://api.moonshot.ai/v1/models` → **HTTP 401** "Invalid Authentication" (credential not valid for the international endpoint).
- API compatibility: **OpenAI-compatible** — `GET /v1/models`, `Authorization: Bearer`, `object: "model"`, `data[]` list. Existing `httpx` suffices; no SDK installed.

### Models available to this credential (from the provider model-list — not invented)

| id | context | reasoning metadata | role fit |
|---|---|---|---|
| **`kimi-k3`** | 1,048,576 | `supports_reasoning: true`, `supports_thinking_type: "only"`, `think_efforts` / `reasoning_efforts` = `{low, high, max}` default `max`, `supports_dynamic_tools: true`, `supports_image_in/video_in: true` | **general chat/reasoning — HIGH_CAPABILITY pick** |
| `kimi-k2.6` | 262,144 | `supports_reasoning: true` (no thinking-only flag) | general chat — lower-capability alternative |
| `kimi-k2.7-code-highspeed` | 262,144 | `supports_reasoning: true` | **coding-specialised — excluded (§7.10)** |
| `kimi-k2.7-code` | 262,144 | `supports_reasoning: true` | **coding-specialised — excluded (§7.10)** |

Metadata not exposed by `/models` (marked `PENDING_PROVIDER_METADATA`): output-token limit,
explicit stable/preview/deprecated tag, JSON-mode / JSON-Schema support flags, pricing. No
preview/deprecated marker was returned for any model, so `kimi-k3` is treated as
current/available pending a definitive stable tag.

### Recommended `KIMI_CHINESE_HIGH_CAPABILITY` candidate: **`kimi-k3`**

Why:
1. **Callable now** by this credential (appears in the 200 model-list).
2. **Newest generation** (k3 vs k2.x) — highest capability ceiling in the list.
3. **1M-token context** — 4× the `kimi-k2.6` alternative; ample headroom for the 30-item evidence payload.
4. **Dedicated reasoning-effort control** (`low`/`high`/`max`) — lets the adapter request the lowest effort for cross-model parity.
5. **Not a coding-specialised variant** — the two `-code` ids are excluded per selection criterion 10.
6. **Strong Chinese-native model** — direct product-fit: Dataset V1 is 27/30 Chinese-dominant JDs.
7. Capability gap vs `kimi-k2.6` is **substantial**, so the HIGH_CAPABILITY slot takes `kimi-k3` even though `/models` exposes no explicit stable-vs-preview tag (criterion 8 only prefers stable when the capability difference is *not* substantial).

### Reasoning mode
`reasoning_mode = mandatory` — `supports_thinking_type: "only"` means thinking cannot be disabled;
`default_effort = "max"`. `reasoning_comparability_flag = true`. **Not auto-rejected.** The eval
adapter will request `reasoning_effort`/`think_effort = "low"` (if the parameter is accepted) to
approximate single-pass parity; it will **not** enable `high`/`max`, and other candidates get **no**
compensating high-compute mode. Same handling class as `deepseek-v4-pro`.

### Structured-output classification
**`UNKNOWN_PENDING_TRANSPORT_VALIDATION`.** Moonshot is OpenAI-compatible and
`response_format={"type":"json_object"}` is expected/documented, but this cannot be verified from
`/models` metadata and no inference is permitted in this task. Moonshot `json_object` mode has
historically also required the literal token `json` in the request — if transport validation
confirms this, reuse the existing `TRANSPORT_SERIALIZATION_ONLY` line (`"Return the response as
JSON."`) **scoped to the Moonshot adapter only**, exactly as for Qwen/DeepSeek. Canonical future
output is unchanged: `summary`, `requirement_matches[{requirement_id, match_label ∈
{Strong,Partial,Missing}, evidence_ids[], reason}]`, `suggested_preparation[]`.

### Transport adapter assessment — `MoonshotBenchmarkAdapter` (eval-only)
| field | value |
|---|---|
| provider | `moonshot` |
| model_id | `kimi-k3` |
| base_url | `https://api.moonshot.cn/v1` |
| credential_env | `MOONSHOT_API_KEY` |
| transport_style | OpenAI-compatible REST `POST /v1/chat/completions` (system + user messages) |
| OpenAI-compatible | **yes** |
| structured_output mechanism | `response_format` (`json_object` expected; `json_schema` PENDING) + Section D in-prompt; `structured_output_limitation` likely true |
| temperature policy | send `temperature=0`; omit-if-rejected fallback retained (Moonshot has constrained k-series temperature historically) — PENDING transport validation |
| reasoning policy | mandatory thinking; request `reasoning_effort="low"` if accepted; record `reasoning_mode=mandatory` + comparability flag; do not compensate other candidates |
| usage metadata path | `usage.prompt_tokens` / `completion_tokens` / `total_tokens`; reasoning-token path (`completion_tokens_details.reasoning_tokens`) PENDING |
| latency capture | feasible (wall-clock around the single non-streaming call), identical to other adapters |
| **adapter complexity** | **LOW** — another OpenAI-compatible endpoint; the `QwenBenchmarkAdapter` / `DeepSeekBenchmarkAdapter` pattern applies directly; only extra is the mandatory-reasoning effort control |

### Pricing
`pricing_status = PENDING_OFFICIAL_PRICING_VERIFICATION` — `/models` returned no pricing fields; no
web search performed in this task.

### Next step
STOP. No synthetic transport smoke test in this task. The exact Kimi model (`kimi-k3`) must be
approved by the assistant/user first; then a small synthetic **Section A + Section D** transport
validation (synthetic requirement/evidence only) will run.

---

## Final transport-validation gate (2026-09-01, attempt 3) — `kimi-k3` approved, then blocked on temperature

`kimi-k3` was **approved** as the Kimi benchmark candidate and included in the final
Section A + Section D transport-validation gate (4 calls: `qwen3.8-max`, `qwen3.8-flash`,
`deepseek-v4-pro`, `kimi-k3`; Gemini excluded, not called).

| model | result |
|---|---|
| `qwen3.8-max` | **PASS** (HTTP 200; exact canonical fields; no aliases; single-pass) |
| `qwen3.8-flash` | **PASS** (HTTP 200; same) |
| `deepseek-v4-pro` | **PASS** (HTTP 200; same; `reasoning_mode=mandatory`, `reasoning_tokens=105`) |
| `kimi-k3` | **FAIL / TRANSPORT_BLOCKED** — HTTP 400 `"invalid temperature: only 1 is allowed for this model"` |

`kimi-k3` blocker: **`temperature=0` (the fixed production value) is rejected — `kimi-k3` mandates
`temperature=1`.** This is the **Opus-5 lesson repeating for Moonshot**. The request failed at
parameter validation **before** `reasoning_effort="low"` (the correct OpenAI-compatible param;
metadata key `reasoning_efforts`, valid `low`/`high`/`max`, default `max`) or the JSON / Section D
contract could be evaluated — so Kimi's structured-output class and reasoning-effort acceptance
remain **UNKNOWN**.

Per the task rules the call was **not retried**, no alternative parameters were tried, and the
candidate was **not substituted**. `kimi-k3` remains the KIMI_CHINESE_HIGH_CAPABILITY candidate.

**Fix (pre-approved by the manifest `transport_policy` / Opus-5 lesson; NOT applied here):** one
explicitly-approved single synthetic re-call with `temperature=1` (recording a
`temperature_comparability_note`) or with `temperature` omitted; then verify
`reasoning_effort="low"` acceptance and full Section D adherence against the §15 bar. See
`cross_provider_execution_plan.md` Step 3e.

Manifest after attempt 3: `status = transport_validation_incomplete`,
`candidate_resolution_complete = false`, `benchmark_execution_approved = false`. 3 / 4 new
candidates transport-validated.

---

## `kimi-k3` re-validation (2026-09-01, attempt 3b) — single approved call — **PASS**

One explicitly-approved synthetic call: `temperature=1` (`MODEL_REQUIRED_VALUE`) +
`reasoning_effort="low"` + Section A + Section D. No retry, no fallback, no substitute.

| check | result |
|---|---|
| HTTP | **200** |
| `temperature=1` accepted | **yes** (temperature=0 had returned HTTP 400) |
| `reasoning_effort="low"` accepted | **yes** (HTTP 200, no param error; effort not echoed by API) |
| structured output | **JSON_OBJECT_ONLY** — Section D honoured exactly |
| canonical fields | **EXACT** — top-level `{summary, requirement_matches, suggested_preparation}`, item `{requirement_id, match_label, evidence_ids, reason}`, no aliases, no extras, no adapter semantic repair |
| `requirement_id` preserved | **yes** (`synthetic_req_001`) |
| `match_label` | `"Strong"` (valid) |
| `evidence_ids` | `["synthetic_ev_001"]` (canonical list) |
| reasoning | **mandatory** — `reasoning_content` present, `reasoning_tokens = 170` |
| usage | in 636 / out 320 / reasoning 170 / total 956 |
| latency | 13,601.3 ms |
| **verdict** | **PASS** (all 12 §8 criteria) |

**All four new candidates are now transport-validated.** Manifest:
`status = transport_validation_complete`, `candidate_resolution_complete = true`,
`benchmark_execution_approved = false`.

### Final Round 1B pool

| slot | provider | model id | Round 1B calls | comparability flags |
|---|---|---|---|---|
| REFERENCE | anthropic | `claude-sonnet-4-5-20250929` | 0 (reuse) | — |
| QWEN_HIGH_CAPABILITY | alibaba_qwen_dashscope | `qwen3.8-max` | 30 | — |
| QWEN_COST_QUALITY | alibaba_qwen_dashscope | `qwen3.8-flash` | 30 | — |
| DEEPSEEK_HIGH_VALUE | deepseek | `deepseek-v4-pro` | 30 | `reasoning_comparability_flag` |
| KIMI_CHINESE_HIGH_CAPABILITY | moonshot | `kimi-k3` | 30 | `reasoning_comparability_flag` + `temperature_comparability_flag` (`temperature=1`) |

Future new inference calls: **120** (4 × 30). Gemini excluded (records preserved). **Round 1B is NOT
started — awaiting explicit approval.**
