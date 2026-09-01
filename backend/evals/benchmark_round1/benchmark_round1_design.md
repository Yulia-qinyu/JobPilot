# JobPilot Evaluation — Benchmark Round 1: Fixed-Prompt Model Comparison (Design)

**Status: `design_ready`. This document is design only. Zero live LLM/API calls were made. No production code, prompt, Ground Truth, Dataset, candidate evidence, normalization, or Match Score was changed.**

---

## 1. Why this experiment exists

Baseline Error Analysis V1 concluded that **~93% of reconciled label errors trace *primarily* to the
prompt not communicating frozen rubric rules** (OR-list, project-vs-work, adjacency,
no-outcome-≠-downgrade, narrowest-unmet-subclaim). That is a **hypothesis, not a proven fact** — the
analysis could not separate "the prompt is under-specified" from "the model is not strong enough to
reason correctly even with the current wording".

Round 1 is the control that separates the two:

> At the **exact same** JobPilot semantic-matching contract (same prompt text, same schema, same
> temperature, same normalization, same scoring, same 100 frozen requirements, same 30-item evidence
> snapshot), **does changing only the underlying model** materially improve classification, OR-list
> reasoning, adjacency discrimination, project-vs-work reasoning, schema reliability, and Match Score
> ranking quality?

- If a stronger model closes most of the gap **with no prompt change** → the deficit is largely
  **model capability**; prompt work has a smaller ceiling.
- If no model materially improves under the current prompt → the deficit is largely
  **prompt/rule communication**, and the deferred Prompt/Rubric Communication Ablation is where the
  gains are.

## 2. What variable changes

**Exactly one:** the model identifier passed to `ClaudeStructuredClient` (a plain parameter;
`app/config.py` `Settings.claude_model`). No code path, prompt, or schema changes when the identifier
changes.

## 3. What stays fixed (control variables)

| variable | frozen value |
|---|---|
| Dataset | `job_match_eval_dataset_v1` (`3654d64c…b2b558`) |
| Ground Truth | `job-match-ground-truth-v2` (`52cda176…1ba050`, commit `1a31c8d`) |
| Matchable requirements scored | 100 (eligibility 42, knowledge 16, subjective — all excluded) |
| Candidate evidence | frozen `candidate_evidence_snapshot` (30 items, `resume_extracted` / `manual_confirmed`; `resume_hash a5c64e17…`) |
| Prompt semantics + text | `job-fit-v3-matchable-only`, byte-identical from `requirement_matcher.py` (`e99ed027…d19b`) |
| Response contract | `fit-analysis-wire-v2` / `FitAnalysisOutput` |
| Labels | `Strong` / `Partial` / `Missing` |
| Temperature | 0 |
| `max_tokens` | 4096 |
| Calls per job | 1 semantic call (production Phase-3 architecture); 30 calls / model |
| Normalization | production `FitAnalysisService._normalize_matches` (unchanged) |
| Deterministic scoring | production `MatchScoreService` (Critical 5 / Important 3 / Preferred 1; Strong 1.0 / Partial 0.5 / Missing 0.0; `round_half_up`; matchable only) |
| Evaluation join key | `(job_id, requirement_id)` — exact, no fuzzy/text join |

## 4. Why prompt tuning is deferred

Adding OR-list / adjacency / project-vs-work / narrowest-subclaim guidance to the prompt is the
**treatment** the whole pipeline is building toward — but if applied now it would confound the model
comparison (different candidates would effectively get different instructions). Round 1 answers
"which model under the *current* prompt", then a separate **Prompt/Rubric Communication Ablation**
runs `job-fit-v3` vs a rubric-aligned prompt **on the single selected model**.

## 5. Provider / model compatibility — what is actually available locally

Inspected `backend/requirements*.txt`, the installed venv, `backend/app/services/`, `backend/app/config.py`,
`.env` / `../.env`, and process environment.

| finding | detail |
|---|---|
| Providers implemented in code | **Anthropic only** — one client, `app/services/claude_client.py` (`ClaudeStructuredClient` → `anthropic` SDK `client.messages.parse(model=…, output_format=FitAnalysisOutput)`). |
| Installed LLM SDKs | **`anthropic 0.125.0` only.** No `openai`, `google-generativeai`, `vertexai`, `litellm`, `boto3`, `cohere`, `mistralai`. |
| Model configuration hook | `Settings.claude_model` (default `claude-sonnet-4-5-20250929`), override via `.env` `CLAUDE_MODEL` or a `Settings` copy. **Changing the model requires no code change and no matching-semantics change.** |
| Credentials present | `ANTHROPIC_API_KEY` only (in `.env`). **No** `OPENAI_API_KEY`, `GOOGLE_API_KEY` / `GEMINI_API_KEY`, `AWS_*`, `VERTEX_*`, `AZURE_OPENAI_*` anywhere. |
| Enumerating exact Anthropic model ids | The SDK exposes `client.models.list()` / `client.models.retrieve(id)`. **Not called in this design task** (would be a live API call). Execution Step 1 calls `models.list()` to resolve candidate slots to exact identifiers for this key. |
| Structured-output mechanics across providers | Anthropic: `messages.parse(output_format=<pydantic model>)`. OpenAI would use Structured Outputs (`response_format` JSON-schema). Gemini would use `response_schema` / function-calling. These are **transport/serialization only** and would each need an eval-only adapter — they do **not** change the semantic prompt. |
| Same prompt verbatim | Yes for any Anthropic model (identical code path). For OpenAI/Gemini the same **prompt string** is sent; only the schema-binding wrapper differs (documented as TRANSPORT_ONLY). |

**Conclusion on availability:** only **Anthropic** models are executable in Round 1. Exact
non-baseline Anthropic identifiers are **not verifiable offline** and are resolved at execution Step 1
via `client.models.list()`. Cross-provider comparison is **not available locally** and is deferred.

## 6. Recommended Round 1 candidate set

3–4 models total (screening, not a leaderboard):

| slot | model | live calls | rationale |
|---|---|---|---|
| **REFERENCE_BASELINE** | `claude-sonnet-4-5-20250929` | **0** (reuse `job_match_baseline_claude_current_v1_*`) | fixed anchor |
| **ANTHROPIC_HIGHER_TIER** | Opus-tier id from `models.list()` | 30 | is the Strong→Partial compression capacity-bound at the same prompt? |
| **ANTHROPIC_COST_EFFICIENT_TIER** | Haiku-tier id from `models.list()` | 30 | is a cheaper tier "good enough" under the same contract? |
| **ANTHROPIC_SAME_TIER_ALT_BUILD** *(optional)* | newest/distinct Sonnet id if present | 30 | within-tier / newer-build variation |

**Planned live calls: 60 (2 new candidates) or 90 (3 new candidates). Design task: 0.**

## 7. Models excluded and why

| model | reason |
|---|---|
| OpenAI GPT reasoning tier | no `openai` SDK installed; no `OPENAI_API_KEY`. Needs SDK + credentials + eval-only adapter (design in §12). Deferred. |
| Gemini | no `google-generativeai` / `vertexai` SDK; no Google credentials. Same as above. Deferred. |
| Any specific dated non-baseline Anthropic id | not verifiable offline; must not be invented. Resolved at execution Step 1. |

## 8. Primary metric & quality gates

**Primary model-selection metric: Macro F1 on the 100 frozen matchable requirements** (reconciled
predictions). Reported alongside a **co-primary system metric: Effective Correct Coverage**
= `(correct AND successfully normalized) / 100`, so a model with strong F1 but poor schema
reliability cannot look artificially good.

### Hard gates (all must pass to remain a candidate)

| gate | threshold | baseline | justification |
|---|---|---|---|
| Macro F1 | ≥ **0.75** | 0.692 | +0.058 ≈ the "meaningful" band; below this, not worth switching |
| Effective Correct Coverage | ≥ **0.75** | 0.62 | protects against high-F1 / low-schema-reliability models |
| Grounding Rate | ≥ **0.98** | 1.000 | evidence safety must not regress |
| Unsupported Match Rate | ≤ **0.02** | 0.000 | no fabricated / mis-cited evidence |
| No catastrophic schema pattern | job normalization ≥ 28/30 **and** no systematic id duplication/omission (>1 job lost = fail) | 29/30 | 1 lost job is the baseline ceiling; a candidate that loses 2+ fails |

### Strong/Partial trade-off gate (all must pass — a candidate is **not** "improved" if Strong recall rises while precision collapses)

| metric | threshold | baseline |
|---|---|---|
| Strong recall | ≥ **0.75** | 0.630 |
| Strong precision | ≥ **0.80** | 0.879 |
| Partial precision | ≥ **0.60** | 0.477 |
| Missing recall | ≥ **0.667** (no regression) | 0.667 |
| Strong→Partial errors | **< 17** | 17 |
| Missing→Partial errors | **≤ 6** (must not increase while fixing Strong→Partial) | 6 |

### Schema reliability (preferred, not gating in Round 1)

30/30 normalized jobs and 100/100 requirement coverage are **preferred**. A single-run zero-error
result does **not** prove reliability — repeat-run robustness is a later round. Record every schema
failure per model regardless.

### Improvement bar vs baseline Macro F1 0.692

`< +0.02` noise · `+0.02–0.05` small · `+0.05–0.10` meaningful · `≥ +0.10` large.
**Round 1 is screening, not statistical proof:** Dataset V1 is 100 rows / 30 jobs, single run,
class-imbalanced (52 / 30 / 18). Treat a lone `+0.02–0.05` as suggestive, not confirmed.

## 9. Classification metrics (per model, GT fixed)

Accuracy · Macro P / R / F1 · per-class P / R / F1 for Strong, Partial, Missing · 3×3 confusion
matrix (GT rows × Prediction cols) · the 6 directional transition counts.

## 10. System reliability metrics (per model)

raw schema parse success · job normalization success · requirement prediction coverage · Effective
Correct Coverage · duplicate requirement ids · omitted requirement ids · hallucinated requirement ids
· invalid evidence ids · invalid labels · retry count · complete job success rate.

## 11. Grounding metrics (per model)

Grounding Rate · Unsupported Match Rate · Evidence ID validity rate · Strong/Partial zero-evidence
rate · Missing-with-evidence anomaly rate. **Grounding is a safety/reliability dimension, not a
substitute for semantic correctness** — Baseline V1 had grounding 1.000 while 27/27 wrong
Strong/Partial predictions still cited only valid evidence.

## 12. Cross-provider adapter (design only — not built)

If the user later approves cross-provider comparison, an **eval-only** adapter lives at
`backend/evals/scripts/eval_structured_client_<provider>.py` and implements the same surface as
`ClaudeStructuredClient.generate(prompt, output_model, tool_name)`:

- **OpenAI**: `client.chat.completions.parse(model=…, messages=[{"role":"user","content":prompt}],
  response_format=FitAnalysisOutput, temperature=0, max_tokens=4096)` (Structured Outputs). The
  `prompt` string is unchanged; only the schema binding differs → **TRANSPORT_ONLY**.
- **Gemini**: `model.generate_content(prompt, generation_config={"response_mime_type":"application/json",
  "response_schema": <FitAnalysisOutput json schema>, "temperature":0, "max_output_tokens":4096})`.
  Same prompt string → **TRANSPORT_ONLY**.

Rules: no semantic guidance added; the adapter maps provider output back into `FitAnalysisOutput`
and then hands off to the **unchanged** production `_normalize_matches`. All provider-specific
mechanics are logged in `benchmark_round1_manifest.json` as `transport_serialization_only`. **No
production code is modified** — the adapter is import-only under `backend/evals/`.

## 13. How schema failures are handled

A candidate's raw output per job is persisted **before** any Ground Truth is loaded. Then production
`_normalize_matches` runs unchanged. If it raises (id-set violation), that whole job is `unreconciled`
and its requirements count as `omitted` in Effective Correct Coverage — exactly as Baseline V1
treated `tencent:2047239002926510080`. No eval-side repair, no extra retries beyond the production
Anthropic SDK default.

## 14. How Match-Score quality is measured

Per model, per job (excluding any unscorable job): deterministic **Model Match Score** (production
`MatchScoreService`, model-predicted importance × model label). Compared against:

- **A. GT Match Score** (frozen canonical importance × Human label) — same construct, isolates label
  error: MAE, median abs err, max err, jobs diff ≥ 20, jobs diff ≥ 30, Spearman(Model, GT).
- **B. Human Match Fit** (1–5 ordinal): Spearman(Model score, HMF).

Fixed reference points (from Baseline V1 analysis, do not recompute): GT Match Score vs Human Match
Fit **Spearman 0.845**; Baseline Match Score vs Human Match Fit **0.537**; GT vs Baseline score
**0.707**. A better model should move (B) toward 0.845.

## 15. How slices are evaluated

Slices are **reproduced from Baseline V1 artifacts, not re-derived** — the per-requirement flags
already exist in `job_match_baseline_claude_current_v1_error_slices.csv` and
`…_score_analysis.csv`, plus Dataset V1 `role_category`. For each slice, per model: n · accuracy ·
Macro F1 (only if slice n ≥ 12, else counts only) · error count · directional error breakdown.

**Key slice hypotheses to test (not to fix):**

- **OR-list** (n = 18, baseline accuracy **0.44**): does a stronger model recognise that one satisfied
  allowed alternative is enough (fewer Strong→Partial in OR rows) **without** crediting
  adjacent-but-unsatisfied alternatives (no more Missing→Partial in OR rows)? Report OR-list
  accuracy, Strong→Partial-within-OR, Missing→Partial-within-OR.
- **Technology adjacency** (baseline: 5/6 GT-Missing→Partial adjacency-driven): report technology-
  adjacency false-positive count, especially GT Missing → predicted Partial/Strong.
- **Project-vs-work** (baseline: 6 under-credited, 8 over-credited): report **both** directions. A
  better model distinguishes "direct project / productization evidence" from "formal-role / senior
  professional experience requirement" **without a single universal rule**.
- **Small-matchable jobs** (≤ 3 requirements) and **one-requirement jobs**: report per-job score
  volatility — this is a scoring/UX artifact, tracked but not a model gate.
- **Mismatched-control jobs**: sanity check that a stronger model does not "over-cover" a role the
  candidate is structurally wrong for.

## 16. Key failure-direction test (central trade-off)

For every candidate: the full 6-transition matrix. The benchmark **explicitly tests whether a
stronger model reduces `Strong→Partial` (17) without increasing `Missing→Partial` (6)**. A model that
merely shifts the compression the other way (more Missing→Partial, fewer Strong→Partial) does **not**
pass the Strong/Partial trade-off gate.

## 17. Latency / token / cost design

Per model: total wall time · total model latency · mean / median / P90 / min / max latency per job ·
input / output / total tokens · avg tokens per job · avg tokens per requirement. **Cost**: no pricing
in repo config and no web lookup permitted → record `COST_PENDING_EXTERNAL_PRICING_LOOKUP` and report
token usage only. A later explicit pricing task converts tokens → cost.

## 18. Baseline reuse & single-run policy

- **Reference model `claude-sonnet-4-5-20250929` is NOT rerun.** Its metrics come from
  `job_match_baseline_claude_current_v1_*` (frozen). Rerun-all only if a fairness defect is identified
  and explicitly approved (none identified).
- **One run per new candidate**, temperature 0. **No repeat trials in Round 1** — variance
  measurement is a later round.

## 19. Dataset V1 is now development data — explicit warning

Ground Truth has been inspected, baseline errors analysed, and failure slices designed from observed
errors. **Dataset V1 is now a development / model-selection benchmark set.** Any improvement measured
in Round 1 (or the later prompt ablation) **must not** be presented as unbiased final test
performance.

## 20. Dataset V2 held-out policy

A **held-out Dataset V2** is required for unbiased validation of whatever model + prompt Round 1 and
the ablation select. Dataset V2 should: prioritise campus / new-grad full-time roles; increase
company diversity (Baseline V1 is 87% Tencent + Baidu); broaden requirement-type distribution;
retain internship / experienced / mismatched controls. **It must not be inspected before it is used
as a test set.**

## 21. Contamination control

Model inputs may contain **only**: the frozen matchable `requirement_id` + `normalized_requirement`
+ `source_text` (as context), the frozen 30-item candidate evidence snapshot, and the unchanged
`job-fit-v3` prompt + `fit-analysis-wire-v2` schema. Model inputs must **never** contain any human
label / eligibility status / evidence adjudication / Human Match Fit / human notes / error-analysis
bucket / slice name / known failure case / OR-list / project-vs-work / adjacency human decision /
GoFin manual facts / any Ground Truth. **Ground Truth is loaded only after every raw prediction for a
candidate is persisted to disk.**

## 22. No implementation in this task

No multi-provider adapter was built. No benchmark runner was created (it is fully specified in
`benchmark_round1_execution_plan.md`; it will reuse the proven input-construction from
`backend/evals/scripts/run_current_claude_baseline_v1.py`, changing only the model identifier and
output directory). No production code touched.

---

## Deliverables created by this design task

| file | purpose |
|---|---|
| `benchmark_round1_manifest.json` | machine-readable pre-registration: fixed variables, candidates, metrics, gates, policies |
| `benchmark_round1_design.md` | this document |
| `benchmark_round1_candidate_matrix.csv` | provider/model rows with availability, adapter needs, planned calls, cost status |
| `benchmark_round1_execution_plan.md` | the exact 12-step run protocol |

Execution-time output files (`benchmark_round1_metrics.*`, `…_predictions_<slug>.*`,
`…_job_scores.csv`, `…_slice_metrics.csv`, `…_errors.csv`, `…_latency_tokens.csv`,
`…_model_comparison.md`) are **not** created here.

**Benchmark Round 1 design completed. No live benchmark calls made. Ready for candidate approval before execution.**
