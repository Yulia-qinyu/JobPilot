# Benchmark Round 1 — Execution Plan (Fixed-Prompt Model Comparison)

**Do NOT execute until candidate models are approved.** This plan is the pre-registered protocol.
Each new Anthropic candidate = 30 live calls. Reference model is reused (0 calls).

Runner: a new eval-only script `backend/evals/scripts/run_benchmark_round1.py` that **reuses the
input construction of `run_current_claude_baseline_v1.py` verbatim** (EvidenceCatalog from the frozen
snapshot; per-job RequirementCatalog of frozen matchable `ScoredRequirement`s; production
`RequirementMatcher` + `_normalize_matches` + `MatchScoreService`) and changes **only** (a) the model
identifier passed to `ClaudeStructuredClient` and (b) the output directory. No production code is
modified.

---

## Step 1 — Validate candidate availability

- Run `anthropic.Anthropic(api_key=<env>).models.list()` **once**. Record the full returned id list
  into `benchmark_round1_manifest.json → resolved_models`.
- Map each `RESOLVE_AT_EXECUTION__*` slot to a concrete id:
  - `ANTHROPIC_HIGHER_TIER` → the Opus-tier id (drop the slot if none).
  - `ANTHROPIC_COST_EFFICIENT_TIER` → the Haiku-tier id (drop if none).
  - `ANTHROPIC_SAME_TIER_ALT_BUILD` → a Sonnet id ≠ `claude-sonnet-4-5-20250929` (skip if none).
- Confirm cross-provider slots remain `NOT_AVAILABLE_LOCALLY` (no SDK/credentials). Do not attempt.
- **Gate:** proceed only with `claude-sonnet-4-5-20250929` (reference) + 2–3 resolved Anthropic ids.
  Present the resolved list for approval before any 30-call run.

## Step 2 — Validate no prompt semantic drift

- Assert `RequirementMatcher.PROMPT_VERSION == "job-fit-v3-matchable-only"` and
  `SCHEMA_VERSION == "fit-analysis-wire-v2"`.
- Assert `sha256(requirement_matcher.py) == e99ed02728452d6f50b39867a6dbf5e5a79e0fb9d78b610d66297f5d6a1ad19b`
  and `sha256(claude_client.py) == 76d953c4ae852502c0c85b16a53f1f8fcaeb3a7f39c791ff1776a3ed0b729b81`.
- Assert the runner sends the identical prompt string for every model (diff the constructed prompt
  across model slots → must be byte-identical).
- **Gate:** any mismatch aborts the run.

## Step 3 — Dry-run input construction only (no model call)

- Build the `EvidenceCatalog` from the frozen `candidate_evidence_snapshot`; assert 30 items and
  `{source_type}:{source_id}` == each `evidence_id`.
- Build all 30 per-job `RequirementCatalog`s from the frozen matchable rows; assert 100 total
  `ScoredRequirement`s, `source_kind == "v2_matchable"`, `importance_hint` ∈ {high, medium, low}.
- Assert `requirement_id` values match the frozen `(job_id, requirement_id)` keys exactly.
- Print the constructed request payload for job 1 for visual confirmation; **make no API call.**

## Step 4 — Run one candidate at a time

- For the approved model list, run models **sequentially** (never interleave). For each model:
  30 jobs, one `RequirementMatcher.analyze(catalog, evidence)` call per job, temperature 0,
  `max_tokens 4096`, production Anthropic SDK default retries only.
- Model slug = sanitised identifier (e.g. `claude-opus-…`). Output dir:
  `backend/evals/benchmark_round1/`.

## Step 5 — Persist raw response BEFORE Ground Truth load

- Write `benchmark_round1_predictions_<slug>.json` incrementally: per job — submitted requirement
  ids, submitted evidence catalog, model id, request timestamp, **raw parsed model output**,
  latency, input/output tokens, schema-parse success, error.
- **Ground Truth file is not opened during Steps 4–5.**

## Step 6 — Normalize (production, unchanged)

- For each job, run `FitAnalysisService._normalize_matches(raw_output, catalog, evidence)`.
- Record: normalized matches, `unsupported_evidence_count`, `hard_downgrade_count`,
  `deterministic_adjustment_count`, and any `FitAnalysisNormalizationError` (→ job unreconciled,
  its requirements `omitted`).
- Compute per-job deterministic Match Score via `MatchScoreService.score(normalized)` (skip if the
  job failed normalization).

## Step 7 — Load Ground Truth (only now)

- Open `job_match_annotation_full_v2_human_verified.json`; assert SHA-256
  `52cda176e166146ffc24a85067f13618c5f717cedab506f0ba17fe5e701ba050`.
- Build `(job_id, requirement_id) → {human_match_label, human_evidence_ids, importance,
  human_match_fit}`.

## Step 8 — Compute metrics (per model)

- Join predictions ↔ GT on `(job_id, requirement_id)` exactly. Record reconciled / unreconciled.
- Classification: Accuracy, Macro P/R/F1, per-class P/R/F1 (Strong/Partial/Missing), 3×3 confusion
  matrix, 6 directional transition counts.
- System: raw parse success, job normalization success, requirement coverage, **Effective Correct
  Coverage** = correct-and-normalized / 100, duplicate/omitted/hallucinated ids, invalid labels,
  invalid evidence ids, retry count, complete job success rate.
- Grounding: Grounding Rate, Unsupported Match Rate, Evidence-ID validity rate, Strong/Partial
  zero-evidence rate, Missing-with-evidence anomaly rate.
- Score quality: GT Match Score (frozen importance × Human label) per job; Model Match Score per job;
  MAE / median / max abs err, jobs Δ≥20, jobs Δ≥30, Spearman(Model, GT), Spearman(Model, Human Match
  Fit). Fixed references: GT-vs-HMF 0.845, baseline-vs-HMF 0.537.
- Latency / tokens as in the manifest. Cost → `COST_PENDING_EXTERNAL_PRICING_LOOKUP`.
- Write `benchmark_round1_metrics.json` + `benchmark_round1_metrics.csv` (one row per model),
  `benchmark_round1_job_scores.csv`, `benchmark_round1_errors.csv`,
  `benchmark_round1_latency_tokens.csv`.

## Step 9 — Generate slice metrics

- Load per-requirement slice flags from `job_match_baseline_claude_current_v1_error_slices.csv`
  (`is_or_list`, `is_compound`, `root_cause_groups`) + `…_score_analysis.csv`
  (`matchable_requirement_count`) + Dataset V1 `role_category`.
- For each slice × model: n, accuracy, Macro F1 (only if n ≥ 12), error count, directional breakdown.
  Special reports: OR-list accuracy + Strong→Partial-in-OR + Missing→Partial-in-OR; technology-
  adjacency false-positive count (GT Missing → Partial/Strong); project under- vs over-crediting
  counts.
- Write `benchmark_round1_slice_metrics.csv`.

## Step 10 — Compare against baseline

- Assemble `benchmark_round1_model_comparison.md`: one table with the reference row (reused Baseline
  V1 numbers) + one row per new model, across Macro F1, Effective Correct Coverage, per-class F1,
  Strong recall/precision, Partial precision, Missing recall, Strong→Partial, Missing→Partial,
  grounding, normalization success, Spearman(score, HMF), tokens, latency.
- Highlight Δ Macro F1 vs 0.692 against the improvement bar (`<+0.02` noise … `≥+0.10` large).

## Step 11 — Screen candidates

- Apply the manifest's hard gates + Strong/Partial trade-off gate to each model.
- Mark each: `PASS_ALL_GATES` / `FAILS_GATE_<name>` / `REFERENCE`.
- A model is **not** "improved" if Strong recall rises while Strong precision < 0.80 or
  Missing→Partial increases above 6.

## Step 12 — Select top 2–3 for deeper work

- Rank models that pass all gates by Macro F1, then by (Effective Correct Coverage, Spearman vs HMF,
  cost/latency).
- Recommend the top 1–2 to carry into the **Prompt/Rubric Communication Ablation** (job-fit-v3 vs
  rubric-aligned prompt, on the selected model only).
- If **no** new model passes the gates → the deficit is prompt/rule communication; proceed straight
  to the ablation on the reference model.
- Do **not** promote any model to production from Round 1 (development-set only; Dataset V2 held-out
  validation required first).

---

## Guardrails during execution

- 0 web calls. 0 OpenAI/Gemini calls. Only Anthropic, only approved ids.
- No prompt / schema / normalization / scoring / Ground Truth / Dataset / evidence change.
- No repeat trials. No batching change. No eval-side retry beyond SDK default.
- All new files under `backend/evals/benchmark_round1/` and `backend/evals/scripts/`.
- No `git add` / `commit` / `push` without explicit instruction. `README.md` untouched.
