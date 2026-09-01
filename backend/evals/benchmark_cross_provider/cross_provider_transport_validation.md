# Cross-Provider Transport Validation (before Round 1B)

**Synthetic transport smoke test — NOT the benchmark.** No Dataset V1 JD, no Ground Truth
requirement, no real candidate evidence, no Human Match Fit, no baseline slice reached any model.
No quality metrics computed.

- **Attempt 1 (2026-09-01)** — 5 calls, 0 tokens billed, **0/5 passed**: `gemini-2.5-pro` 404,
  `gemini-3.7-flash` 503, `qwen3.8-max`/`qwen3.8-flash` 400 (json-token), `deepseek-v4-pro` 402.
- **Attempt 2 — re-validation (2026-09-01)** — 5 calls, 1,896 tokens billed, **0/5 fully passed**:
  Gemini ×2 HTTP 429 (account prepay depleted); Qwen ×2 + DeepSeek HTTP 200 but the minimal
  Section-A-only prompt let each model invent label keys (`match_level` / `match_status` /
  `match_grade`).
- **Attempt 3 — FINAL transport-validation gate (2026-09-01)** — Gemini **excluded**
  (`USER_OPERATIONAL_COST_POLICY`); 4 new candidates, **Section A + Section D**, **4 calls, 0
  retries, 2,190 tokens billed**, **3 / 4 passed**. `kimi-k3` **TRANSPORT_BLOCKED** on `temperature`.
- **Attempt 3b — `kimi-k3` single approved re-call (2026-09-01)** — `temperature=1` (model-required)
  + `reasoning_effort=low`, **Section A + Section D**, **1 call, 0 retries, 956 tokens billed**.
  **`kimi-k3` PASS.** All four new candidates are now transport-validated →
  `status = transport_validation_complete`.

---

## Final five-model screening pool (attempt 3)

| slot | provider | model id | Round 1B calls |
|---|---|---|---|
| REFERENCE | anthropic | `claude-sonnet-4-5-20250929` | 0 (reuse Round 1A / Baseline V1) |
| QWEN_HIGH_CAPABILITY | alibaba_qwen_dashscope | `qwen3.8-max` | 30 |
| QWEN_COST_QUALITY | alibaba_qwen_dashscope | `qwen3.8-flash` | 30 |
| DEEPSEEK_HIGH_VALUE | deepseek | `deepseek-v4-pro` | 30 |
| KIMI_CHINESE_HIGH_CAPABILITY | moonshot | `kimi-k3` | 30 |
| ~~GEMINI ×2~~ | ~~google_gemini~~ | — | **EXCLUDED_BY_USER_OPERATIONAL_COST_POLICY** (records preserved) |

Gemini not queried or called in attempt 3. No GLM. No silent substitution.

## Prompt assembly — Section A + Section D (confirmed)

Every attempt-3 request carried:

- **Section A** — the frozen `job-fit-v3-matchable-only` semantic matching instructions, byte-identical
  to `cross_provider_prompt_parity.md` §A. **Not modified.** ("You are JobPilot's evidence-grounded
  requirement matcher …")
- **Section D** — the canonical `FitAnalysisOutput` field contract, **output-contract only**:
  top-level `summary` / `requirement_matches` / `suggested_preparation`; each `requirement_matches`
  item `requirement_id` / `match_label` (`Strong` | `Partial` | `Missing`) / `evidence_ids` (array) /
  `reason`; each `suggested_preparation` item `title` / `action` / `priority` / `requirement_ids`.
  Section D explicitly forbids the aliases `match_level` / `match_status` / `match_grade` /
  `evidence_source_ids` / `reasons`. **No OR-list / adjacency / project-vs-work / compound /
  examples / Ground Truth / rubric guidance** — none added. The semantic prompt was not improved.

**Result: Section D eliminated the attempt-2 alias problem.** All three HTTP-200 models returned the
exact canonical top-level keys and the exact canonical item keys, with **no adapter-side semantic
repair**.

## Synthetic test definition

- Requirement `synthetic_req_001` — "Has experience using SQL for product analytics."
- Evidence `synthetic_ev_001` — "Built a small analytics dashboard using SQL to analyse product usage."

## Results — 3 / 4 passed the §15 pass bar

| candidate | HTTP | structured-output class | canonical fields | req_id | match_label | evidence_ids | reason | verdict |
|---|---|---|---|---|---|---|---|---|
| `qwen3.8-max` | **200** | JSON_OBJECT_ONLY (+ Section D) | exact top-level + exact item keys, no aliases | `synthetic_req_001` ✓ | `"Strong"` ✓ | `["synthetic_ev_001"]` (list) ✓ | non-empty string ✓ | **PASS** |
| `qwen3.8-flash` | **200** | JSON_OBJECT_ONLY (+ Section D) | exact, no aliases | ✓ | `"Strong"` ✓ | list ✓ | string ✓ | **PASS** |
| `deepseek-v4-pro` | **200** | JSON_OBJECT_ONLY (+ Section D) | exact, no aliases | ✓ | `"Strong"` ✓ | list ✓ | string ✓ | **PASS** (reasoning mandatory) |
| `kimi-k3` | **400** | **TRANSPORT_BLOCKED** | — | — | — | — | — | **FAIL — blocked** |

### `kimi-k3` blocker (exact)

```
HTTP 400 invalid_request_error
"invalid temperature: only 1 is allowed for this model"
```

The request set `temperature=0` (the fixed production value). **`kimi-k3` rejects `temperature=0`
and mandates `temperature=1`.** This is the **Opus-5 lesson repeating for Moonshot** — semantic-
contract parity ≠ transport-parameter identity. The request failed at parameter validation **before**
`reasoning_effort` or the JSON contract were evaluated, so for `kimi-k3`:

- `reasoning_effort: "low"` acceptance — **UNKNOWN** (not reached).
- structured-output class — **UNKNOWN_PENDING_TRANSPORT_VALIDATION** (not reached).
- requirement-id / match_label / evidence_ids / reason adherence — **not observable**.

Per this task's rules (no retries, no silent parameter experimentation, no substitution, 4-call cap
reached) the blocker is recorded and the model is **not** retried or replaced here. The fix is
already pre-approved in the manifest `transport_policy` ("omit the temperature parameter for any
model whose API rejects/deprecates it — LESSON FROM OPUS 5"); for `kimi-k3` specifically the API
wants `temperature=1` rather than omission. Applying it needs **one** explicitly-approved single
re-call.

## Per-candidate detail

### `qwen3.8-max` — PASS
- Base `https://dashscope.aliyuncs.com/compatible-mode/v1`; `temperature=0` accepted; `enable_thinking=false` accepted; `response_format={"type":"json_object"}`; `TRANSPORT_SERIALIZATION_ONLY` line `"Return the response as JSON."` (Qwen adapter scope).
- Top-level keys exactly `{summary, requirement_matches, suggested_preparation}`. Item keys exactly `{requirement_id, match_label, evidence_ids, reason}`. No alias fields. No extra keys.
- `requirement_id = "synthetic_req_001"`; `match_label = "Strong"`; `evidence_ids = ["synthetic_ev_001"]`; `reason` non-empty.
- Usage: input **539**, output **146**, reasoning **null**, total **685**. Latency **3,608.9 ms**. `reasoning_content` absent (single-pass).

### `qwen3.8-flash` — PASS
- Same transport policy and model params.
- Exact canonical top-level + item keys, no aliases, no extras.
- `requirement_id` preserved; `match_label = "Strong"`; `evidence_ids` a list; `reason` a string.
- Usage: input **539**, output **133**, reasoning **null**, total **672**. Latency **2,226.4 ms**. Single-pass.

### `deepseek-v4-pro` — PASS
- Base `https://api.deepseek.com`; `temperature=0` accepted; `response_format={"type":"json_object"}`; `TRANSPORT_SERIALIZATION_ONLY` line `"Return the response as JSON."` (DeepSeek adapter scope).
- Exact canonical top-level + item keys, no aliases, no extras.
- `requirement_id` preserved; `match_label = "Strong"`; `evidence_ids = ["synthetic_ev_001"]`; `reason` a string.
- **`reasoning_mode = mandatory`** — `reasoning_content` present; `usage.completion_tokens_details.reasoning_tokens = 105`. `reasoning_comparability_flag = true` (permanent).
- Usage: input **612**, output **221**, reasoning **105**, total **833**. Latency **4,888.6 ms**.

### `kimi-k3` — FAIL / TRANSPORT_BLOCKED
- Base `https://api.moonshot.cn/v1`; model `kimi-k3`; `MOONSHOT_API_KEY`.
- Sent: `temperature=0`, `max_tokens=2048`, `response_format={"type":"json_object"}`,
  `reasoning_effort="low"` (OpenAI-compatible param; metadata key `reasoning_efforts`, valid
  `low`/`high`/`max`), `TRANSPORT_SERIALIZATION_ONLY` line (Moonshot adapter scope).
- **HTTP 400** — `temperature=0` rejected; model requires `temperature=1`.
- No usage / no response / latency **1,283.6 ms** (round-trip to the 400).

## Structured-output mechanism used per model

| model | mechanism | final class |
|---|---|---|
| `qwen3.8-max` | `response_format={"type":"json_object"}` + Section D in-prompt + json-token line | **JSON_OBJECT_ONLY** (Section D fully honoured) |
| `qwen3.8-flash` | same | **JSON_OBJECT_ONLY** |
| `deepseek-v4-pro` | same | **JSON_OBJECT_ONLY** |
| `kimi-k3` | intended `response_format={"type":"json_object"}` + Section D + json-token line; **not reached** | **TRANSPORT_BLOCKED** (temperature) |

Strict provider-native `json_schema` was **not** asserted for any model this run (json_object +
Section D was sufficient for the three that ran); a strict-schema probe stays optional for Round 1B.

## Reasoning-mode classification

| model | reasoning_mode | comparability flag | evidence |
|---|---|---|---|
| `qwen3.8-max` | standard single-pass (`enable_thinking=false`) | — | `reasoning_content` absent; `reasoning_tokens` null |
| `qwen3.8-flash` | standard single-pass | — | same |
| `deepseek-v4-pro` | **mandatory** | **true** | `reasoning_content` present; `reasoning_tokens = 105` |
| `kimi-k3` | **mandatory** (from metadata `supports_thinking_type="only"`); effort request not yet accepted | **true** | requested `reasoning_effort="low"`; blocked by temperature before evaluation |
| `claude-sonnet-4-5-20250929` (reference) | standard production single-pass (no thinking param) | — | Baseline V1 / Round 1A |

Round 1B parity: Kimi = mandatory reasoning at lowest supported effort (`low`, pending acceptance);
DeepSeek = mandatory reasoning standard mode; Qwen = thinking disabled; Claude = existing production
baseline. **Claude/Qwen are not given artificial reasoning.**

## Canonical field adherence (the attempt-2 fix, verified)

| model | top-level exact | item keys exact | alias fields | adapter semantic repair |
|---|---|---|---|---|
| `qwen3.8-max` | ✓ `{summary, requirement_matches, suggested_preparation}` | ✓ `{requirement_id, match_label, evidence_ids, reason}` | none | **none** |
| `qwen3.8-flash` | ✓ | ✓ | none | **none** |
| `deepseek-v4-pro` | ✓ | ✓ | none | **none** |
| `kimi-k3` | — (blocked) | — | — | — |

## Requirement-id preservation

`qwen3.8-max`, `qwen3.8-flash`, `deepseek-v4-pro` — all echoed `synthetic_req_001` verbatim.
`kimi-k3` — not observable (blocked).

## Evidence-id field adherence

All three HTTP-200 models emitted `evidence_ids` (canonical name) as a JSON array containing
`"synthetic_ev_001"`. No `evidence_source_ids` alias. `kimi-k3` — not observable.

## Temperature compatibility

| model | `temperature=0` |
|---|---|
| `qwen3.8-max` | **accepted** (HTTP 200) |
| `qwen3.8-flash` | **accepted** (HTTP 200) |
| `deepseek-v4-pro` | **accepted** (HTTP 200) |
| `kimi-k3` | **REJECTED** — "only 1 is allowed for this model" (HTTP 400). Opus-5-class transport-parameter incompatibility. |

## Usage-token capture

| model | input | output | reasoning | total |
|---|---|---|---|---|
| `qwen3.8-max` | 539 | 146 | null | 685 |
| `qwen3.8-flash` | 539 | 133 | null | 672 |
| `deepseek-v4-pro` | 612 | 221 | 105 | 833 |
| `kimi-k3` | — | — | — | — (blocked) |
| **total billed** | **1,690** | **500** | **105** | **2,190** |

## Reasoning-token capture

`deepseek-v4-pro`: `reasoning_tokens = 105` via `usage.completion_tokens_details.reasoning_tokens`
(+ `message.reasoning_content` present). Qwen ×2: `null` (expected under `enable_thinking=false`).
`kimi-k3`: not captured (blocked); the reasoning-token path stays PENDING.

## Latency

`qwen3.8-max` 3,608.9 ms · `qwen3.8-flash` 2,226.4 ms · `deepseek-v4-pro` 4,888.6 ms ·
`kimi-k3` 1,283.6 ms (to the HTTP 400).

## Pass / fail per model

| model | verdict |
|---|---|
| `qwen3.8-max` | **PASS** — all 11 §15 criteria met; JSON_OBJECT_ONLY + Section D; no repair |
| `qwen3.8-flash` | **PASS** — all 11 §15 criteria met |
| `deepseek-v4-pro` | **PASS** — all 11 §15 criteria met; `reasoning_mode=mandatory` recorded (not a fail cause) |
| `kimi-k3` | **FAIL — TRANSPORT_BLOCKED**: `temperature=0` rejected (model requires `temperature=1`) |

**3 / 4 new candidates transport-validated. 1 blocked. No substitution.**

## Remaining blockers

| model | blocker | class | fix (NOT applied here) |
|---|---|---|---|
| `kimi-k3` | HTTP 400 `temperature=0` rejected; model requires `temperature=1` | TRANSPORT_PARAMETER (Opus-5 class) | one explicitly-approved single re-call with `temperature=1` (or `temperature` omitted); record a `temperature_comparability_note`; then re-check `reasoning_effort="low"` acceptance + Section D adherence |

## Smoke-test tokens / cost

- Tokens billed: **input 1,690 · output 500 · reasoning 105 · total 2,190** (across the 3 HTTP-200 calls). `kimi-k3` billed 0.
- Cost: **`PENDING_OFFICIAL_PRICING_VERIFICATION`** — not computed, not guessed. Not part of benchmark cost.

## Integrity (re-verified after attempt 3)

- `requirement_matcher.py` `e99ed02728452d6f50b39867a6dbf5e5a79e0fb9d78b610d66297f5d6a1ad19b`
- `claude_client.py` `76d953c4ae852502c0c85b16a53f1f8fcaeb3a7f39c791ff1776a3ed0b729b81`
- `match_score.py` `8ae2d59389da7f3ae783bb57daca81c6611cd5c009a95005e6d772bc6c8dfad2`
- Ground Truth `52cda176e166146ffc24a85067f13618c5f717cedab506f0ba17fe5e701ba050`
- Dataset V1 `3654d64c0f94e507e91343706bd79ca6b20f8081ee22880bf537744d88b2b558`
- No file under `backend/app/`, `backend/alembic/`, `frontend/` changed. `.env` not modified.
- No Dataset V1 / Ground Truth / real candidate evidence / Human Match Fit / baseline slice sent to any model.
- Gemini exclusion history, Opus 5 temperature incompatibility, Haiku 4.5 Round 1A results, Sonnet
  baseline, Round 1A, prior Qwen/DeepSeek smoke failures+fixes, Kimi candidate-resolution metadata —
  all preserved.

---

# Attempt 3b — `kimi-k3` single approved temperature re-validation (2026-09-01)

**1 synthetic inference call. 0 retries. 0 fallback. 0 substitution.** Section A + Section D.
Synthetic `synthetic_req_001` / `synthetic_ev_001` only. No Dataset V1 / Ground Truth / real
evidence. No quality metrics.

## Transport parameters
| field | value |
|---|---|
| `temperature_requested` | **1** (`temperature_policy = MODEL_REQUIRED_VALUE`; `temperature_comparability_flag = true`) |
| `temperature_accepted` | **yes** — HTTP 200 (attempt-3 `temperature=0` had returned HTTP 400) |
| `reasoning_effort_requested` | **`low`** (param `reasoning_effort`; OpenAI-compatible; metadata key `reasoning_efforts`, valid `low`/`high`/`max`, default `max`) |
| `reasoning_effort_accepted` | **yes** — HTTP 200, no parameter error; `observed_reasoning_effort` not echoed by the API |
| structured output | `response_format={"type":"json_object"}` + Section D in-prompt + `"Return the response as JSON."` (`TRANSPORT_SERIALIZATION_ONLY`, Moonshot adapter scope) |

## Result — **PASS** (all 12 §8 criteria)

| # | criterion | result |
|---|---|---|
| 1 | HTTP inference succeeds | ✓ HTTP 200 |
| 2 | response is parseable JSON | ✓ |
| 3 | canonical top-level fields exist | ✓ exactly `{summary, requirement_matches, suggested_preparation}` |
| 4 | item has `requirement_id` / `match_label` / `evidence_ids` / `reason` | ✓ exactly those 4, no extras |
| 5 | `requirement_id == synthetic_req_001` | ✓ |
| 6 | `match_label ∈ {Strong, Partial, Missing}` | ✓ `"Strong"` |
| 7 | `evidence_ids` is a canonical list | ✓ `["synthetic_ev_001"]` |
| 8 | no semantic alias remapping needed | ✓ no `match_level` / `match_status` / `match_grade` / `evidence_source_ids` / `reasons` |
| 9 | `reasoning_effort=low` accepted | ✓ |
| 10 | usage metadata captured | ✓ |
| 11 | reasoning-token metadata captured | ✓ `reasoning_tokens = 170` (+ `reasoning_content` present) |
| 12 | latency captured | ✓ **13,601.3 ms** |

## Recorded metadata
| field | value |
|---|---|
| model_id | `kimi-k3` |
| provider / base_url | Moonshot AI / `https://api.moonshot.cn/v1` |
| `temperature_requested` / `temperature_accepted` | 1 / **yes** |
| `reasoning_mode` | **mandatory** |
| `reasoning_effort_requested` / `reasoning_effort_accepted` | `low` / **yes** |
| `observed_reasoning_effort` | not returned by the API |
| `input_tokens` | 636 |
| `output_tokens` | 320 |
| `reasoning_tokens` | 170 |
| `total_tokens` | 956 |
| `latency_ms` | 13,601.3 |
| `structured_output_class` | **JSON_OBJECT_ONLY** (Section D honoured exactly) |
| `canonical_field_adherence` | **EXACT** |
| `requirement_id_preserved` | **true** |
| `reasoning_comparability_flag` | **true** (mandatory reasoning at lowest effort) |
| tokens billed | 956 (input 636 / output 320, incl. 170 reasoning) |
| cost | `PENDING_OFFICIAL_PRICING_VERIFICATION` — not computed |

## Verdict — 4 / 4 new candidates transport-validated

| model | transport status |
|---|---|
| `qwen3.8-max` | **TRANSPORT_VALIDATED** (attempt 3) |
| `qwen3.8-flash` | **TRANSPORT_VALIDATED** (attempt 3) |
| `deepseek-v4-pro` | **TRANSPORT_VALIDATED** (attempt 3; `reasoning_mode=mandatory`) |
| `kimi-k3` | **TRANSPORT_VALIDATED** (attempt 3b; `temperature=1` required; `reasoning_mode=mandatory`, effort `low`) |

Manifest: `status = transport_validation_complete`, `candidate_resolution_complete = true`,
`benchmark_execution_approved = false`. Round 1B pool: `claude-sonnet-4-5-20250929` (reference, 0
calls) + `qwen3.8-max` + `qwen3.8-flash` + `deepseek-v4-pro` + `kimi-k3`. Future new inference
calls: **120** (4 × 30).

`deepseek-v4-pro` and `kimi-k3` carry `reasoning_comparability_flag = true` into Round 1B;
`kimi-k3` additionally carries `temperature_comparability_flag = true` (`temperature=1` vs the
`temperature=0` used by every other candidate). Do not compensate other candidates.

**Round 1B is NOT started.** Awaiting explicit approval.
