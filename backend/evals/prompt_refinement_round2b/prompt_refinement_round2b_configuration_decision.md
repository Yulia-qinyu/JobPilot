# Prompt Refinement Round 2B — Final Configuration Decision

**Development-set decision (Dataset V1). Not a production change.** Dataset V1 prompt development is
now frozen — no Round 2C. Dataset V2 remains held out.

## Decision-rule evaluation

### Kimi (§15)
Prefer Prompt C over the control **only if** coverage = 100/100 **AND** ECC ≥ 0.74 **AND** Macro F1
≥ 0.740 **AND** grounding not degraded.

| condition | Prompt C result | met? |
|---|---|---|
| coverage = 100/100 | 100/100 · 30/30 | ✓ |
| ECC ≥ 0.74 | 0.75 | ✓ |
| **Macro F1 ≥ 0.740** | **0.7225** | **✗** |
| grounding not degraded | 1.00 / 0.00 (unchanged) | ✓ |

**Conditions NOT met → select `kimi-k3` + `job-fit-v3-matchable-only` (control).** Prompt C restored
kimi-k3's coverage and pushed Partial precision above 0.60, but at a **−0.017 Macro F1 regression**:
the explicit rules over-push kimi-k3 to Strong (recall 0.83→0.90) and collapse Partial recall
(0.567→0.467). kimi-k3's calibration is best left un-instructed.

### Qwen (§16)
Prefer Prompt C over the control **if** coverage = 100/100 **AND** ECC ≥ 0.71 **AND** Macro F1
improves meaningfully **AND** grounding not degraded.

| condition | Prompt C result | met? |
|---|---|---|
| coverage = 100/100 | 100/100 · 30/30 | ✓ |
| ECC ≥ 0.71 | 0.78 | ✓ |
| Macro F1 improves meaningfully | **+0.084** (0.702 → 0.786) | ✓ |
| grounding not degraded | 1.00 / 0.00 (unchanged) | ✓ |

**Conditions MET → select `qwen3.8-max` + `job-fit-v3-rubric-refined-v2` (Prompt C).**

## KIMI_FINAL_V1_CONFIGURATION

| field | value |
|---|---|
| model | `kimi-k3` |
| prompt id | **`job-fit-v3-matchable-only`** (control) |
| transport | Moonshot `https://api.moonshot.cn/v1`; `temperature=1` (`MODEL_REQUIRED_VALUE`); `reasoning_mode=mandatory`; `reasoning_effort=low`; `response_format={"type":"json_object"}` + Section D 4-field output contract + `"Return the response as JSON."` (Moonshot adapter scope); `max_tokens=4096`; one non-streaming call per job |
| comparability flags | `reasoning_comparability_flag=true`, `temperature_comparability_flag=true` |
| expected Dataset V1 metrics | Macro F1 0.740 · ECC 0.74 · coverage 100/100 · Chinese-JD Macro F1 0.7515 · ρ(score, HMF) 0.723 · grounding 1.00 / 0.00 |

## QWEN_FINAL_V1_CONFIGURATION

| field | value |
|---|---|
| model | `qwen3.8-max` |
| prompt id | **`job-fit-v3-rubric-refined-v2`** (Prompt C — eval-only; adjacency + project-vs-formal-work + calibration rules; instruction-block SHA `7625ac37…`) |
| transport | Alibaba DashScope mainland `https://dashscope.aliyuncs.com/compatible-mode/v1`; `temperature=0`; `enable_thinking=false`; `response_format={"type":"json_object"}` + Section D 4-field output contract + `"Return the response as JSON."` (Qwen adapter scope); `max_tokens=4096`; one non-streaming call per job |
| comparability flags | none (single-pass, `temperature=0`) |
| expected Dataset V1 metrics | Macro F1 0.786 · ECC 0.78 · coverage 100/100 · Chinese-JD Macro F1 0.7608 · ρ(score, HMF) 0.704 · grounding 1.00 / 0.00 |

## Dataset V2 finalists

### PRIMARY_DATASET_V2_FINALIST — **`qwen3.8-max` + `job-fit-v3-rubric-refined-v2`**

This **reverses** the Round 1B / Round 2A primary (kimi-k3). Under each model's FINAL Dataset V1
configuration:

| | kimi-k3 + control | qwen3.8-max + Prompt C | Δ (qwen − kimi) |
|---|---|---|---|
| Macro F1 | 0.740 | **0.786** | **+0.046** |
| ECC | 0.74 | **0.78** | **+0.04** |
| Accuracy | 0.740 | **0.780** | +0.04 |
| Partial precision | 0.567 | **0.643** | +0.076 |
| Missing→Partial | 4 | **2** | −2 |
| Match Score MAE | 10.43 | **7.5** | −2.9 |
| Chinese-JD Macro F1 | 0.7515 | **0.7608** | +0.009 (≈ tied) |
| ρ(score, HMF) | **0.723** | 0.704 | −0.019 |
| mean latency | 28,125 ms | **11,668 ms** | **~2.4× faster** |
| transport caveats | mandatory reasoning; temperature=1 | none | simpler |

The task's condition — *"prefer Kimi as primary unless the refined experiment materially changes the
quality/reliability conclusion"* — **is triggered**: +0.046 Macro F1 and +0.04 ECC in
qwen3.8-max's favour, plus the first-ever pass of Macro F1 ≥ 0.75 / ECC ≥ 0.75 / Strong P ≥ 0.80 /
Partial P ≥ 0.60 together, plus ~2.4× lower latency and no reasoning/temperature caveats, is a
material change.

### SECONDARY_DATASET_V2_FINALIST — **`kimi-k3` + `job-fit-v3-matchable-only`**

The robust, un-tuned fallback: Macro F1 0.740 / ECC 0.74 / 100 % coverage with **no prompt tuning**,
and the best score↔Human-Match-Fit correlation (0.723). If qwen3.8-max's Dataset V1 gain does not
hold on held-out Dataset V2, kimi-k3 + control is the config to fall back to.

### Overfitting caveat

qwen3.8-max's +0.084 Macro F1 is a **development-set** result on the **final** allowed tuning
iteration. Prompt C's three rules (adjacency, project-vs-formal-work, calibration) were shaped from
Dataset V1 error analysis in Round 2A. The magnitude **must be confirmed on held-out Dataset V2**
before it is trusted; the Dataset V1 stop rule exists to bound exactly this risk. The Round 2B
result is a strong signal, not a settled outcome.

## Prompt-bottleneck status (unchanged discipline)

**REAL_BUT_PARTIAL_LEVER.** Round 2A causally demonstrated that changing rubric communication
changes matcher behaviour. Round 2B shows the effect is **model-specific and can be large**: for
qwen3.8-max a compact refined rubric produces a large development-set gain; for kimi-k3 any added
rubric block is net-negative. This is **not** evidence that the prompt is the sole or dominant
bottleneck — no such claim, no ~93%-causal attribution. Model choice and per-model prompt fit both
matter, and the compound slice regressed for qwen3.8-max even with no compound rule (genuine dataset
difficulty).

## Dataset V1 STOP

This is the **final** Dataset V1 prompt-development iteration. **No Round 2C. No further rule tuning
against Dataset V1. No more examples. No further failure-inspection-then-iterate.** Proceed to
Dataset V2 held-out validation with the two finalist configurations above.
