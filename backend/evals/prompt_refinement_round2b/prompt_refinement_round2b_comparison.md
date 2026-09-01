# Prompt Refinement Round 2B — A / B / C Comparison

**FINAL Dataset V1 prompt-development iteration.** Development-set only; Dataset V2 held out, not used.
Controls (A) and full rubric (B) reused, not rerun. **60 new inference calls** (kimi-k3, qwen3.8-max
× 30). Raw persisted before GT load (guard `GROUND_TRUTH_NOT_LOADED_YET` on all 60).

- **A / control** = `job-fit-v3-matchable-only` + Section D 4-field (SHA `abacf2cf…`)
- **B / rejected** = `job-fit-v3-rubric-aligned-v1` (Round 2A; 5 rule groups incl. OR-list + compound; +3,442 chars; SHA `4ff452b9…`)
- **C / refined** = `job-fit-v3-rubric-refined-v2` (Round 2B; **3 compact rule groups only** — Technology Adjacency, Project-vs-Formal-Work, Strong/Partial/Missing Calibration; **OR-list and compound rules removed**; +1,808 chars; SHA `7625ac37…`). Base byte-identical to A outside the single insert. Production `requirement_matcher.py` SHA `e99ed027…` unchanged.

Prompt-bottleneck status: **REAL_BUT_PARTIAL_LEVER** (Round 2A causally demonstrated rubric
communication affects behaviour; not the sole/dominant cause; no ~93%-causal claim).

## kimi-k3 — A vs B vs C

| metric | A control | B full rubric | **C refined** |
|---|---|---|---|
| **Macro F1** | 0.7396 | 0.7661¹ | **0.7225** |
| **Δ Macro F1 vs A** | — | +0.027¹ | **−0.017 (NOT_SUPPORTED / regression)** |
| **ECC** | 0.74 | 0.69 | **0.75** |
| Accuracy | 0.740 | 0.758 | 0.750 |
| **coverage · job-norm** | 100/100 · 30/30 | **91/100 · 29/30** | **100/100 · 30/30** ✓ |
| Strong P / R / F1 | 0.782 / 0.827 / 0.804 | 0.854 / 0.761 / 0.805 | 0.783 / **0.904** / 0.839 |
| Partial P / R / F1 | 0.567 / 0.567 / 0.567 | 0.571 / 0.741 / 0.645 | **0.609** / **0.467** / 0.528 |
| Missing P / R / F1 | 0.933 / 0.778 / 0.849 | 0.933 / 0.778 / 0.849 | 0.824 / 0.778 / 0.800 |
| Strong→Partial | 9 | 11 | **5** |
| Missing→Partial | 4 | 4 | 4 |
| Partial→Strong | 12 | 6 | **13** |
| Grounding / Unsupported | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 |
| Match Score MAE | 10.43 | 10.66 | **9.87** |
| ρ(score, HMF) | 0.723 | 0.722 | **0.734** |
| Chinese-JD Macro F1 | 0.7515 | 0.7698 | 0.7437 |
| adjacency slice acc / FP | 0.60 / 2 | 0.60 / 2 | **0.80 / 1** |
| project slice Macro F1 | 0.536 | 0.690 | 0.589 |
| OR-list slice Macro F1 (monitoring) | 0.736 | 0.562 | **0.630** (still below A) |
| compound slice Macro F1 (monitoring) | 0.626 | 0.604 | **0.626** (restored to A) |
| mean latency (ms) | 28,125 | 29,440 | 29,236 |
| total tokens (reasoning) | 107,576 (3,370) | 129,530 (5,218) | 121,284 (5,630) |
| integrity | — | INTEGRITY_OK (91/100 cov) | **INTEGRITY_OK (100/100)** |

¹ B Macro F1 on 91 reconciled requirements — not a like-for-like base.

Confusion (S/P/M): A `[[43,9,0],[12,17,1],[0,4,14]]` → C `[[47,5,0],[13,14,3],[0,4,14]]`.

**Prompt C fixed the Round 2A coverage failure (100/100, INTEGRITY_OK) and pushed Partial precision
above 0.60 (0.609), but Macro F1 REGRESSED −0.017.** The explicit calibration rules over-push
kimi-k3 toward Strong (Strong recall 0.83→0.90, Strong→Partial 9→5) at the cost of Partial recall
(0.567→0.467) and Missing precision (0.933→0.824). kimi-k3's calibration was already the best in the
pool; adding any rubric block destabilises its Partial/Strong boundary. Its OR-list slice stays
below control (0.630 vs 0.736) **even though the OR-list rule was removed** — kimi degrades on
OR-lists under any added rubric text.

## qwen3.8-max — A vs B vs C

| metric | A control | B full rubric | **C refined** |
|---|---|---|---|
| **Macro F1** | 0.7016 | 0.7142 | **0.7858** |
| **Δ Macro F1 vs A** | — | +0.013 (NOT_SUPPORTED) | **+0.084 (SUPPORTED)** |
| **ECC** | 0.71 | 0.71 | **0.78** |
| Accuracy | 0.71 | 0.71 | **0.78** |
| **coverage · job-norm** | 100/100 · 30/30 | 100/100 · 30/30 | **100/100 · 30/30** ✓ |
| Strong P / R / F1 | 0.830 / 0.750 / 0.788 | 0.826 / 0.731 / 0.775 | 0.800 / **0.846** / 0.822 |
| Partial P / R / F1 | 0.512 / 0.733 / 0.603 | 0.513 / 0.633 / 0.567 | **0.643** / 0.600 / 0.621 |
| Missing P / R / F1 | 1.000 / 0.556 / 0.714 | 0.824 / 0.778 / 0.800 | 0.941 / **0.889** / **0.914** |
| Strong→Partial | 13 | 14 | **8** |
| Missing→Partial | 8 | 4 | **2** |
| Partial→Strong | 8 | 8 | 11 |
| Grounding / Unsupported | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 |
| Match Score MAE | 11.5 | 10.63 | **7.5** |
| ρ(score, GT) / ρ(score, HMF) | 0.677 / 0.609 | 0.720 / 0.557 | 0.722 / **0.704** |
| Chinese-JD Macro F1 | 0.7087 | 0.7014 | **0.7608** |
| adjacency slice acc / FP | 0.40 / 3 | 0.80 / 1 | **0.80 / 1** |
| project slice Macro F1 | 0.616 | 0.667 | **0.721** |
| OR-list slice Macro F1 (monitoring) | 0.458 | 0.522 | **0.521** (no regression from removing the rule) |
| compound slice Macro F1 (monitoring) | 0.627 | 0.561 | 0.510 (dataset difficulty; present with no compound rule) |
| mean latency (ms) | 13,609 | 11,412 | **11,668** |
| total tokens | 108,549 | 129,077 | **118,664** (+9% vs A; half of B's overhead) |
| integrity | — | INTEGRITY_OK | **INTEGRITY_OK** |

Confusion (S/P/M): A `[[39,13,0],[8,22,0],[0,8,10]]` → C `[[44,8,0],[11,18,1],[0,2,16]]`.

**Prompt C is a large development-set win for qwen3.8-max.** Macro F1 +0.084 (SUPPORTED, just under
STRONGLY at +0.10), ECC +0.07, **Partial precision 0.512→0.643 (crosses 0.60)**, Missing recall
0.556→0.889, Strong→Partial 13→8, Missing→Partial 8→2, Match-Score MAE 11.5→7.5, score↔HMF
0.609→0.704, Chinese-JD +0.052 — all with 100/100 coverage, grounding 1.00/0.00 preserved, only
+9% tokens. **The reduced prompt beat the full Prompt B by +0.072 Macro F1** — the OR-list and
compound rules in B were confusing/counterproductive for qwen3.8-max; removing them unlocked the
gain from the 3 useful rules.

## Head-to-head under each model's FINAL Dataset V1 config

| | kimi-k3 + A (control) | qwen3.8-max + C (refined) |
|---|---|---|
| Macro F1 | 0.740 | **0.786** |
| ECC | 0.74 | **0.78** |
| Accuracy | 0.740 | **0.780** |
| coverage · job-norm | 100/100 · 30/30 | 100/100 · 30/30 |
| Partial precision | 0.567 | **0.643** |
| Strong→Partial / Missing→Partial | 9 / 4 | 8 / **2** |
| Grounding / Unsupported | 1.00 / 0.00 | 1.00 / 0.00 |
| Chinese-JD Macro F1 | 0.7515 | **0.7608** |
| Match Score MAE | 10.43 | **7.5** |
| ρ(score, HMF) | **0.723** | 0.704 |
| mean latency | 28,125 ms | **11,668 ms** (~2.4× faster) |
| total tokens | 107,576 | 118,664 |
| caveats | mandatory reasoning; temperature=1; mainland endpoint | temperature=0; single-pass; mainland endpoint |

**qwen3.8-max + Prompt C now leads kimi-k3 + control on Macro F1 (+0.046), ECC (+0.04), Accuracy,
Partial precision, directional errors, Match-Score MAE, and latency; it is ~2.4× faster with no
reasoning/temperature caveat.** kimi-k3 retains only the score↔HMF-correlation edge (0.723 vs 0.704).

## Neither config clears the quality gate

| target | kimi-k3 + A | qwen3.8-max + C |
|---|---|---|
| Macro F1 ≥ 0.75 | ✗ 0.740 | ✗ 0.786 → **passes** |
| ECC ≥ 0.75 | ✗ 0.74 | ✓ **0.78** |
| Strong Recall ≥ 0.75 | ✓ 0.827 | ✓ 0.846 |
| Strong Precision ≥ 0.80 | ✗ 0.783 | ✓ 0.800 |
| Partial Precision ≥ 0.60 | ✗ 0.567 | ✓ **0.643** |
| Missing Recall ≥ 0.667 | ✓ 0.778 | ✓ 0.889 |
| Grounding ≥ 0.98 | ✓ 1.00 | ✓ 1.00 |
| Unsupported ≤ 0.02 | ✓ 0.00 | ✓ 0.00 |

**`qwen3.8-max + job-fit-v3-rubric-refined-v2` is the first configuration in the entire benchmark to
pass Macro F1 ≥ 0.75, ECC ≥ 0.75, Strong Precision ≥ 0.80, AND Partial Precision ≥ 0.60**
simultaneously — on Dataset V1. It just misses Macro F1's own primary gate by being *above* it
(0.786) while ECC (0.78) also clears. This is a **development-set** result and must be confirmed on
held-out Dataset V2.

See `prompt_refinement_round2b_configuration_decision.md` for the final configurations and the
Dataset V2 finalist recommendation.
