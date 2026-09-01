# Cross-Provider Model Screening — Execution Plan (Round 1B)

**Do NOT execute until credentials are set and exact model identifiers are resolved and approved.**
Design only. Each new model = 30 live calls. Max new inference = **5 × 30 = 150**. Reference Sonnet:
**0** (reuse Round 1A / Baseline V1). OpenAI: excluded.

Runner: a new eval-only script `backend/evals/scripts/run_cross_provider_benchmark.py` that reuses the
proven input construction of `run_benchmark_round1.py` (EvidenceCatalog from the frozen snapshot;
per-job RequirementCatalog of frozen matchable requirements; production `_normalize_matches` +
`MatchScoreService`) and swaps the `RequirementMatcher` call for a `BenchmarkModelAdapter`
(see `cross_provider_adapter_design.md`). No production code is modified.

---

## Step 1 — Resolve credentials  ✅ DONE (2026-09-01)
> `GEMINI_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY` all **present**. `OPENAI_API_KEY` absent (excluded).
- Read `.env` / env for `GEMINI_API_KEY` (or the Vertex path), `DASHSCOPE_API_KEY` + region base URL,
  `DEEPSEEK_API_KEY`. **Values never printed.**
- Any provider without a credential is marked `not_ready` and dropped from this run (not a failure).
- Confirm `OPENAI_API_KEY` is **not** requested and OpenAI is skipped.

## Step 2 — Verify exact model availability (metadata only, no inference)  ✅ DONE (2026-09-01)
> Gemini model-list 200 (52); DeepSeek model-list 200 (3); Qwen mainland model-list 200 (249; intl 401). Resolved: `gemini-3.7-flash`, `gemini-3.5-flash-lite`, `qwen3.8-max`, `qwen3.8-flash`, `deepseek-v4-pro`. See `cross_provider_resolved_models.json`.
- Gemini: `GET /v1beta/models` (or `google-genai` `client.models.list()`). Record every returned id.
- Qwen: OpenAI-compatible `GET {BASE}/models` (or the Model Studio catalogue). Record ids + region.
- DeepSeek: OpenAI-compatible `GET https://api.deepseek.com/models`. Record ids.
- Map each `PENDING_PROVIDER_VERIFICATION` slot to a concrete id per its role (HIGH_CAPABILITY /
  COST_QUALITY / HIGH_VALUE). Slots with no viable id are dropped.
- **These are metadata/auth calls, not inference — they generate no model response and incur no
  benchmark token usage. Record each probe.**

## Step 3 — Verify structured-output support (metadata / spec only)
- For each resolved model, confirm the transport it will use for Section D:
  strict JSON Schema (`responseSchema` / `response_format json_schema`) vs `json_object` fallback.
- Where only `json_object` is available, set `structured_output_limitation=true` for that model and
  plan to measure schema reliability (parse success, invalid labels, id-set violations).
- Confirm whether `temperature` is accepted; if rejected/deprecated, plan to omit it and record it
  (the Opus 5 lesson).
- Confirm reasoning mode: standard single-pass; no thinking budget / no `enable_thinking` / no
  mandatory-CoT model unless it *is* the chosen model (then record `reasoning_mode=mandatory`).

## Step 4 — Implement eval-only adapters
- `GeminiBenchmarkAdapter`, `QwenBenchmarkAdapter`, `DeepSeekBenchmarkAdapter` under
  `backend/evals/scripts/` per `cross_provider_adapter_design.md`. `AnthropicBenchmarkAdapter` wraps
  the existing client (reference; not called in 1B).
- Adapters assemble Sections A + B + C, request Section D, map output into `FitAnalysisOutput`, and
  hand off to the **unchanged** `_normalize_matches`. No semantic fields are adapter-filled.
- Assert: no file under `backend/app/`, `backend/alembic/`, `frontend/` changed.

## Step 5 — Offline prompt-parity validation (no inference)
- For every resolved model, construct the full request and assert Section A text is byte-identical to
  `cross_provider_prompt_parity.md` §A (diff each provider's assembled prompt → A must match exactly).
- Assert B/C payloads match the frozen matchable requirements and the 30-item evidence snapshot.
- Assert the only per-provider differences are system/user split, the shared JSON-mandate line,
  schema-binding kind, omitted `temperature` — all logged as `TRANSPORT_SERIALIZATION_ONLY`.

## Step 6 — Dry-run request construction (no inference)
- Print the assembled request for job 1 for each provider for visual confirmation. **No API call.**

## Step 7 — Approve final candidate IDs
- Present the resolved model list (provider, exact id, role, transport, reasoning mode, structured-
  output kind, pricing status) for explicit approval before any 30-call run.

## Step 8 — Run one provider/model at a time
- Sequential, never interleaved. For each model: 30 jobs, one non-streaming structured call per job,
  `temperature=0` where accepted (else omitted + recorded), SDK/httpx default retries only.
- Output dir: `backend/evals/benchmark_cross_provider/`. Slug = `<provider>-<sanitised-model-id>`.

## Step 9 — Persist raw predictions BEFORE Ground Truth load
- `cross_provider_predictions_<slug>.json` incrementally: submitted requirements, submitted evidence,
  provider, model id, request timestamp, **raw provider response** (secrets stripped),
  `parsed_output`, `transport_metadata`, latency, token usage (normalised), schema-parse success,
  retry count, error.
- **Ground Truth file is not opened during Steps 8–9.**

## Step 10 — Normalize (production, unchanged)
- `FitAnalysisService._normalize_matches(parsed_output, catalog, evidence)` per job; record
  normalization success / `FitAnalysisNormalizationError`.
- Per-job deterministic `MatchScoreService.score(normalized)` (skip failed-normalization jobs).

## Step 11 — Load frozen Ground Truth (only now)
- Open `job_match_annotation_full_v2_human_verified.json`; assert SHA-256
  `52cda176e166146ffc24a85067f13618c5f717cedab506f0ba17fe5e701ba050`.
- Build `(job_id, requirement_id) → {human_match_label, human_evidence_ids, importance, human_match_fit}`.

## Step 12 — Compute identical metrics
- Reuse the metric code of `run_benchmark_round1.py` / `compare_benchmark_round1.py` verbatim:
  Accuracy, Macro P/R/F1, per-class P/R/F1, confusion matrix, 6 directional transitions,
  raw parse success, normalization success, requirement coverage, **Effective Correct Coverage**,
  duplicate/omitted/hallucinated ids, invalid labels, invalid evidence ids,
  Grounding Rate, Unsupported Match Rate, Evidence-ID validity, Strong/Partial-zero-evidence,
  Missing-with-evidence, Match Score MAE vs GT score, Spearman(model score, GT score),
  Spearman(model score, Human Match Fit).

## Step 13 — Generate slice metrics
- Load the **pre-registered** slice flags from
  `backend/evals/job_match_baseline_claude_current_v1_error_slices.csv` +
  `…_score_analysis.csv` + Dataset V1 `role_category`. **Do not redefine slices after seeing 1B
  results.** Per slice × model: n, accuracy, Macro F1 (only if slice n ≥ 12), error count,
  directional breakdown. Plus the Chinese-JD subset (27 jobs) as a first-class slice.

## Step 14 — Latency / token / verified cost
- Per model: total wall, mean/median/P90/min/max latency; input/output/total tokens; avg/job;
  avg/requirement. Cost = tokens × **officially verified** provider pricing (see manifest
  `pricing_status`); any unverified rate → `PENDING_OFFICIAL_PRICING_VERIFICATION`, tokens only.

## Step 15 — Build the Pareto frontier
- Plot models on QUALITY (Macro F1, Strong recall, Partial precision, Missing recall) × RELIABILITY
  (ECC, coverage, schema, grounding) × EFFICIENCY (latency, cost/job) × PRODUCT FIT (Chinese-JD
  subset F1, provider operational complexity). Mark dominated vs non-dominated models. **No weighted
  composite score.**

## Step 16 — Select Top 3
- From the non-dominated set, considering the reference (Sonnet 4.5) and Round 1A (Haiku 4.5). Record
  the rationale per axis. Do not promote any model to production from Round 1B.

## Step 17 — Run deeper benchmark / Prompt Ablation
- Deeper: repeat runs (variance) on the Top 3.
- Prompt/Rubric Communication Ablation: `job-fit-v3` vs a rubric-aligned prompt on the Top 1–2 models.
- Then Dataset V2 held-out validation → final production model selection / routing decision.

---

## Guardrails during execution
- 0 OpenAI calls, 0 OpenAI config. Only Gemini / Qwen / DeepSeek (+ reused Anthropic reference).
- No prompt / schema / normalization / scoring / Ground Truth / Dataset / evidence change.
- No production code change — adapters are eval-only under `backend/evals/`.
- No repeat trials in Round 1B (deferred). No batching change. No eval-added retries.
- Ground Truth loaded only after raw persist. No human labels / adjudication notes / slice names in
  any model input.
- No `git add` / `commit` / `push` without explicit instruction. `README.md` untouched.

---

## Transport-validation update (2026-09-01) — 0/5 candidates passed; a targeted re-validation is needed BEFORE Step 4

Smoke test (5 synthetic calls, 0 tokens billed) outcomes:
- `gemini-2.5-pro` — HTTP 404, not callable by this credential. **Slot needs re-approval** (`gemini-3.1-pro-preview` or `gemini-3.7-flash`).
- `gemini-3.7-flash` — HTTP 503 transient. Re-validate 1 call.
- `qwen3.8-max` / `qwen3.8-flash` — HTTP 400: DashScope `json_object` mode requires the token `json` in `messages`. **Transport-only fix**: `QwenBenchmarkAdapter` appends the minimal `"Return the response as JSON."` line (`TRANSPORT_SERIALIZATION_ONLY`). Re-validate.
- `deepseek-v4-pro` — HTTP 402 Insufficient Balance. **User must fund the DeepSeek account.** Re-validate after funding.

### Step 3b — Re-run transport smoke test (blocking gate; <= 5 synthetic calls)
1. Confirm the approved Gemini HIGH_CAPABILITY id.
2. Confirm the DeepSeek account has balance.
3. Apply the Qwen adapter `json`-token serialization line.
4. Re-run one synthetic call per still-unvalidated candidate. Require all pass criteria (Section 11 of the manifest / transport_validation.md).
5. Only when all five candidates transport-validate -> manifest `status = transport_validation_complete`, then Steps 4-17 proceed on explicit Round 1B execution approval.

### Step 3b — RE-VALIDATION attempt 2 (2026-09-01): still 0/5; a THIRD targeted re-validation is needed

Pool change applied: `gemini-2.5-pro` removed (HTTP 404) → `gemini-3.1-pro-preview` (preview;
`operational_stability_flag=true`). DeepSeek account funded (`GET /user/balance` → `is_available=true`).
Qwen `json`-token line applied.

Attempt-2 outcomes (5 synthetic calls, 1,896 tokens billed on the 3 HTTP-200 calls, 0 retries):
- `gemini-3.1-pro-preview` — **HTTP 429 RESOURCE_EXHAUSTED**: Gemini/AI Studio prepayment credits
  depleted. **User must fund the Gemini account.** Blocks BOTH Gemini candidates.
- `gemini-3.7-flash` — **HTTP 429** same account. (Attempt-1 503 was transient.)
- `qwen3.8-max` / `qwen3.8-flash` — **HTTP 200**. `json`-token fix works; `requirement_id` preserved;
  usage + latency captured. **Gap**: minimal smoke prompt omitted Section D → label keys
  `match_level` / `match_status`.
- `deepseek-v4-pro` — **HTTP 200**. Account funded; `json`-token line works; `requirement_id`
  preserved. **Gap**: label key `match_grade`. **`reasoning_mode = mandatory`** confirmed
  (`reasoning_tokens=408`, `reasoning_content` present) — permanent comparability flag into Round 1B.

### Step 3c — THIRD transport re-validation (blocking gate; <= 5 synthetic calls)
1. **User funds the Gemini / AI Studio account** (HTTP 429 — blocks both Gemini candidates).
2. Update the smoke harness to assemble **Section A + Section D** (the fixed output-field contract,
   identical wording for every provider — no semantic content) and bind strict `json_schema` where
   the provider supports it (Gemini `responseSchema`; Qwen/DeepSeek `response_format` `json_schema`
   if accepted, else `json_object` + Section D in-prompt + `structured_output_limitation=true`).
3. Re-run one synthetic call per still-unvalidated candidate (≤ 5). Require the FULL §10 pass bar:
   canonical field names obtainable with **no adapter-side semantic repair**.
4. Only when all five pass → manifest `status = transport_validation_complete`,
   `candidate_resolution_complete = true`, `benchmark_execution_approved = false`; then Steps 4–17
   proceed on explicit Round 1B execution approval.
5. `deepseek-v4-pro` carries `reasoning_mode = mandatory` into Round 1B; do not compensate other
   candidates with a high-compute mode.

## Candidate-pool update (2026-09-01) — Gemini excluded, Kimi added; NEW pool = 4 new candidates, 120 max calls

- **Gemini ×2 → `EXCLUDED_BY_USER_OPERATIONAL_COST_POLICY`** (user instruction; also historically
  HTTP 429 prepay-depleted). Do NOT re-enable, do NOT request Gemini billing, do NOT re-probe Gemini.
  All Gemini transport records (attempt 1 HTTP 404/503, attempt 2 HTTP 429) are PRESERVED in the
  manifest and `cross_provider_transport_validation.{json,md}`.
- **+ `KIMI_CHINESE_HIGH_CAPABILITY = kimi-k3` (Moonshot AI)** — candidate RESOLVED via non-inference
  model-list only (`GET https://api.moonshot.cn/v1/models` → HTTP 200, 4 models). `MOONSHOT_API_KEY`
  present. OpenAI-compatible. Adapter complexity LOW. Reasoning **mandatory**
  (`supports_thinking_type="only"`) → `reasoning_comparability_flag=true`. Structured output
  `UNKNOWN_PENDING_TRANSPORT_VALIDATION`. Pricing PENDING. **0 Kimi inference calls.** See
  `cross_provider_candidate_replacement.md`.
- **Round 1B new-candidate pool is now**: `qwen3.8-max`, `qwen3.8-flash`, `deepseek-v4-pro`,
  `kimi-k3` (+ reference `claude-sonnet-4-5-20250929`, 0 calls). Max new inference **4 × 30 = 120**.

### Step 3d — Kimi transport validation (blocking gate for the Kimi slot; part of the Step 3c re-validation, ≤ 5 synthetic calls total)
1. Assistant/user approves the exact Kimi model (`kimi-k3`).
2. Assemble synthetic **Section A + Section D** (synthetic requirement `synthetic_req_001` / evidence
   `synthetic_ev_001` only — no Dataset V1, no Ground Truth, no real evidence).
3. One synthetic `POST /v1/chat/completions` call: `response_format={"type":"json_object"}`,
   `temperature=0`, `reasoning_effort="low"` if accepted. If HTTP 400 for a missing `json` token,
   one narrowly-justified retry with the `TRANSPORT_SERIALIZATION_ONLY` line (Moonshot adapter
   scope), else report the blocker.
4. Record: HTTP status, structured-output class (STRICT_SCHEMA_SUPPORTED / JSON_OBJECT_ONLY /
   STRUCTURED_OUTPUT_LIMITED), `requirement_id` preservation, `match_label` enum, `evidence_ids`
   representation, `reasoning_mode` + reasoning tokens, `temperature` acceptance, usage, latency.
5. Kimi passes on the same §10 bar as the others. `reasoning_mode=mandatory` carries into Round 1B;
   do not compensate other candidates.
6. `benchmark_execution_approved` stays `false` until every retained candidate passes and the user
   explicitly approves Round 1B.

## FINAL transport-validation gate (2026-09-01, attempt 3) — 3/4 passed; kimi-k3 blocked on temperature

Prompt: **Section A + Section D** (canonical output-field contract, output-contract-only). 4 calls,
0 retries, 2,190 tokens billed. Gemini excluded — not queried, not called.

| model | result |
|---|---|
| `qwen3.8-max` | **PASS** — HTTP 200; exact canonical top-level + item fields; no aliases; req_id preserved; `match_label "Strong"`; `evidence_ids` list; `reason` string; single-pass; usage in=539/out=146; latency 3608.9 ms |
| `qwen3.8-flash` | **PASS** — HTTP 200; same; usage in=539/out=133; latency 2226.4 ms |
| `deepseek-v4-pro` | **PASS** — HTTP 200; same; `reasoning_mode=mandatory` (reasoning_tokens=105); usage in=612/out=221/reasoning=105; latency 4888.6 ms |
| `kimi-k3` | **FAIL / TRANSPORT_BLOCKED** — HTTP 400 `"invalid temperature: only 1 is allowed for this model"`. `temperature=0` rejected; requires `temperature=1` (Opus-5 class). Blocked before `reasoning_effort="low"` / JSON contract evaluated. NOT retried, NOT substituted. |

**Section D eliminated the attempt-2 alias problem** — the three HTTP-200 models produced the exact
canonical field names with no adapter-side semantic repair.

### Step 3e — kimi-k3 temperature re-validation (blocking gate for the Kimi slot; ONE approved synthetic call)
1. Approve `kimi-k3` temperature handling: send `temperature=1` (record `temperature_comparability_note`) **or** omit `temperature`.
2. One synthetic **Section A + Section D** `POST /v1/chat/completions`: `response_format={"type":"json_object"}`, `reasoning_effort="low"`, `"Return the response as JSON."` (Moonshot scope), plus the approved temperature handling.
3. Record: HTTP status; whether `reasoning_effort="low"` is accepted (and `observed_reasoning_effort` if returned); structured-output class; canonical top-level + item field adherence; `requirement_id` preservation; `match_label` enum; `evidence_ids` list; `reason` string; usage (incl. reasoning tokens); latency. Pass on the §15 bar.
4. Only when `kimi-k3` also passes → manifest `status = transport_validation_complete`, `candidate_resolution_complete = true`, `benchmark_execution_approved = false`; then seek explicit Round 1B execution approval.
5. `deepseek-v4-pro` and `kimi-k3` carry `reasoning_comparability_flag = true` into Round 1B; do not compensate other candidates.

### Round 1B new-candidate pool (unchanged count): `qwen3.8-max`, `qwen3.8-flash`, `deepseek-v4-pro`, `kimi-k3` (+ reference `claude-sonnet-4-5-20250929`, 0 calls). Max new inference **4 × 30 = 120**.

## Step 3e RESOLVED — `kimi-k3` re-validation (2026-09-01, attempt 3b, 1 approved call): **PASS**

`temperature=1` (`MODEL_REQUIRED_VALUE`) + `reasoning_effort="low"` + Section A + Section D →
**HTTP 200 PASS**. Exact canonical top-level + item fields, no aliases, no adapter semantic repair.
`requirement_id` preserved; `match_label "Strong"`; `evidence_ids ["synthetic_ev_001"]`.
`reasoning_effort="low"` accepted; `reasoning_mode=mandatory` (`reasoning_tokens=170`,
`reasoning_content` present). usage in=636/out=320/reasoning=170/total=956; latency 13,601.3 ms.

### Transport-validation gate — COMPLETE

| model | verdict |
|---|---|
| `qwen3.8-max` | TRANSPORT_VALIDATED (attempt 3) |
| `qwen3.8-flash` | TRANSPORT_VALIDATED (attempt 3) |
| `deepseek-v4-pro` | TRANSPORT_VALIDATED (attempt 3); `reasoning_comparability_flag=true` |
| `kimi-k3` | TRANSPORT_VALIDATED (attempt 3b); `reasoning_comparability_flag=true` + `temperature_comparability_flag=true` (`temperature=1`) |

Manifest: `status = transport_validation_complete`, `candidate_resolution_complete = true`,
`benchmark_execution_approved = false`. **Round 1B is NOT started — awaiting explicit approval.**
On approval, Steps 4–17 proceed: implement the four eval-only adapters, offline prompt-parity
assertion (Section A byte-identical + Section D identical for all four; per-provider differences =
json-token line + `enable_thinking=false` (Qwen) + `reasoning_effort="low"` (Kimi) +
`temperature=1` (Kimi) — all `TRANSPORT_SERIALIZATION_ONLY` / transport-parameter), then one
provider/model at a time, 30 jobs each, raw persist before Ground Truth load.
