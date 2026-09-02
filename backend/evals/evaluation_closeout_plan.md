# JobPilot Evaluation — Close-out Plan

**Scope decision:** deliberately reduced. Goal = a **credible AI Product Evaluation Case
Study**, not a production-grade or publication-grade benchmark. No expansion of evaluation
breadth. No production code / Match Score changes. No staging/commit/push yet.

Checkpoint: `a82ee17` ("eval: complete prompt ablation and refinement"). Dataset V1 prompt
development frozen. Frozen finalists: **Qwen3.8-Max + Prompt C** (`job-fit-v3-rubric-refined-v2`)
and **Kimi K3 + Control / Prompt A** (`job-fit-v3-matchable-only`).

---

## 1. Exact remaining tasks

| # | task | inference? | output |
|---|---|---|---|
| **T1** | **Targeted taxonomy fixes (V1 GT).** Fix only the already-identified obvious errors: (a) degree / education / explicit years-of-experience requirements currently typed `matchable` → `eligibility`; (b) clearly subjective traits currently typed `matchable` → `subjective` (non-scoring). Recorded as corrections against the frozen GT (raw GT untouched). Note Match-Score denominator impact per affected job. **No 158-row re-review.** | none | `importance_audit/taxonomy_targeted_fixes.{json,md}` |
| **T2** | **Importance calibration (8–10 cases).** From the 30-row `importance_round1_adjudication_pack`, take only the 8–10 highest-|ΔI↔P| / clearest-centrality rows. Human fills `human_importance` + `importance_uncertain` + notes for those, as a **calibration reference set**. Remaining ~20 rows stay `importance_not_explicitly_human_verified` (documented). **No exhaustive adjudication.** | none | `importance_audit/importance_calibration_set.{csv,md}` |
| **T3** | **Match GT — freeze as-is.** Preserve the existing human Strong/Partial/Missing adjudication (V1 full-v2 human-verified + the 9 synthetic decisions in `synthetic_match_adjudication_checkpoint`). No relabeling. Document where taxonomy/importance remain subjective. | none | `match_gt_limitations.md` |
| **T4** | **Dataset V2 held-out preparation.** V2-Real: freeze the verified pool as-is (16 `human_provenance_verified` Batch-2 jobs + any already-collected verified extras — **no new large-scale collection**), run matcher-independent canonical requirement-candidate extraction, do a lightweight human GT pass. V2-Synthetic: finish the 65-probe human review (9 high-risk already done), freeze the scenario-derived GT. **Metrics kept strictly separate; synthetic never merged into real.** | none | `dataset_v2/dataset_v2_real_frozen.json`, `..._real_requirements.json`, `..._real_gt.json`; `dataset_v2_synthetic/synthetic_gt_frozen.json`; `dataset_v2/dataset_v2_heldout_manifest.json` |
| **T5** | **Finalist held-out evaluation.** Run **only** the two frozen finalist configs, one call per job per model per dataset, against V2-Real (held-out) and V2-Synthetic (stress) **separately**. Metrics: Macro F1, ECC, per-class P/R/F1, confusion, grounding / unsupported-match, Match Score MAE vs GT, Spearman(model score, HMF). Synthetic additionally split **all-matchable / probe-only / per-scenario-category**. **No prompt tuning, no new models, no few-shot.** | **yes — only these 2 frozen configs** | per-model×dataset `predictions.json` + `metrics.json` (8 files) under `dataset_v2*/heldout/`; `finalist_heldout_comparison.{json,md}` |
| **T6** | **Final Job Analysis Evaluation summary.** One consolidated case-study report: dataset design · GT construction · baseline · model comparison (Round 1A/1B) · prompt ablation (Round 2A/2B) · held-out validation (T5) · key error slices · final model decision · limitations (§7 wording below) · what would be done next in production. | none | `job_analysis_evaluation_final_summary.md` (optional shareable `.html` case study) |
| **T7** | **Close-out commit.** Stage explicit eval-only paths only, secret scan, protected-path check, one commit, push origin/main. | none | git commit + push |

## 2. Tasks explicitly dropped

- Full 158-row taxonomy re-review (only the obvious pre-identified errors are fixed).
- Exhaustive Importance adjudication — all 30 Round-1 rows, and then all 158 rows (only 8–10 calibration cases).
- Round 2C or any further prompt tuning / few-shot iteration / Prompt A/B/C changes (frozen).
- New model search / additional providers or variants (Gemini, GLM, OpenAI, more Qwen/Kimi). DeepSeek stays eliminated.
- Match Score redesign, re-weighting, or adding eligibility into the score.
- Recomputing Spearman(GT Match Score, Human Match Fit) as a *proven* construct-validity number — it stays "provisionally supported / pre-Importance-audit".
- Expanding the synthetic set beyond the current 50 jobs / 7 scenario categories / 65 probes.
- Large-scale V2-Real collection to hit the earlier 24–30-job / ≥10-company diversity targets (use the verified pool; document small-N).
- Production/UI implementation of the Capability-Match vs Eligibility presentation (documentation only).
- Any publication- or production-grade benchmark framing or validity claim.

## 3. Estimated artifacts to produce

**~20–24 eval-only files, 0 production files**, across T1–T7:
- T1: 2  ·  T2: 2  ·  T3: 1  ·  T4: 6  ·  T5: ~10 (8 predictions/metrics + 2 comparison)  ·  T6: 1–2  ·  T7: 0 (commit only).

All under `backend/evals/**` (`importance_audit/`, `dataset_v2/`, `dataset_v2_synthetic/`). Raw/frozen GT artifacts remain untouched; corrections and held-out results are recorded as new files.

## 4. Exact next execution step

**Begin T1 — Targeted taxonomy fixes.** Scan the 100 Dataset V1 `matchable` requirements for
(a) degree / education / explicit years-of-experience wording that belongs in `eligibility`,
and (b) clearly subjective-trait wording that belongs in `subjective`. Produce
`backend/evals/importance_audit/taxonomy_targeted_fixes.{json,md}` listing each proposed
change (`requirement_id`, before/after `requirement_type`, one-line JD-grounded reason,
affected job's Match-Score denominator delta) for human confirmation. No full re-review, no
model inference, no commit.

## 5. Stop condition

After **T5** (held-out finalist evaluation) and **T6** (final Job Analysis Evaluation
summary) are complete and **T7** (close-out commit) is pushed, the **Job Analysis
Evaluation is COMPLETE**. No further Job Analysis eval work — no more taxonomy review,
importance adjudication, prompt tuning, model search, synthetic expansion, or Match Score
changes. Next effort: a separate, **lightweight Daily Planning Agent evaluation**.

## 7. Evaluation limitation wording (to appear verbatim in T6)

- **Small dataset.** Dataset V1 = 30 jobs / 158 canonical requirements (100 matchable); V2-Real is a small verified held-out pool. Estimates carry wide uncertainty.
- **Human annotation subjectivity.** Ground Truth Strong/Partial/Missing and Human Match Fit are single-adjudicator judgments; taxonomy and importance calls at the margins are debatable.
- **Importance calibration is partial, not exhaustive.** Only 8–10 high-impact importance labels received explicit human review; the rest remain `importance_not_explicitly_human_verified`.
- **Synthetic set is behavioral stress testing, not real-world performance estimation.** The V2-Synthetic Challenge Set probes known decision boundaries with a controlled, non-representative distribution; its metrics must never be read as real-world accuracy or merged with V2-Real.
- **Dataset V1 is development / model-selection data** (used for model screening and prompt ablation); it is not held out.
- **Dataset V2 is the held-out validation set**; the +0.084 Macro F1 Prompt-C gain observed on Dataset V1 is a development-set result pending V2 confirmation.
- **Not a production-grade benchmark.** This is a credible AI Product Evaluation Case Study; no production- or publication-grade validity is claimed.
