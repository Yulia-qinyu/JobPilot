# Cross-Provider Eval-Only Adapter Design (Round 1B)

**Not implemented in this readiness task.** Design only. All adapters live under `backend/evals/`
(no production service is modified). Production Anthropic behaviour stays exactly as it is.

## Why an abstraction (lesson from Opus 5)

Round 1A showed **semantic-contract parity ≠ transport-parameter identity**: the production client
hard-codes `temperature=0`, and `claude-opus-5` rejects that parameter, so a semantically-identical
task could not be sent. Cross-provider screening must isolate:

- **SEMANTIC CONTRACT** — Sections A + B + C + D of `cross_provider_prompt_parity.md` (fixed), and
- **PROVIDER / MODEL TRANSPORT ADAPTER** — per-provider serialization, auth, endpoint, schema
  binding, and parameter quirks (allowed to differ; `TRANSPORT_SERIALIZATION_ONLY`).

## `BenchmarkModelAdapter` — conceptual interface

```
class BenchmarkModelAdapter:                     # eval-only, backend/evals/scripts/
    provider: str                                # "anthropic" | "google_gemini" | "alibaba_qwen" | "deepseek"
    model_id: str

    def build_request(self, *, semantic_prompt: str, structured_schema: dict,
                      job_id: str, matchable_requirements: list, frozen_evidence: list) -> dict:
        """Assemble A+B+C into this provider's transport shape. NO semantic guidance added."""

    def call(self, request: dict) -> AdapterResult:
        """Single non-streaming structured call. temperature=0 if accepted, else omit + record."""
```

### `AdapterResult` (uniform across providers)

```
provider              : str
model_id              : str
raw_response          : dict            # full provider JSON (secrets stripped)
parsed_output          : FitAnalysisOutput | None   # mapped into the production wire model
normalized_output      : list[RequirementMatch] | None   # from production _normalize_matches
usage                  : {input_tokens, output_tokens, total_tokens, cached_input_tokens?, reasoning_tokens?}
latency_ms             : float
schema_success         : bool          # parsed into FitAnalysisOutput without loss
transport_metadata     : {endpoint, auth_env_var, temperature_sent: bool, json_mode, system_user_split: bool,
                          json_mandate_line_added: bool, response_schema_kind, region_base_url?}
retry_count            : int           # provider-SDK / httpx-retry default only; no eval-added retries
error                  : str | None
```

## Per-provider adapters

### `AnthropicBenchmarkAdapter` (reference — reused, not re-run in 1B)
- Transport: existing `ClaudeStructuredClient.generate(prompt, output_model=FitAnalysisOutput, tool_name="submit_requirement_matches")`, or a 5-line eval wrapper around `client.messages.parse`.
- `temperature=0` sent. No `thinking` param. `transport_metadata.json_mode = "messages.parse output_format"`.

### `GeminiBenchmarkAdapter`
- Transport option 1 (native): `google-genai` SDK `client.models.generate_content(model=<id>, contents=<A+B+C>, config=GenerateContentConfig(response_mime_type="application/json", response_schema=<JSON Schema of FitAnalysisOutput>, temperature=0))`.
- Transport option 2 (no SDK): `httpx.post(f"{BASE}/v1beta/models/{id}:generateContent", headers={"x-goog-api-key": KEY}, json={"contents":[...], "generationConfig":{"responseMimeType":"application/json","responseSchema":{...},"temperature":0}})`.
- Optional: OpenAI-compat endpoint `/v1beta/openai/chat/completions` with `response_format={"type":"json_schema", "json_schema":{...}}`.
- `system_instruction` = Section A allowed (transport split); user = B + C. Record `system_user_split=true`.
- Reasoning: use the standard / non-thinking model id; do **not** set a thinking budget.

### `QwenBenchmarkAdapter` (Alibaba Model Studio / DashScope)
- Transport (OpenAI-compatible, preferred): `httpx.post(f"{BASE}/chat/completions", headers={"Authorization": f"Bearer {DASHSCOPE_API_KEY}"}, json={"model":<id>, "messages":[{"role":"system","content":A},{"role":"user","content":B+C}], "response_format":{"type":"json_schema","json_schema":{...}}, "temperature":0})`.
  - `BASE` = the region-correct DashScope OpenAI-compatible base URL (intl vs cn) — **resolve at Step 1**.
- If `json_schema` is not accepted: fall back to `response_format={"type":"json_object"}`, keep Section D's schema in the prompt as instruction, and set `structured_output_limitation=true`.
- Reasoning: do **not** pass `enable_thinking=true`. Record `reasoning_mode=standard`.
- Native alternative: `dashscope` SDK `Generation.call(...)` (optional; httpx path avoids the dependency).

### `DeepSeekBenchmarkAdapter`
- Transport (OpenAI-compatible): `httpx.post("https://api.deepseek.com/chat/completions", headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}, json={"model":<id>, "messages":[{"role":"system","content":A},{"role":"user","content":B+C+JSON_MANDATE}], "response_format":{"type":"json_object"}, "temperature":0})`.
- `JSON_MANDATE` = the transport-only line **"Respond only with a single JSON object."** — DeepSeek json mode historically requires the literal token `json` in the prompt. **Apply the identical line to every provider** so parity holds; label `json_mandate_line_added=true` on all.
- Strict `json_schema` support: **verify at Step 3**; if unavailable, `structured_output_limitation=true` and measure schema reliability.
- Model choice: the standard chat model. Avoid the mandatory-CoT reasoner unless it *is* the chosen high-value model — then record `reasoning_mode=mandatory` and do not compensate other candidates.
- `openai` SDK is **not** installed and **not** to be installed (OpenAI-provider exclusion is unrelated, but the httpx path keeps the dependency surface minimal).

## Output → production normalization (unchanged)

Every adapter maps its provider output into the production `FitAnalysisOutput` pydantic model
(`summary`, `requirement_matches[RequirementMatchOutput]`, `suggested_preparation[PreparationOutput]`),
then hands it to the **unchanged** `FitAnalysisService._normalize_matches(output, catalog, evidence)`
and `MatchScoreService.score(normalized)`. Adapters never fill in missing semantic fields — if the
model omits `importance` / `is_hard_requirement` / `hard_requirement_category` / `confidence`, that is
a `schema_success=false` for that call and is measured, not patched.

## Mapping notes

- `match_label` (Strong/Partial/Missing) ↔ production `match_status`.
- `evidence_ids` strings ↔ production `evidence_source_ids`; `_normalize_matches` drops any id not in
  the frozen catalog (so "unsupported evidence" is measured downstream, identical to Round 1A).
- Provider token accounting field names differ (`usage.input_tokens` / `usage.prompt_tokens` /
  `usageMetadata.promptTokenCount`); the adapter normalises to `{input_tokens, output_tokens,
  total_tokens}` and records any `cached_input_tokens` / `reasoning_tokens` separately for cost.

## Hard constraints

- No file under `backend/app/`, `backend/alembic/`, `frontend/` is created or modified.
- No new production dependency. `google-genai` / `dashscope` are **optional** eval-only installs; the
  `httpx` path (already a dependency) works for all three new providers.
- No eval-added retry logic beyond the SDK / httpx default.
- No streaming. One structured call per job. 30 calls per model.

---

## Transport-validation update (2026-09-01)

- **Qwen DashScope also mandates the token `json` in the request** for `response_format:{type:json_object}`
  (smoke test returned HTTP 400 `'messages' must contain the word 'json' in some form`). The
  `QwenBenchmarkAdapter` therefore appends the same minimal `"Return the response as JSON."` line
  (`TRANSPORT_SERIALIZATION_ONLY`, Qwen adapter scope). This is **required by Qwen's own API**, not
  parity propagation from DeepSeek. `enable_thinking=false` and `temperature=0` were accepted.
- **`gemini-2.5-pro` is NOT callable by the current credential** (HTTP 404 — "no longer available to
  new users"). `AnthropicBenchmarkAdapter` is unaffected; the Gemini HIGH_CAPABILITY slot needs a
  re-approved model id (`gemini-3.1-pro-preview` or `gemini-3.7-flash`).
- **`gemini-3.7-flash`**: transient HTTP 503 (high demand); re-validate.
- **`deepseek-v4-pro`**: HTTP 402 Insufficient Balance; user must fund the account before the
  `DeepSeekBenchmarkAdapter` can be validated.
- **`temperature`**: no provider rejected `temperature=0` (contrast Opus 5). The omit-if-rejected
  fallback stays, but is not needed for any current candidate.

## Transport RE-VALIDATION update (2026-09-01, attempt 2)

- **Gemini pool change**: `gemini-2.5-pro` (HTTP 404 attempt 1) → **`gemini-3.1-pro-preview`** as
  GEMINI_HIGH_CAPABILITY (provider-recommended; only Pro-tier id in the model list;
  `release_status=preview`, `operational_stability_flag=true`). `gemini-3.7-flash` stays as
  GEMINI_COST_QUALITY. The `GeminiBenchmarkAdapter` for the pro-preview slot **does not send
  `thinkingConfig`** — per task policy the model's native reasoning is neither forced off nor given a
  premium/max budget; actual `thoughtsTokenCount` is recorded.
- **Gemini adapter — NEW blocker**: both Gemini candidates returned **HTTP 429 RESOURCE_EXHAUSTED**
  ("prepayment credits are depleted"). This is an **account-billing** block on the shared Gemini /
  AI Studio project, not transport. The `GeminiBenchmarkAdapter` request shape is still unconfirmed.
  User must fund the Gemini account; both Gemini candidates then unblock together.
- **Qwen adapter — json-token fix VALIDATED**: appending `"Return the response as JSON."`
  (`TRANSPORT_SERIALIZATION_ONLY`, Qwen adapter scope) took `qwen3.8-max` / `qwen3.8-flash` from
  HTTP 400 → **HTTP 200**. `temperature=0` and `enable_thinking=false` accepted; `reasoning_tokens`
  null (standard single-pass). `requirement_id` preserved; usage + latency captured.
- **DeepSeek adapter — funded + json-token line VALIDATED**: account funded
  (`GET /user/balance` → `is_available=true`, boolean only). `deepseek-v4-pro` HTTP 402 → **HTTP 200**
  with the same `"Return the response as JSON."` line (DeepSeek adapter scope). **`reasoning_mode =
  mandatory`** confirmed: `usage.completion_tokens_details.reasoning_tokens = 408`,
  `message.reasoning_content` present, no disable switch. Record the comparability flag; do **not**
  grant other candidates a compensating high-compute mode.
- **NEW: JSON_OBJECT_ONLY providers need Section D in the assembled prompt**. The minimal smoke
  request carried only Section A. Under `response_format:{type:json_object}` with no in-prompt field
  contract, each of the 3 models named the label field differently — `match_level` (qwen3.8-max),
  `match_status` (qwen3.8-flash), `match_grade` (deepseek-v4-pro) — and varied `reason`/`reasons`,
  item nesting, and `evidence_source_ids` placement. **`_normalize_matches` must not repair this.**
  The Round 1B assembled prompt already includes **Section D** (`cross_provider_prompt_parity.md` §D)
  for every provider — identical wording, no semantic content — so this is a smoke-harness gap, not a
  model or transport defect. For strict-schema providers (Gemini) the `responseSchema` binding also
  fixes key names; for JSON_OBJECT_ONLY providers Section D stays in-prompt and
  `structured_output_limitation=true`, with schema-key adherence measured as a reliability metric.
  The next re-validation smoke run must assemble **Section A + Section D** and probe strict
  `json_schema` where available.
- **`temperature`**: still not rejected anywhere (Qwen ×2 + DeepSeek accepted `temperature=0` at
  HTTP 200; Gemini blocked before parameter validation).

## Candidate-pool update (2026-09-01) — Gemini excluded, Kimi added

- **Gemini ×2 removed from the pool**: `EXCLUDED_BY_USER_OPERATIONAL_COST_POLICY` (user instruction;
  also historically HTTP 429 prepay-depleted). `GeminiBenchmarkAdapter` stays documented above for
  the historical record but is **not to be run**. No further Gemini metadata calls / billing
  requests.
- **`MoonshotBenchmarkAdapter` (new, eval-only)** — `KIMI_CHINESE_HIGH_CAPABILITY = kimi-k3`:
  - Transport (OpenAI-compatible): `httpx.post("https://api.moonshot.cn/v1/chat/completions",
    headers={"Authorization": f"Bearer {MOONSHOT_API_KEY}"}, json={"model": "kimi-k3",
    "messages": [{"role":"system","content": A}, {"role":"user","content": B + C + D}],
    "response_format": {"type": "json_object"}, "temperature": 0})`.
  - Base URL: `https://api.moonshot.cn/v1` (mainland — resolved; the `.ai` international host returned
    HTTP 401 for this credential).
  - `credential_env = MOONSHOT_API_KEY`. OpenAI-compatible: **yes**.
  - Structured output: `UNKNOWN_PENDING_TRANSPORT_VALIDATION`. Plan for `json_object` +
    Section D in-prompt + `structured_output_limitation=true`; probe strict `json_schema` at
    validation. **If Moonshot rejects `json_object` without the literal token `json`** (historically
    true), append the existing `TRANSPORT_SERIALIZATION_ONLY` line `"Return the response as JSON."`
    **scoped to the Moonshot adapter only** — same rule as Qwen/DeepSeek, not parity propagation.
  - Reasoning: **mandatory** (`supports_thinking_type="only"`, `default_effort="max"`). Request
    `reasoning_effort`/`think_effort = "low"` if accepted (parity); never `high`/`max`. Record
    `reasoning_mode=mandatory` + `reasoning_comparability_flag=true`; do **not** compensate other
    candidates. Same handling class as `deepseek-v4-pro`.
  - `temperature=0` sent; omit-if-rejected fallback retained (Moonshot has constrained k-series
    temperature historically) — verify at transport validation.
  - Usage: `usage.prompt_tokens` / `completion_tokens` / `total_tokens`; reasoning-token path
    (`completion_tokens_details.reasoning_tokens`) PENDING. Latency: wall-clock, feasible.
  - **Adapter complexity: LOW** — the `QwenBenchmarkAdapter` / `DeepSeekBenchmarkAdapter` shape
    applies directly; the only addition is the mandatory-reasoning effort control.
- No production service modified. `MoonshotBenchmarkAdapter` lives under `backend/evals/scripts/`.
  `dashscope` / `google-genai` remain optional; `httpx` covers Moonshot too.

## FINAL transport-validation update (2026-09-01, attempt 3 — Section A + Section D)

- **Section D works.** With Section A (frozen semantics) + Section D (canonical output-field
  contract) in every request, `qwen3.8-max`, `qwen3.8-flash`, and `deepseek-v4-pro` each returned
  **exact** canonical top-level keys `{summary, requirement_matches, suggested_preparation}` and
  **exact** item keys `{requirement_id, match_label, evidence_ids, reason}` — zero aliases, zero
  extra keys, **no adapter-side semantic repair**. The attempt-2 alias problem
  (`match_level`/`match_status`/`match_grade`) is resolved. `_normalize_matches` still does not
  remap anything. `JSON_OBJECT_ONLY` + Section D in-prompt is sufficient; strict provider-native
  `json_schema` is an **optional** Round 1B probe, not required.
- **`QwenBenchmarkAdapter` — VALIDATED**: `response_format={"type":"json_object"}` + Section D +
  `"Return the response as JSON."` (Qwen scope) + `temperature=0` + `enable_thinking=false`. HTTP
  200, single-pass (`reasoning_tokens` null). Usage/latency captured.
- **`DeepSeekBenchmarkAdapter` — VALIDATED**: same shape (DeepSeek scope for the json line). HTTP
  200. `reasoning_mode=mandatory` re-confirmed (`reasoning_content` present, `reasoning_tokens=105`)
  → `reasoning_comparability_flag=true` permanent. Usage (incl. reasoning tokens) / latency captured.
- **`MoonshotBenchmarkAdapter` — BLOCKED on `temperature`**: `kimi-k3` returned **HTTP 400
  "invalid temperature: only 1 is allowed for this model"**. The **Opus-5 lesson repeats**:
  `temperature=0` (production's hard-set value) is rejected; `kimi-k3` mandates `temperature=1`.
  Adapter change required (eval-only): for `kimi-k3` send `temperature=1` (or omit `temperature`
  and take the model default), and record a `temperature_comparability_note` in
  `transport_metadata` — `kimi-k3` cannot be run at `temperature=0` like the others. The
  request failed at parameter validation **before** `reasoning_effort="low"` (the correct
  OpenAI-compatible param; metadata key `reasoning_efforts`, valid `low`/`high`/`max`, default
  `max`) or the JSON contract were evaluated, so both remain **unverified**. Per task rules this
  was **not** retried and the candidate was **not** substituted; a single explicitly-approved
  re-call is the next step.
- **`temperature` policy reaffirmed**: send `temperature=0` where accepted (Qwen ×2, DeepSeek —
  confirmed); where a model rejects it, adjust per that model's requirement and record it
  (`claude-opus-5` → omit; `kimi-k3` → `temperature=1`).

## `kimi-k3` re-validation update (2026-09-01, attempt 3b — 1 approved call)

- **`MoonshotBenchmarkAdapter` — VALIDATED.** `temperature=1` (`MODEL_REQUIRED_VALUE`) +
  `reasoning_effort="low"` + `response_format={"type":"json_object"}` + Section D in-prompt +
  `"Return the response as JSON."` (Moonshot scope) → **HTTP 200 PASS**.
- Canonical adherence **EXACT**: top-level `{summary, requirement_matches, suggested_preparation}`,
  item `{requirement_id, match_label, evidence_ids, reason}`, no aliases, no extras, **no
  adapter-side semantic repair**. `requirement_id` preserved; `match_label = "Strong"`;
  `evidence_ids = ["synthetic_ev_001"]`.
- `reasoning_effort="low"` **accepted** (HTTP 200, no parameter error; the API does not echo the
  effort back). `reasoning_mode = mandatory`: `reasoning_content` present, `reasoning_tokens = 170`.
- Usage in **636** / out **320** / reasoning **170** / total **956**. Latency **13,601.3 ms**
  (slowest of the pool — mandatory reasoning + Moonshot).
- **Round 1B adapter settings for `kimi-k3`** (eval-only): `temperature=1` (record
  `temperature_comparability_note` — every other candidate runs `temperature=0`), `reasoning_effort=
  "low"`, `response_format={"type":"json_object"}` + Section D + json-token line (Moonshot scope).
  `reasoning_comparability_flag = true`. Do not compensate other candidates.

## Cross-provider transport-validation — FINAL state (all four new candidates)

| model | adapter | transport | structured output | reasoning | temperature | verdict |
|---|---|---|---|---|---|---|
| `qwen3.8-max` | `QwenBenchmarkAdapter` | OpenAI-compat + json-token line | JSON_OBJECT_ONLY + Section D | single-pass (`enable_thinking=false`) | `0` accepted | **VALIDATED** |
| `qwen3.8-flash` | `QwenBenchmarkAdapter` | same | JSON_OBJECT_ONLY + Section D | single-pass | `0` accepted | **VALIDATED** |
| `deepseek-v4-pro` | `DeepSeekBenchmarkAdapter` | OpenAI-compat + json-token line | JSON_OBJECT_ONLY + Section D | **mandatory** (flag) | `0` accepted | **VALIDATED** |
| `kimi-k3` | `MoonshotBenchmarkAdapter` | OpenAI-compat + json-token line | JSON_OBJECT_ONLY + Section D | **mandatory**, effort `low` (flag) | **`1` required** (flag) | **VALIDATED** |
| `claude-sonnet-4-5-20250929` | existing `ClaudeStructuredClient` | `messages.parse` output_format | STRICT_SCHEMA | single-pass | `0` (production) | reference (reuse) |
