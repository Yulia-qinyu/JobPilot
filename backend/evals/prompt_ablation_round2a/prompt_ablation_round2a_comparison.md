# Prompt / Rubric Communication Ablation — Round 2A Comparison

**Control = Round 1B same-contract result (`job-fit-v3-matchable-only` + Section D 4-field), reused,
not rerun.** **Treatment = `job-fit-v3-rubric-aligned-v1`** (eval-only; control instruction block +
one inserted `ADJUDICATION RULES` block of 5 frozen rules; production `requirement_matcher.py`
unchanged, SHA `e99ed027…`). Everything else identical: Dataset V1, 30 jobs, 100 matchable
requirements, Ground Truth V2, frozen evidence, model ids, transports, reasoning/temperature
policies, `max_tokens=4096`, one call/job, `_normalize_matches`, `MatchScoreService`, join key,
metrics. **90 new inference calls** (3 models × 30). Raw persisted before GT load on all 90.

Pre-ablation wording: **HYPOTHESIS_STRENGTHENED** (not PROMPT_CAUSE_PROVEN). This task tests the
causal hypothesis.

## Per-model control → treatment

### qwen3.8-max (COST_QUALITY_CANDIDATE) — hypothesis support: **NOT_SUPPORTED / negligible**

| metric | control | treatment | Δ |
|---|---|---|---|
| **Macro F1** | 0.7016 | 0.7142 | **+0.013** |
| **ECC** | 0.71 | 0.71 | 0.00 |
| Accuracy | 0.71 | 0.71 | 0.00 |
| Strong P / R / F1 | 0.830 / 0.750 / 0.788 | 0.826 / 0.731 / 0.775 | −0.004 / −0.019 / −0.013 |
| Partial P / R / F1 | 0.512 / 0.733 / 0.603 | 0.513 / 0.633 / 0.567 | +0.002 / **−0.100** / −0.036 |
| Missing P / R / F1 | 1.000 / 0.556 / 0.714 | 0.824 / 0.778 / 0.800 | −0.176 / **+0.222** / +0.086 |
| Strong→Partial | 13 | 14 | +1 |
| Missing→Partial | 8 | 4 | **−4** |
| Partial→Strong / Partial→Missing | 8 / 0 | 8 / 3 | 0 / +3 |
| Grounding / Unsupported | 1.00 / 0.00 | 1.00 / 0.00 | — |
| Coverage · job-norm | 100/100 · 30/30 | 100/100 · 30/30 | — |
| Match Score MAE | 11.5 | 10.63 | −0.87 |
| ρ(score, GT) / ρ(score, HMF) | 0.677 / 0.609 | 0.720 / 0.557 | +0.043 / **−0.053** |
| Chinese-JD Macro F1 | 0.7087 | 0.7014 | −0.007 |
| mean latency (ms) | 13,609 | 11,412 | −2,197 |
| total tokens | 108,549 | 129,077 | **+20,528 (+19%)** |
| integrity | — | **INTEGRITY_OK** | — |

Confusion (S/P/M): control `[[39,13,0],[8,22,0],[0,8,10]]` → treatment `[[38,14,0],[8,19,3],[0,4,14]]`.
The rubric halved Missing→Partial (8→4) and fixed adjacency false-positives, but pushed Partial
recall down (0.733→0.633) and cut score↔HMF correlation. Net Macro F1 essentially unchanged.

### kimi-k3 (TOP_QUALITY_CANDIDATE) — hypothesis support: **WEAKLY_SUPPORTED on classification, OFFSET by a coverage regression**

| metric | control | treatment | Δ |
|---|---|---|---|
| **Macro F1** (on reconciled) | 0.7396 (100 reqs) | 0.7661 (**91 reqs**) | +0.027 (not comparable base) |
| **ECC** | 0.74 | **0.69** | **−0.05** |
| Accuracy (on reconciled) | 0.740 | 0.758 | +0.018 |
| Coverage · job-norm | 100/100 · 30/30 | **91/100 · 29/30** | −9 reqs · −1 job |
| Strong P / R / F1 | 0.782 / 0.827 / 0.804 | 0.854 / 0.761 / 0.805 | +0.072 / **−0.066** / +0.001 |
| Partial P / R / F1 | 0.567 / 0.567 / 0.567 | 0.571 / 0.741 / **0.645** | +0.005 / +0.174 / **+0.078** |
| Missing P / R / F1 | 0.933 / 0.778 / 0.849 | 0.933 / 0.778 / 0.849 | 0 / 0 / 0 |
| Strong→Partial | 9 | 11 | +2 |
| Missing→Partial | 4 | 4 | 0 |
| Partial→Strong | 12 | 6 | **−6** |
| Grounding / Unsupported | 1.00 / 0.00 | 1.00 / 0.00 | — |
| Match Score MAE | 10.43 | 10.66 | +0.23 |
| ρ(score, GT) / ρ(score, HMF) | 0.652 / 0.723 | 0.699 / 0.722 | +0.047 / −0.001 |
| Chinese-JD Macro F1 | 0.7515 | 0.7698 | +0.018 |
| mean latency (ms) | 28,125 | 29,440 | +1,315 |
| total tokens (reasoning) | 107,576 (3,370) | 129,530 (5,218) | **+21,954 (+20%)** |
| integrity | — | **INTEGRITY_OK** | — |

Confusion (S/P/M): control `[[43,9,0],[12,17,1],[0,4,14]]` → treatment `[[35,11,0],[6,20,1],[0,4,14]]`.
**One job (`tencent:2047239002926510080`, 9 requirements) returned empty / non-JSON content under
the longer treatment prompt** (`json_parse_error`; HTTP 200; `total_retries=0`; single-job, not a
systematic failure) → coverage 91/100, ECC 0.74→0.69. On the requirements it *did* answer, the
rubric improved Partial calibration markedly (Partial F1 +0.078; Partial→Strong over-promotion 12→6)
but Strong recall fell and OR-list regressed (see rule slices). **The treatment prompt is a
reliability risk for kimi-k3 and needs a confirming re-run before any adoption.**

### claude-sonnet-4-5-20250929 (INCUMBENT_CONTROL) — hypothesis support: **WEAKLY_SUPPORTED (cleanest positive)**

| metric | control | treatment | Δ |
|---|---|---|---|
| **Macro F1** | 0.6757 | 0.7073 | **+0.032** |
| **ECC** | 0.66 | 0.70 | **+0.04** |
| Accuracy | 0.66 | 0.70 | +0.04 |
| Coverage · job-norm | 100/100 · 30/30 | 100/100 · 30/30 | — |
| Strong P / R / F1 | 0.935 / 0.558 / 0.699 | 0.917 / 0.635 / 0.750 | −0.019 / **+0.077** / +0.051 |
| Partial P / R / F1 | 0.462 / 0.800 / 0.585 | 0.512 / 0.700 / 0.592 | **+0.051** / −0.100 / +0.007 |
| Missing P / R / F1 | 0.765 / 0.722 / 0.743 | 0.696 / 0.889 / 0.780 | −0.069 / **+0.167** / +0.038 |
| Strong→Partial | 23 | 18 | **−5** |
| Missing→Partial | 5 | 2 | **−3** |
| Partial→Strong / Partial→Missing / Strong→Missing | 2 / 4 / 0 | 3 / 6 / 1 | +1 / +2 / +1 |
| Grounding / Unsupported | 1.00 / 0.00 | 1.00 / 0.00 | — |
| Match Score MAE | 14.87 | 12.03 | **−2.84** |
| ρ(score, GT) / ρ(score, HMF) | 0.746 / 0.647 | 0.814 / 0.679 | +0.068 / **+0.032** |
| Chinese-JD Macro F1 | 0.6694 | 0.7026 | **+0.033** |
| mean latency (ms) | 18,865 | 19,881 | +1,016 |
| total tokens | 151,264 | 174,329 | **+23,065 (+15%)** |
| verified cost (30 jobs) | $0.766 | $0.846 | +$0.08 |
| integrity | — | **INTEGRITY_OK** | — |

Confusion (S/P/M): control `[[29,23,0],[2,24,4],[0,5,13]]` → treatment `[[33,18,1],[3,21,6],[0,2,16]]`.
This is where the hypothesis holds best: the rubric raised Strong recall (0.558→0.635, S→P 23→18),
raised Partial precision (0.462→0.512, the biggest absolute Partial-P gain of the three), raised
Missing recall (0.722→0.889, M→P 5→2), sharply improved OR-list (Macro F1 0.30→0.554) and adjacency
(0.40→0.80), and improved Match-Score MAE (−2.84) and score↔HMF correlation (+0.032) — all with **no
coverage or grounding loss**. Trade-offs: Partial recall −0.10, Missing precision −0.069, compound
slice regressed, +15% tokens.

## Summary deltas

| model | Δ Macro F1 | band | Δ ECC | Δ Acc | Δ Strong R | Δ Strong P | Δ Partial P | Δ Partial R | Δ Missing R | Δ S→P | Δ M→P | Δ MS MAE | Δ ρ(score,HMF) | Δ Chinese-JD mF1 | Δ tokens | coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.8-max | **+0.013** | NOT_SUPPORTED | 0.00 | 0.00 | −0.019 | −0.004 | +0.002 | −0.100 | **+0.222** | +1 | **−4** | −0.87 | **−0.053** | −0.007 | +20.5k | 100/100 |
| kimi-k3 | +0.027¹ | WEAKLY_SUPPORTED¹ | **−0.05** | +0.018 | −0.066 | +0.072 | +0.005 | +0.174 | 0 | +2 | 0 | +0.23 | −0.001 | +0.018 | +22.0k | **91/100** |
| claude-sonnet-4-5 | **+0.032** | WEAKLY_SUPPORTED | **+0.04** | +0.04 | **+0.077** | −0.019 | **+0.051** | −0.100 | **+0.167** | **−5** | **−3** | **−2.84** | **+0.032** | **+0.033** | +23.1k | 100/100 |

¹ kimi-k3's Macro F1 delta is on 91 reconciled requirements vs the control's 100 — not a like-for-like base. Its coverage-aware ECC **fell 0.05**. Net: not clearly successful.

## Pre-registered success criteria (Macro F1 ≥ +0.05 AND no grounding degradation AND no catastrophic coverage loss)

| model | Macro F1 ≥ +0.05 | grounding preserved | coverage preserved | **clearly successful?** |
|---|---|---|---|---|
| qwen3.8-max | ✗ (+0.013) | ✓ (1.00 / 0.00) | ✓ (100/100) | **NO** |
| kimi-k3 | ✗ (+0.027 on reconciled) | ✓ (1.00 / 0.00) | ✗ (91/100; ECC −0.05) | **NO** |
| claude-sonnet-4-5 | ✗ (+0.032) | ✓ (1.00 / 0.00) | ✓ (100/100) | **NO** |

**No model is "clearly successful". No model clears the quality gate (Macro F1 ≥ 0.75, ECC ≥ 0.75).
No model reaches Partial precision 0.60** (best: kimi-k3 treatment 0.571).

See `prompt_ablation_round2a_rule_slices.md` for the OR-list / adjacency / project / formal-work /
compound slice deltas, `prompt_ablation_round2a_model_interaction.md` for the §29 cross-model
answers and the causal interpretation, and `prompt_ablation_round2a_recommendation.md` for the
post-ablation model recommendation and Dataset V2 finalists.
