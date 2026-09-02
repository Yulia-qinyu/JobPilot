# Frozen Finalist Held-Out Evaluation — Consolidated Comparison

**A (primary):** `qwen3.8-max + job-fit-v3-rubric-refined-v2` (Prompt C)  ·  **B:** `kimi-k3 + job-fit-v3-matchable-only` (Control / Prompt A)

Corrections applied post-run (no model output changed): grounding metric fixed to the assembled-prompt `evidence_source_id` set (harness fed doubled-prefix IDs); one kimi V2-Real transient 429 completed under the standard retry policy.

## V2-Real  (primary held-out signal — N = 8 jobs / 32 matchable GT; low statistical power)

| metric | qwen + Prompt C | kimi + Control |
|---|---|---|
| Macro F1 | 0.8697 | **0.892** |
| ECC | 0.8125 | **0.8438** |
| Accuracy | 0.8125 | **0.8438** |
| Strong F1 | 0.7857 | **0.8485** |
| Partial F1 | 0.8235 | 0.8276 (~tie) |
| Missing F1 | 1.0 | 1.0  (Missing support = 1) |
| Grounding rate | 1.0 | 1.0 |
| Unsupported-match rate | 0.0 | 0.0 |
| Match-Score MAE (vs GT repr-core) | 9.5 | **7.625** |
| Spearman(model score, HMF) | **0.7608** | 0.7506 (~tie, N=8) |
| Coverage | 1.0 | 1.0 |
| Mean latency | **15322.5 ms** | 34134.3 ms |
| First-pass success | **8/8** | 7/8 (1×429, recovered on retry) |

V2-Real confusion — qwen `{'Strong': {'Strong': 11, 'Partial': 4, 'Missing': 0}, 'Partial': {'Strong': 2, 'Partial': 14, 'Missing': 0}, 'Missing': {'Strong': 0, 'Partial': 0, 'Missing': 1}}` ; kimi `{'Strong': {'Strong': 14, 'Partial': 1, 'Missing': 0}, 'Partial': {'Strong': 4, 'Partial': 12, 'Missing': 0}, 'Missing': {'Strong': 0, 'Partial': 0, 'Missing': 1}}`

## V2-Synthetic — human-reviewed probe subset (20 S/P/M rows)

| metric | qwen + Prompt C | kimi + Control |
|---|---|---|
| Macro F1 | **0.903** | 0.8362 |
| ECC / accuracy | **0.9** | 0.85 |

Per-scenario probe accuracy:

| category | qwen | kimi |
|---|---|---|
| technology_adjacency | 1.0 | 0.3333 |
| project_vs_formal_work | 1.0 | 1.0 |
| strong_partial_boundary | 1.0 | 1.0 |
| partial_missing_boundary | 0.6667 | 0.6667 |
| or_alternative | 1.0 | 1.0 |
| compound | 1.0 | 1.0 |
| role_core_mismatch | 0.6667 | 1.0 |

**Dominant synthetic failure:** kimi + Control collapses on `technology_adjacency` (accuracy 0.33 — upgrades general LLM / model-eval evidence to Partial/Strong for distinct specialised capabilities). qwen + Prompt C holds `technology_adjacency` at 1.00 — the Prompt-C adjacency guardrail generalises to the stress set. Both models miss `partial_missing_boundary` (0.67); qwen also misses `role_core_mismatch` (0.67).

## V2-Synthetic — all-matchable (98 rows; mostly scenario-derived GT — weaker signal)

| metric | qwen + Prompt C | kimi + Control |
|---|---|---|
| Macro F1 | 0.7849 | **0.8112** |
| ECC | 0.7959 | **0.8367** |
| Mean latency | **9974.5 ms** | 22393.2 ms |

## Read of the evidence — MIXED

- **V2-Real classification:** kimi + Control nominally ahead (Macro F1 +0.022, ECC +0.031, Strong F1 +0.063, MAE −1.9), but every margin is inside the noise of a 32-row / N=8 GT — one flipped label moves Macro F1 by ~0.03. Treat V2-Real classification as a **statistical tie**.
- **V2-Real ranking & grounding:** tie (Spearman ~0.75–0.76 both; grounding 1.0 / unsupported 0.0 both).
- **Synthetic stress test:** qwen + Prompt C clearly better on the human-reviewed probes (0.903 vs 0.836) and decisively better on `technology_adjacency` — the exact failure mode Prompt C was built to fix. kimi + Control's uninstructed calibration reproduces the known Dataset-V1 adjacency weakness.
- **Operational:** qwen is ~2.2× faster (15 s vs 34 s / job on V2-Real; 10 s vs 22 s on synthetic) and had cleaner first-pass reliability.
- **Generalisation of the V1 finding:** the +0.084 Dataset-V1 Prompt-C Macro-F1 gain did **not** reproduce as a held-out V2-Real classification lead for qwen; on real data the two are level. Prompt C's benefit shows up as **robustness on the adjacency stress slice**, not as a real-world accuracy jump.

## Winners

- **V2-Real:** no confident winner (statistical tie). Nominal classification edge: **kimi + Control**. Nominal ranking/MAE/operational edge: **qwen + Prompt C**.
- **Synthetic stress-test:** **qwen + Prompt C**.
- **Operational reliability:** **qwen + Prompt C** (latency + first-pass).

## Recommended production matcher

**qwen3.8-max + Prompt C (`job-fit-v3-rubric-refined-v2`)** — on the balance of: a V2-Real classification tie (not a loss), a decisive synthetic-robustness advantage on the targeted adjacency failure mode, ~2.2× lower latency, and better first-pass reliability. **kimi-k3 + Control remains a fully viable fallback** with slightly better V2-Real Strong-recall and Match-Score MAE. This is a case-study recommendation, not a production-grade benchmark result — see limitations.


---

# Production Economics / Cost Trade-off  (added by T5.5 — the T5 metrics above are unchanged)

_Full analysis: `finalist_cost_analysis.{json,md}`. **No new model calls** — token usage recovered from the frozen T5 prediction artifacts (116/116 calls carry complete usage metadata). Unit prices are **unavailable / unverifiable** in this environment (repo config has none; `qwen3.8-max` / `kimi-k3` list prices not establishable) — dollar cost is price-parameterised, never invented._

| dimension | qwen3.8-max + Prompt C | kimi-k3 + Control |
|---|---|---|
| mean tokens / call (58-call run) | 3,862  (prompt-cache **41%**, reasoning 0) | 3,496  (prompt-cache **13%**, reasoning **~13%** of completion) |
| V2-Real tokens / call | 4,403  (cache **90%**) | 4,018  (cache 6%) |
| raw total tokens / correct V2-Real requirement | 1,355 | **1,191** |
| cache-adjusted billable tokens / correct req (0.25 cache price) | **~646** | ~1,148 |
| V2-Real latency mean / p95 | **15.3 s / 17.8 s** | 34.1 s / 58.8 s |
| V2-Synthetic latency mean / p95 | **10.0 s / 13.3 s** | 22.4 s / 30.1 s |
| first-pass success (58 calls) | **58/58**  (0 retries) | 57/58  (1× HTTP 429, recovered) |
| structured-output parse OK (58) | 58/58 | 58/58 |

**Trade-off answers** — (1) V2-Real quality difference **not materially meaningful** (+1 / 32 correct requirement, within N=8 noise). (2) Faster: **qwen** (~2.2×). (3) More operationally reliable: **qwen** (58/58 first-pass, 0 retries). (4) Cheaper for the observed workload: **qwen on effective cache-adjusted billable tokens** (kimi marginally leaner on raw tokens; exact $ pending verified unit prices; direction favours qwen because ~90% of its V2-Real input is cache-served and it emits no reasoning tokens). (5) The heavier/pricier option buys **no reliable extra quality**, and the synthetic stress test favours qwen (probe Macro F1 0.90 vs 0.84; technology-adjacency 1.00 vs 0.33). (6) Better production trade-off: **qwen3.8-max + Prompt C.**

**Recommendation vs T5: unchanged and strengthened.** Production matcher = **qwen3.8-max + Prompt C**; **kimi-k3 + Control** remains a viable fallback.
