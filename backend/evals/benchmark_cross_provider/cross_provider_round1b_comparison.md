# Round 1B — Cross-Provider Model Screening Results (with Sonnet Comparable Control)

**Fixed semantic contract, current prompt.** Only the provider/model changed. Dataset V1 (30 jobs,
100 matchable requirements), Ground Truth V2, frozen candidate evidence snapshot,
`job-fit-v3-matchable-only` semantics, `fit-analysis-wire-v2` output shape, deterministic
`MatchScoreService`, one call per job, `(job_id, requirement_id)` join — all unchanged. Ground Truth
loaded **only after** every raw prediction was persisted (guard field `GROUND_TRUTH_NOT_LOADED_YET`
on all raw records, every run).

## ⚠️ Dataset governance

**Dataset V1 is DEVELOPMENT / MODEL-SELECTION data — NOT a final unbiased held-out test.** Its
Ground Truth was inspected, baseline errors were analysed, and failure slices were derived from
observed errors before this comparison. Any Round 1B result is **development-set** performance and
must not be presented as unbiased generalisation. **Dataset V2 remains the held-out
validation/test set** and must not be used for iterative prompt tuning before final evaluation.

## Two Sonnet records — kept separate, never merged

| record | source | schema | purpose |
|---|---|---|---|
| **SONNET_PRODUCTION_BASELINE** | Baseline V1 (`job_match_baseline_claude_current_v1`) — **NOT rerun, NOT modified** | FULL 7-field production schema (`RequirementMatchOutput`) via `messages.parse` | measures the **current production system** |
| **SONNET_ROUND1B_COMPARABLE_CONTROL** | **new 30-call run** (this task) | the **same lean 4-field Section D** + TRANSPORT_NORMALIZATION_MAPPING as the Round 1B candidates; Anthropic `messages.parse` binding the lean Section-D schema (`_FitLean`), `temperature=0`, `max_tokens=4096`, no thinking param | **apples-to-apples model comparison** under the Round 1B contract |

**All model-to-model ranking below uses the COMPARABLE CONTROL.** The PRODUCTION BASELINE is shown
separately for product-current-state reference only.

## Prompt assembly & mapping (identical for every Round 1B row incl. the Sonnet control)

- **Section A** = the frozen `job-fit-v3-matchable-only` instructions, captured verbatim from the
  unchanged production `RequirementMatcher` (SHA `e99ed027…`). Not edited.
- **Section D** = the transport-validated canonical **4-field** output contract:
  `summary` / `requirement_matches[{requirement_id, match_label, evidence_ids, reason}]` /
  `suggested_preparation`. Output-contract only — no OR-list / adjacency / project-vs-work /
  compound / example / Ground-Truth / failure-case guidance.
- **TRANSPORT_NORMALIZATION_MAPPING** (non-semantic, identical for every model incl. the Sonnet
  control): `match_label→match_status`, `evidence_ids→evidence_source_ids`, `reason→reason`;
  `importance` := the frozen canonical requirement importance (the `importance_hint` value surfaced
  to every model; a JD property, not a Ground-Truth label); `is_hard_requirement` := `False` and
  `hard_requirement_category` := `"none"` (deterministically mandated by the production prompt for
  `source_kind=v2_matchable`); `confidence` := `"Medium"` constant. Then the **unchanged**
  `_normalize_matches` + `MatchScoreService` run.
- **Reasoning / temperature comparability flags:** `deepseek-v4-pro`, `kimi-k3` run **mandatory,
  non-disableable reasoning** (`reasoning_comparability_flag`); `kimi-k3` also runs `temperature=1`
  (`MODEL_REQUIRED_VALUE`; `temperature_comparability_flag`) vs `temperature=0` for all others.
  Qwen ×2 run `enable_thinking=false`. Sonnet control runs `temperature=0`, no thinking param.

## Experiment integrity

| model | model calls | schema parse | job normalization | retries | integrity | GT-load guard |
|---|---|---|---|---|---|---|
| **SONNET_ROUND1B_COMPARABLE_CONTROL** | 30/30 | 30/30 | 30/30 | 0 | **INTEGRITY_OK** | clean |
| qwen3.8-max | 30/30 | 30/30 | 30/30 | 0 | **INTEGRITY_OK** | clean |
| qwen3.8-flash | 30/30 | 30/30 | 30/30 | 0 | **INTEGRITY_OK** | clean |
| deepseek-v4-pro | 30/30 | **19/30** | **19/30** | 0 | INTEGRITY_OK¹ | clean |
| kimi-k3 | 30/30 | 30/30 | 30/30 | 1 (transient) | **INTEGRITY_OK** | clean |
| SONNET_PRODUCTION_BASELINE | 0 (reused) | 30/30 | 29/30 | — | ref | — |

¹ `deepseek-v4-pro` completed all 30 calls with no prompt/transport drift, but its non-disableable
reasoning consumed the entire fixed 4096-token output budget on 11/30 jobs (reasoning emitted, **no
answer**) → **56/100 requirements unscored**. A reliability failure of the model under the fixed
contract (recorded per §7; `max_tokens` NOT raised — that would break the fixed transport). The
DeepSeek run also suffered repeated multi-minute transport stalls (4 launch attempts). A bounded
HTTP-client timeout+retry setting (`ROUND1B_HTTP_TIMEOUT=90`, `ROUND1B_MAX_RETRIES=6`) was used
**for DeepSeek only** to let the run finish — an HTTP-client operational setting, not a change to
the model request (prompt / schema / temperature / max_tokens unchanged).

- Total new inference calls: **150** — Round 1B 4 new models × 30 = 120, **+ 30** Sonnet comparable
  control (this task, approved). Reference PRODUCTION_BASELINE: 0. Haiku / Opus / Gemini / GLM: 0.
  (Plus a handful of de-risking smoke calls before each full run; disclosed in the run logs.)
- Fixed-input SHAs unchanged: `requirement_matcher.py` `e99ed027…`, `claude_client.py` `76d953c4…`,
  `match_score.py` `8ae2d593…`, Ground Truth `52cda176…`, Dataset V1 `3654d64c…`.

---

## PRIMARY model-selection table (all rows under the SAME Round 1B contract)

| row | Sonnet Comparable Control | Qwen3.8 Max | Qwen3.8 Flash | DeepSeek V4 Pro | Kimi K3 |
|---|---|---|---|---|---|
| **Macro F1** | 0.676 | 0.702 | 0.659 | 0.706 ⚠️(44 reqs) | **0.740** |
| **Δ Macro F1 vs Sonnet control** | — | **+0.026 (small)** | −0.017 (regression) | +0.031 ⚠️(invalid) | **+0.064 (meaningful)** |
| **Effective Correct Coverage** | 0.66 | 0.71 | 0.68 | **0.35** ⚠️ | **0.74** |
| **Accuracy** (on reconciled) | 0.66 | 0.710 | 0.680 | 0.796 (44) | 0.740 |
| Strong P | 0.936 | 0.830 | 0.774 | 0.926 (44) | 0.782 |
| Strong R | 0.558 | 0.750 | 0.788 | 0.926 (44) | **0.827** |
| Strong F1 | 0.699 | 0.788 | 0.781 | 0.926 (44) | **0.804** |
| Partial P | 0.462 | 0.512 | 0.474 | 0.417 (44) | **0.567** |
| Partial R | 0.800 | 0.733 | 0.600 | 0.714 (44) | 0.567 |
| Partial F1 | 0.585 | **0.603** | 0.529 | 0.526 (44) | 0.567 |
| Missing P | 0.765 | 1.000 | 1.000 | 1.000 (44) | 0.933 |
| Missing R | 0.722 | 0.556 | 0.500 | 0.500 (44) | **0.778** |
| Missing F1 | 0.743 | 0.714 | 0.667 | 0.667 (44) | **0.849** |
| **Strong→Partial** | **23** | 13 | 11 | 2 (44) | **9** |
| **Missing→Partial** | 5 | 8 | 9 | 5 (44) | **4** |
| Partial→Strong | 2 | 8 | 12 | 2 (44) | 12 |
| Partial→Missing | 4 | 0 | 0 | 0 (44) | 1 |
| OR-list (acc / Macro F1) | 0.333 / 0.300 | 0.444 / 0.458 | 0.444 / 0.458 | 0.556 / – (9) | **0.778 / 0.736** |
| Technology-adjacency (acc, n=5) | 0.40 | 0.40 | 0.20 | 0.00 (4) | **0.60** |
| Project/work (acc / Macro F1) | 0.645 / 0.638 | 0.662 / 0.616 | 0.642 / 0.560 | 0.762 / 0.645 (21) | 0.651 / 0.536 |
| Compound (acc / Macro F1) | 0.692 / 0.683 | 0.615 / 0.627 | 0.462 / 0.336 | – | 0.615 / 0.626 |
| **Chinese-JD Macro F1** | 0.669 | 0.709 (+0.039) | 0.672 (+0.002) | 0.679 (40 reqs) | **0.752 (+0.082)** |
| Chinese-JD accuracy | 0.656 | 0.720 | 0.699 | 0.800 (40) | 0.753 |
| Grounding rate | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Unsupported match rate | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Evidence-ID validity | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Job normalization | **30/30** | **30/30** | **30/30** | **19/30** | **30/30** |
| Requirement coverage | **100/100** | **100/100** | **100/100** | **44/100** | **100/100** |
| Match Score MAE vs GT | 14.87 | 11.5 | 12.83 | 8.89 (19 jobs) | **10.43** |
| Score vs GT Spearman | 0.746 | 0.677 | 0.803 | 0.830 (19) | 0.652 |
| Score vs HMF Spearman (ceiling 0.845) | 0.647 | 0.609 | 0.667 | 0.700 (19) | **0.723** |
| mean latency (ms) | 18,865 | **13,609** | **11,397** | 48,049 | 28,125 |
| P90 latency (ms) | 24,226 | 20,922 | **19,154** | 65,100 | 39,289 |
| input tokens | 125,266 | 84,331 | 84,331 | 86,972 | 84,543 |
| output tokens | 25,998 | 24,218 | 22,219 | 95,269 | 23,033 |
| reasoning tokens | 0 | 0 | 0 | 82,971 | 3,370 |
| total tokens | 151,264 | 108,549 | **106,550** | 182,241 | 107,576 |
| verified cost (30 jobs) | **$0.766** (Anthropic public, verified 2026-09-01) | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| flags | ref control; single-pass; temp 0; 4-field D | temp 0; `enable_thinking=false`; 4-field D | temp 0; `enable_thinking=false`; 4-field D | temp 0; **reasoning MANDATORY**; 4-field D | **temp 1**; **reasoning MANDATORY** low-effort; 4-field D |

⚠️ DeepSeek rows are computed over the **44/100 requirements** (19/30 jobs) it actually answered —
**not comparable** to the full-coverage models. Its system-level number is **ECC 0.35** (see §11).

### PRODUCTION BASELINE (separate — current production system, full 7-field schema)

| | Macro F1 | ECC | Acc | Strong P/R/F1 | Partial P/R/F1 | Missing P/R/F1 | S→P | M→P | grounding | coverage · norm | MS MAE | ρ(score,HMF) | mean lat | tokens | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SONNET_PRODUCTION_BASELINE | 0.692 | 0.62 | 0.681 | 0.879/0.630/0.734 | 0.477/0.778/0.591 | 0.857/0.667/0.750 | 17 | 6 | 1.000/0.000 | 91/100 · 29/30 | 13.45 | 0.537 | 21,068 ms | 159,061 | $0.854 |

---

## What changed when Sonnet ran the SAME lean contract (key new finding)

| metric | PRODUCTION_BASELINE (7-field) | COMPARABLE_CONTROL (4-field) | Δ |
|---|---|---|---|
| Macro F1 | 0.692 | **0.676** | **−0.016** |
| ECC | 0.62 | 0.66 | +0.04 (100/100 vs 91/100 coverage) |
| Strong recall | 0.630 | **0.558** | **−0.072** |
| Strong→Partial | 17 | **23** | **+6** |
| Partial precision | 0.477 | 0.462 | −0.015 |
| Missing recall | 0.667 | 0.722 | +0.055 |
| ρ(score, HMF) | 0.537 | 0.647 | +0.110 |
| requirement coverage | 91/100 | **100/100** | +9 |
| total tokens | 159,061 | 151,264 | −7,797 |

**The lean 4-field contract slightly WORSENS Sonnet's classification** (Macro F1 −0.016; Strong
recall drops sharply and Strong→Partial rises 17→23). The production 7-field schema — which forces
the model to commit an explicit `importance` / `is_hard_requirement` / `confidence` per requirement
— was helping Sonnet's Strong/Partial calibration. But the lean contract also **eliminates the
91/100 normalization gap** (Sonnet control reconciles 100/100) and **markedly improves score↔HMF
correlation** (0.537 → 0.647). So the "comparability gap" was not one-directional: the leaner
contract helped coverage and job-score calibration while hurting per-label Strong recall.

**Implication for the model comparison:** under the *identical* lean contract, the new candidates'
advantage over Sonnet is **larger**, not an artefact of an easier contract. Kimi-k3's Macro F1 lead
grows from +0.048 (vs production baseline) to **+0.064 (vs comparable control) — now a "meaningful"
improvement**. Qwen3.8 Max moves from "not compelling" (+0.010) to a genuine **"small" (+0.026)**
classification improvement, on top of its reliability and latency edge.

---

## Rankings (all under the SAME Round 1B contract)

### Macro F1 (primary)
1. **kimi-k3 — 0.740**
2. qwen3.8-max — 0.702
3. **SONNET_ROUND1B_COMPARABLE_CONTROL — 0.676**
4. qwen3.8-flash — 0.659
- deepseek-v4-pro — 0.706 *(invalid: only 44/100 requirements; system ECC 0.35 — not ranked against full-coverage models)*

### Effective Correct Coverage (system co-primary)
1. **kimi-k3 — 0.74**
2. qwen3.8-max — 0.71
3. qwen3.8-flash — 0.68
4. **SONNET_ROUND1B_COMPARABLE_CONTROL — 0.66**
5. deepseek-v4-pro — 0.35

### Per-class F1 (full-coverage models)
- **Strong F1:** kimi-k3 **0.804** > qwen-max 0.788 > qwen-flash 0.781 > Sonnet-control 0.699
- **Partial F1:** qwen-max **0.603** > Sonnet-control 0.585 = kimi-k3 0.567¹ > qwen-flash 0.529
- **Missing F1:** kimi-k3 **0.849** > Sonnet-control 0.743 > qwen-max 0.714 > qwen-flash 0.667

¹ Sonnet-control 0.585 vs kimi-k3 0.567 — Sonnet-control edges Partial F1 via high Partial recall (0.80) at the cost of Partial precision (0.462) and Strong recall (0.558).

### Confusion matrices (GT rows × Pred cols, S / P / M)
```
SONNET_COMPARABLE_CONTROL (100)   Qwen3.8 Max (100)        Qwen3.8 Flash (100)
  S [ 29  23   0 ]                  S [ 39  13   0 ]         S [ 41  11   0 ]
  P [  2  24   4 ]                  P [  8  22   0 ]         P [ 12  18   0 ]
  M [  0   5  13 ]                  M [  0   8  10 ]         M [  0   9   9 ]

DeepSeek V4 Pro (44 reconciled ONLY)   Kimi K3 (100)        SONNET_PRODUCTION_BASELINE (91, §18)
  S [ 25   2   0 ]                       S [ 43   9   0 ]     Strong→Partial 17 ; Missing→Partial 6
  P [  2   5   0 ]                       P [ 12  17   1 ]     Strong P/R 0.879/0.630
  M [  0   5   5 ]                       M [  0   4  14 ]     Partial P/R 0.477/0.778 ; Missing P/R 0.857/0.667
```

### Directional errors — all six transitions
| transition | Sonnet Control | Qwen Max | Qwen Flash | DeepSeek(44) | Kimi K3 | Sonnet Prod Baseline |
|---|---|---|---|---|---|---|
| Strong→Partial | **23** | 13 | 11 | 2 | **9** | 17 |
| Strong→Missing | 0 | 0 | 0 | 0 | 0 | 0 |
| Partial→Strong | 2 | 8 | 12 | 2 | 12 | (n/a) |
| Partial→Missing | 4 | 0 | 0 | 0 | 1 | 0 |
| Missing→Strong | 0 | 0 | 0 | 0 | 0 | 0 |
| Missing→Partial | 5 | 8 | 9 | 5 | **4** | 6 |

**Every model over-produces Partial.** Under the lean contract Sonnet is the *most* conservative
about Strong (23 Strong→Partial) and kimi-k3 the least (9). No model exceeds Partial precision 0.60.

### OR-list / adjacency / project-vs-work / compound
- **OR-list:** kimi-k3 (0.778 / 0.736) ≫ Qwen pair (0.444 / 0.458) > **Sonnet control (0.333 / 0.300 — worst)**. Under the lean contract Sonnet is the weakest OR-list interpreter.
- **Technology-adjacency** (GT=Missing, adjacent tech; n=5): kimi-k3 **0.60** > Sonnet-control 0.40 = qwen-max 0.40 > qwen-flash 0.20 > deepseek 0.00. Adjacency FPs: kimi-k3 **2**, Sonnet-control 3, qwen-max 3, qwen-flash 4, deepseek 4.
- **Project/work:** all ~0.64–0.76 accuracy; `project_over_credited` — qwen-flash 18, kimi-k3 16, qwen-max 14, **Sonnet-control 5** (Sonnet under-credits project evidence: `project_under_credited` 8 vs kimi-k3 4).
- **Compound:** Sonnet-control best (0.692 / 0.683), qwen-flash worst (0.462 / 0.336).

### Chinese-JD subset (27 jobs, 93 matchable requirements — 90 % of Dataset V1)
| model | reconciled | accuracy | Macro F1 | Δ vs Sonnet control |
|---|---|---|---|---|
| **kimi-k3** | 93/93 | 0.753 | **0.7515** ✓ (meets 0.75 sub-target) | **+0.082** |
| qwen3.8-max | 93/93 | 0.720 | 0.7087 | +0.039 |
| qwen3.8-flash | 93/93 | 0.699 | 0.6717 | +0.002 |
| **SONNET_ROUND1B_COMPARABLE_CONTROL** | 93/93 | 0.656 | 0.6694 | — |
| deepseek-v4-pro | 40/93 | 0.800 | 0.6788 | +0.009 (40 reqs) |

### Grounding & schema/coverage
Grounding rate **1.000**, unsupported-match rate **0.000**, evidence-ID validity **1.000**,
Strong/Partial-zero-evidence **0.000**, Missing-with-evidence **0.000** — for **every** model
including the Sonnet control. No duplicate/hallucinated ids, no invalid labels for any full-coverage
model. Coverage: Sonnet-control / qwen-max / qwen-flash / kimi-k3 = **100/100 · 30/30**;
deepseek-v4-pro = **44/100 · 19/30**.

### Match Score (deterministic `MatchScoreService`, unchanged)
| model | MAE vs GT | median | max | jobs Δ≥20 | jobs Δ≥30 | ρ(model,GT) | ρ(model,HMF) |
|---|---|---|---|---|---|---|---|
| SONNET_ROUND1B_COMPARABLE_CONTROL | 14.87 | 11.0 | 50 | 9 | 4 | 0.746 | 0.647 |
| qwen3.8-max | 11.5 | 8.0 | 50 | 8 | 2 | 0.677 | 0.609 |
| qwen3.8-flash | 12.83 | 12.5 | 40 | 9 | 3 | **0.803** | 0.667 |
| deepseek-v4-pro | 8.89 (19 j) | 0 | 30 | 5 | 1 | 0.830 (19) | 0.700 (19) |
| kimi-k3 | **10.43** | 0 | 50 | 9 | 3 | 0.652 | **0.723** |
| SONNET_PRODUCTION_BASELINE | 13.45 | — | — | — | — | 0.707 | 0.537 |

GT-Match-Score vs Human-Match-Fit Spearman ceiling = **0.845**. Under the SAME contract, **kimi-k3's
model score tracks human match-fit best (0.723)** — +0.076 over the Sonnet control (0.647).
qwen3.8-max is *below* the Sonnet control here (0.609 vs 0.647).

### Latency & tokens
- **Fastest:** qwen3.8-flash (11.4 s / P90 19.2 s), qwen3.8-max (13.6 s / 20.9 s). Both faster than
  the Sonnet control (18.9 s / 24.2 s).
- **kimi-k3:** 28.1 s / 39.3 s — ~1.5× the Sonnet control, for low-effort mandatory reasoning.
- **deepseek-v4-pro:** 48.0 s / 65.1 s — 2.5× the Sonnet control; 82,971 reasoning tokens.
- **Total tokens:** qwen-flash 106.6 k ≈ kimi-k3 107.6 k ≈ qwen-max 108.5 k — all **~29 % below the
  Sonnet control's 151.3 k** (Sonnet's input is inflated by the schema tool definition).

### Verified cost
`SONNET_ROUND1B_COMPARABLE_CONTROL`: **$0.766 / 30 jobs** ($0.0255/job), Anthropic public pricing
$3/$15 per Mtok, verified 2026-09-01. `SONNET_PRODUCTION_BASELINE`: $0.854. The four new models:
`cost_status = PENDING_OFFICIAL_PRICING_VERIFICATION` — token usage recorded in full; cost fillable
later without rerun.

---

## Quality gates (unchanged thresholds)

Primary: **Macro F1 ≥ 0.75, ECC ≥ 0.75, Grounding ≥ 0.98, Unsupported ≤ 0.02.**

| model | Macro F1 ≥ 0.75 | ECC ≥ 0.75 | Grounding ≥ 0.98 | Unsupported ≤ 0.02 | **primary gate** |
|---|---|---|---|---|---|
| SONNET_ROUND1B_COMPARABLE_CONTROL | ✗ 0.676 | ✗ 0.66 | ✓ 1.00 | ✓ 0.00 | **FAIL** |
| qwen3.8-max | ✗ 0.702 | ✗ 0.71 | ✓ 1.00 | ✓ 0.00 | **FAIL** |
| qwen3.8-flash | ✗ 0.659 | ✗ 0.68 | ✓ 1.00 | ✓ 0.00 | **FAIL** |
| deepseek-v4-pro | ✗ 0.706⚠️ | ✗ 0.35 | ✓ 1.00 | ✓ 0.00 | **FAIL** |
| kimi-k3 | ✗ 0.740 | ✗ 0.74 | ✓ 1.00 | ✓ 0.00 | **FAIL (nearest miss: −0.010 / −0.01)** |

Additional targets: **Strong R ≥ 0.75, Strong P ≥ 0.80, Partial P ≥ 0.60, Missing R ≥ 0.667.**

| model | Strong R ≥ 0.75 | Strong P ≥ 0.80 | Partial P ≥ 0.60 | Missing R ≥ 0.667 |
|---|---|---|---|---|
| SONNET_ROUND1B_COMPARABLE_CONTROL | ✗ 0.558 | ✓ 0.936 | ✗ 0.462 | ✓ 0.722 |
| qwen3.8-max | ✓ 0.750 | ✓ 0.830 | ✗ 0.512 | ✗ 0.556 |
| qwen3.8-flash | ✓ 0.788 | ✗ 0.774 | ✗ 0.474 | ✗ 0.500 |
| deepseek-v4-pro | ✓ 0.926⚠️ | ✓ 0.926⚠️ | ✗ 0.417⚠️ | ✗ 0.500⚠️ |
| kimi-k3 | ✓ 0.827 | ✗ 0.782 | ✗ 0.567 | ✓ 0.778 |

**No model passes the primary gate. No model reaches Partial precision 0.60** — best is kimi-k3
0.567; the six records (four providers + two Sonnet contracts) all cluster **0.42–0.57**.

## Improvement size vs the SONNET COMPARABLE CONTROL (Macro F1 0.676)

| model | ΔMacro F1 | band |
|---|---|---|
| kimi-k3 | **+0.064** | **meaningful** (+0.08 ECC, +0.082 Chinese-JD, +0.076 ρ(score,HMF)) |
| qwen3.8-max | **+0.026** | **small** (+0.05 ECC, +0.039 Chinese-JD; but −0.038 on ρ(score,HMF)) |
| deepseek-v4-pro | +0.031 | *invalid* (ECC 0.35, 44 % coverage) |
| qwen3.8-flash | **−0.017** | **regression** (smaller than the −0.033 vs the production baseline, still negative) |

---

See `cross_provider_round1b_pareto.md` for the revised Pareto frontier and
`cross_provider_round1b_shortlist.md` for the revised Top-3 shortlist and the Prompt-Ablation
decision. Aggregates: `cross_provider_round1b_metrics.json` / `.csv`. Per-model artifacts:
`cross_provider_round1b_*_<slug>.*` (`<slug>` includes `sonnet-comparable`).
