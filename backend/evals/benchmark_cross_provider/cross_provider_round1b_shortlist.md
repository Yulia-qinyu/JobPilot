# Round 1B — Shortlist & Prompt-Ablation Decision (with Sonnet Comparable Control)

**Development-set result (Dataset V1). Not a production selection. No production model change.**
All model-to-model comparison uses **`SONNET_ROUND1B_COMPARABLE_CONTROL`** (same lean Section A +
Section D contract). **`SONNET_PRODUCTION_BASELINE` is kept separately, unmodified**, as the
current-production-system reference.

## Category leaders (re-checked against the comparable control)

| category | candidate | why (vs the SAME-contract Sonnet control) |
|---|---|---|
| **Top Quality** | **kimi-k3** — CONFIRMED, and the margin grew | Macro F1 0.740 = **+0.064 (meaningful)** vs the comparable control (was +0.048 vs the production baseline). Best ECC (0.74, +0.08), best Chinese-JD (0.752, +0.082), best Missing recall (0.778), best OR-list (0.74 vs 0.30) and adjacency (0.60 vs 0.40), fewest Strong→Partial (9 vs 23) and Missing→Partial (4 vs 5), best model-score↔HMF correlation (0.723 vs 0.647, +0.076). |
| **Best Cost-Quality** | **qwen3.8-max** — CONFIRMED, now with a real (small) quality gain | Macro F1 0.702 = **+0.026 (small)** vs the comparable control — a genuine classification improvement, no longer "not compelling". ECC 0.71 (+0.05). Faster (13.6 s vs 18.9 s) and lighter (108.5 k vs 151.3 k tokens) than the Sonnet control. Best Partial F1 (0.603). Single-pass `temperature=0` — the **only** new candidate whose transport profile exactly matches the incumbent (no reasoning/temperature caveat). 0 retries. Caveat: Missing recall 0.556 and ρ(score,HMF) 0.609 are **below** the Sonnet control. |
| **Best Chinese Product-Fit** | **kimi-k3** — CONFIRMED | Chinese-JD Macro F1 **0.7515** — the **only** model meeting the 0.75 sub-target; +0.082 over the comparable control (which is last among full-coverage models at 0.669). qwen3.8-max second (0.709, +0.039). |
| **Most Reliable** | **kimi-k3** (ECC-led) — CONFIRMED; **qwen3.8-max** the zero-caveat alternative | kimi-k3: highest ECC (0.74), 100/100 coverage, 30/30 normalization, grounding 1.00, 1 transient retry. qwen3.8-max: ECC 0.71, same coverage/normalization/grounding, **0 retries**, lowest latency variance, no mandatory-reasoning/temperature flags. The Sonnet control's ECC (0.66) is **now last among full-coverage models** — the incumbent is no longer the reliability benchmark. |

**Eliminated on reliability:** `deepseek-v4-pro` — ECC **0.35**, **44/100** requirement coverage
(11/30 jobs emit reasoning but no answer within the fixed 4096-token budget), 48 s mean latency,
83 k reasoning tokens, repeated multi-minute transport stalls. Elimination stands regardless of the
Sonnet comparable-control result.

## §9 — Re-checked claims (under the identical contract)

| question | answer |
|---|---|
| Is Kimi K3 still the Top Quality candidate? | **Yes — more decisively.** Its Macro F1 lead over Sonnet grew from +0.048 (vs production baseline) to **+0.064 (vs comparable control) — a "meaningful" band**. It also leads ECC, Chinese-JD, Missing recall, OR-list, adjacency, directional errors, and score↔HMF correlation. |
| Is Qwen3.8 Max still the Best Cost-Quality candidate? | **Yes.** And its position improved: under the same contract it shows a genuine **+0.026 (small)** Macro F1 improvement (not just "not compelling"), plus +0.05 ECC, at ~30 % faster and ~28 % fewer tokens than the Sonnet control, with no transport caveats. |
| Does Sonnet remain dominated? | **Weakly non-dominated, but not a contender.** It is the **weakest full-coverage model on Macro F1 except qwen3.8-flash (0.676)** and **last on ECC (0.66)**. It survives on the frontier only via niche edges: lower latency than kimi-k3, and higher Missing recall + ρ(score,HMF) + Strong precision than qwen3.8-max. Retained as the **control**, not a shortlist contender for improvement. |
| True Kimi-vs-Sonnet Macro F1 delta under the same contract | **+0.064** (kimi-k3 0.740 vs comparable control 0.676) — vs +0.048 against the production baseline. |
| True ECC difference | **+0.08** (kimi-k3 0.74 vs comparable control 0.66); qwen3.8-max **+0.05** (0.71). |
| True Chinese-JD difference | **+0.082** (kimi-k3 0.752 vs comparable control 0.669); qwen3.8-max +0.039; qwen3.8-flash +0.002. |
| True HMF-correlation difference | **kimi-k3 +0.076** (0.723 vs comparable control 0.647). **qwen3.8-max −0.038** (0.609 — worse than the Sonnet control). qwen3.8-flash +0.020. |

## Top 3 shortlist for deeper evaluation

1. **kimi-k3** — quality + Chinese-fit leader; margin over the same-contract Sonnet is now
   "meaningful". Carry `reasoning_comparability_flag` and `temperature_comparability_flag` forward.
2. **qwen3.8-max** — cost-quality leader; the only new candidate whose transport profile matches the
   incumbent exactly; genuine (small) quality gain + reliability + speed. Watch the sub-baseline
   Missing recall and ρ(score,HMF).
3. **SONNET_ROUND1B_COMPARABLE_CONTROL** — incumbent **control** (already run under the Round 1B
   contract; use as the direct model reference). `SONNET_PRODUCTION_BASELINE` remains the separate
   product-current-state record.

**`qwen3.8-flash`** — retained as a *conditional* low-cost candidate, contingent on the Prompt
Ablation: still a Macro F1 regression (−0.017 vs the comparable control, smaller than before), but
the fastest/cheapest option. Round 1A's `claude-haiku-4-5` (Macro F1 0.679, ECC 0.65) is also a
regression and stays out. **`deepseek-v4-pro` — eliminated.**

**Deeper-evaluation plan:** repeat runs on the Top 3 (variance / stability), then the **Prompt /
Rubric Communication Ablation** on kimi-k3 + qwen3.8-max + the Sonnet control, then Dataset V2
held-out validation. **No model promoted to production from Round 1B.**

---

## §24 — Prompt-Ablation decision questions

**A. Is current Sonnet still competitive?**
As the **production system** (7-field schema): mid-pack — Macro F1 0.692, but ECC 0.62 (91/100
coverage) and ρ(score,HMF) 0.537 are weak. As a **model under the Round 1B contract**: it is the
weakest full-coverage model on Macro F1 except qwen3.8-flash (0.676) and last on ECC (0.66). It is
not obsolete (Missing recall, Strong precision, compound-slice, and — vs qwen-max — HMF-correlation
remain respectable) but it is **not a quality contender** on this dataset.

**B. Does Qwen Max materially improve semantic classification?**
Under the identical contract, **modestly yes**: +0.026 Macro F1 ("small" band, up from "not
compelling" vs the production baseline), plus +0.05 ECC and +0.039 Chinese-JD Macro F1. It also runs
faster and lighter than the Sonnet control with no transport caveats. Not a large gain, but a
genuine, clean improvement.

**C. Does Qwen Flash retain enough quality for a low-cost option?**
**Not currently.** −0.017 Macro F1 vs the comparable control (a regression, though smaller than the
−0.033 vs the production baseline), weakest compound (0.336 Macro F1) and adjacency (0.20) slices,
worst Partial→Strong inflation (12). It is the cheapest and fastest. Verdict: **conditional** —
re-test under the Prompt Ablation before using it anywhere.

**D. Does DeepSeek's mandatory reasoning produce enough quality gain to justify the latency/token
overhead?**
**No — decisively not.** Non-disableable reasoning consumes the entire fixed 4096-token output
budget on every ≥3-requirement job → reasoning emitted, **no answer** on 11/30 jobs → ECC 0.35, 44 %
coverage. Add 48 s mean latency, 83 k reasoning tokens, and repeated multi-minute transport stalls.
On the 44 requirements it answers, Strong F1 is 0.926, but the system is unusable. **Eliminated.**

**E. Does Kimi's mandatory low-effort reasoning + temperature=1 improve Chinese matching enough to
justify its latency/transport differences?**
**Yes.** Under the identical contract, kimi-k3 is the clear best model: **+0.064 Macro F1
(meaningful)**, **+0.08 ECC**, **+0.082 Chinese-JD Macro F1** (the only model meeting that
sub-gate), best Missing recall, best OR-list/adjacency, best directional profile, **+0.076
score↔HMF correlation**. Costs are modest and bounded: ~1.5× the Sonnet control's latency (28 s),
+3.4 k reasoning tokens (total still ~29 % below the Sonnet control), one required `temperature=1`,
and a mainland-only endpoint. The reasoning/temperature comparability flags must travel with it, but
the low-effort reasoning is **productive, not ruinous**.

**F. Does model capability appear to be the main bottleneck?**
**No — the evidence points elsewhere, but this is a HYPOTHESIS, not proven.** What is observed:
- **No model reaches Partial precision 0.60.** Six records — four providers plus *two different
  output contracts for the same Anthropic model* — all cluster at **0.42–0.57**
  (Sonnet-control 0.462, qwen-flash 0.474, Sonnet-production 0.477, qwen-max 0.512, deepseek 0.417,
  kimi-k3 0.567).
- **Every model over-produces the Partial class** in the same directions (Strong→Partial,
  Missing→Partial, Partial→Strong all persist across all models and both Sonnet contracts).
- **Changing only the output contract** (Sonnet 7-field → 4-field) shifted Sonnet's Macro F1 by
  −0.016 and Strong→Partial from 17 → 23 — i.e. *how the task is asked* changes the model's
  calibration, holding the model fixed.
- The best model still misses the 0.75 primary gate by only 0.01.

**Cross-model error convergence, plus the sensitivity of a fixed model to the output-contract shape,
strengthens the hypothesis that rubric / task communication is an important bottleneck.** This is
**HYPOTHESIS_STRENGTHENED**, not proven. The causal share of errors attributable to prompt
communication is **not established** and must be tested directly in the Prompt Ablation. Where model
capability clearly *does* help: OR-list interpretation (kimi 0.74 vs Sonnet-control 0.30) and
technology-adjacency discrimination (kimi 0.60 vs deepseek 0.00).

**G. Or should the next high-value experiment be the Prompt / Rubric Communication Ablation?**
**Yes — the Prompt / Rubric Communication Ablation is the next high-value experiment.** Model
selection alone buys at most +0.064 Macro F1 (kimi-k3) and does not clear the gate; every model and
both Sonnet contracts share the same Partial-precision ceiling and directional bias. Run the
ablation (`job-fit-v3` vs a rubric-aligned prompt: OR-list handling, project-vs-formal-work
weighting, technology-adjacency = Missing, Partial↔Strong threshold, compound-requirement rule) on
**kimi-k3 + qwen3.8-max + the Sonnet control**, then Dataset V2 held-out validation before any
production routing decision. **Do not implement prompt changes yet.**
