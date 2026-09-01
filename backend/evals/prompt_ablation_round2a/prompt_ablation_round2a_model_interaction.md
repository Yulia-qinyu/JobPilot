# Prompt Ablation Round 2A — Cross-Model Interaction & Causal Interpretation

## §29 — Cross-model interaction questions

**A. Does the same rubric-aligned prompt improve all three models?**
On Macro F1: all three move positive, all small — **Sonnet +0.032, kimi-k3 +0.027 (on 91 reconciled
requirements), qwen3.8-max +0.013**. None reaches the pre-registered +0.05 "clearly successful"
threshold. On ECC (coverage-aware): **Sonnet +0.04, qwen3.8-max 0.00, kimi-k3 −0.05** (kimi lost one
job's output under the longer prompt). So: a small positive on classification for all three, but
only Sonnet improves on both primary metrics without a downside.

**B. Which model benefits most?**
**claude-sonnet-4-5-20250929.** Largest Macro F1 gain (+0.032), largest ECC gain (+0.04), largest
OR-list gain (Macro F1 +0.254), adjacency FP −2, Missing recall +0.167, Strong recall +0.077,
Match-Score MAE −2.84, score↔HMF correlation +0.032 — all with no coverage or grounding loss. Sonnet
had the weakest calibration under the lean control contract (Strong→Partial 23, OR-list Macro F1
0.30) and had the most headroom for an explicit rubric to fix.

**C. Does Kimi remain the Top Quality candidate after Prompt B?**
On reconciled Macro F1, yes — 0.766 is still the highest of the three (Sonnet 0.707, qwen3.8-max
0.714). **But** under the treatment prompt kimi-k3's ECC fell to **0.69** (coverage 91/100) — below
qwen3.8-max (0.71) and Sonnet (0.70) — because of a single-job empty-output failure. Under the
**control prompt** kimi-k3 is a clean 100/100 at Macro F1 0.740. Verdict: kimi-k3 remains the
classification-quality leader **on the control prompt**; the rubric-aligned prompt is a reliability
risk for it and must be re-run before that conclusion is trusted with the treatment prompt.

**D. Does Qwen Max close the quality gap enough to become preferable due to lower latency/complexity?**
The raw Macro F1 gap did **not** close (kimi−qwen widened from ~0.038 to ~0.052 on reconciled
Macro F1). But qwen3.8-max now **leads ECC** (0.71 vs kimi 0.69 under treatment; 0.71 vs 0.74 under
control), runs **~2.5× faster** (11–14 s vs 28–29 s mean), uses fewer tokens, and carries **no
reasoning-mandatory or temperature=1 caveat**. For a cost/latency/operational-simplicity decision it
is the more attractive option; for maximum classification quality kimi-k3 (control prompt) still
leads.

**E. Does Sonnet recover under better rubric communication?**
**Partially.** Macro F1 0.6757 → 0.7073 (+0.032), ECC 0.66 → 0.70 (+0.04). This closes roughly half
the distance to qwen3.8-max's 0.702 / 0.71. Sonnet stays 3rd of 3 on Macro F1 and below the
quality gate, but the rubric-aligned prompt makes it a materially better version of itself.

**F. Are OR-list / adjacency / project-vs-work / compound errors materially reduced?**
- **Adjacency: YES for 2/3** — qwen3.8-max and Sonnet both went 0.40 → 0.80 slice accuracy, adjacency
  FP 3 → 1. kimi-k3 flat (already good).
- **Project-vs-work: YES for 2/3** — kimi-k3 (slice Macro F1 0.536 → 0.690) and Sonnet (0.638 →
  0.705). qwen3.8-max over-corrected (project under-credited 4 → 9).
- **OR-list: mixed** — Sonnet up sharply (0.30 → 0.554 Macro F1), qwen3.8-max slightly up, **kimi-k3
  down** (0.736 → 0.562).
- **Compound: WORSE for all three** (slice Macro F1 −0.02 to −0.11). The "narrowest unmet subclaim"
  rule as worded is net-negative on Dataset V1.
Overall: adjacency and project errors are materially reduced for most models; OR-list is model-
dependent; compound regressed. **Not a clean across-the-board reduction.**

**G. Does Partial Precision finally exceed 0.60 for any model?**
**No.** Treatment Partial precision: kimi-k3 0.571 (from 0.567), qwen3.8-max 0.513 (from 0.512),
Sonnet 0.512 (from 0.462 — the largest absolute gain). The **0.60 ceiling on Partial precision holds
under the rubric-aligned prompt for every model.**

## Calibration test (§22)

Desired direction: Strong→Partial ↓, Missing→Partial ↓, without large Strong↔Missing two-step errors.

| model | S→P | M→P | P→S | P→M | S→M | verdict |
|---|---|---|---|---|---|---|
| qwen3.8-max | 13 → 14 (+1) | 8 → 4 (**−4**) | 8 → 8 | 0 → 3 (+3) | 0 → 0 | M→P improved; S→P flat; small new P→M leakage |
| kimi-k3 | 9 → 11 (+2) | 4 → 4 (0) | 12 → 6 (**−6**) | 1 → 1 | 0 → 0 | Partial→Strong over-promotion cut hard; S→P slightly worse |
| claude-sonnet-4-5 | 23 → 18 (**−5**) | 5 → 2 (**−3**) | 2 → 3 (+1) | 4 → 6 (+2) | 0 → 1 (+1) | best: both S→P and M→P down; small P→M and one S→M leak |

**"Partial as a generic uncertainty bucket" is partially reduced** — most visibly for Sonnet (both
over-Partial directions down) and kimi-k3 (Partial→Strong down 12→6). No large Strong↔Missing
two-step errors appeared (Sonnet gained exactly one Strong→Missing). But Partial precision still
does not cross 0.60, so the bucket behaviour is reduced, not eliminated.

## §33 — Causal interpretation

**Status: CAUSALLY_SUPPORTED_BUT_SMALL / PARTIAL.**

The ablation is **direct causal evidence** that clearer rubric communication shifts model
calibration in the predicted direction on specific, named error types:
- adjacency false-positives fell for 2/3 models (the guardrail rule did what it was designed to do);
- Missing→Partial fell for qwen3.8-max (8→4) and Sonnet (5→2);
- Sonnet's OR-list interpretation improved sharply (Macro F1 +0.254) and its Strong recall rose
  +0.077 (Strong→Partial 23→18);
- kimi-k3's Partial→Strong over-promotion fell 12→6.

These are the errors the rules target, and they moved when only the prompt changed — so **rubric
communication is a real, causally-demonstrated contributor** to the calibration problem.

**But the magnitude on the primary metric is small.** Macro F1 improvements are +0.013 / +0.027 /
+0.032 — **none reaches +0.05 ("clearly successful") and none clears the quality gate.** The effect
is also **not uniformly positive**: the compound rule regressed all three models, qwen3.8-max
over-corrected on project evidence, kimi-k3 regressed on OR-lists and lost a job's coverage, and
Partial precision still tops out at 0.571.

**Conclusion:** rubric / task communication is a **real but partial and modest bottleneck**. It is
causally supported that clearer rubric wording reduces specific calibration errors, but clearer
wording **alone does not close the gap** to the quality target. It is **not** established that
prompt communication is *the dominant* cause of the errors, and no ~93%-causal or
PROMPT_CAUSE_PROVEN claim is made. The remaining gap likely involves model capability, dataset
difficulty (especially compound and formal-work requirements), and rule wording that still needs
iteration (compound rule in particular).
