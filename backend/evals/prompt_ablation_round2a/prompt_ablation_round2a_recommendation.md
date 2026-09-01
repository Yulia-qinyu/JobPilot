# Prompt Ablation Round 2A — Post-Ablation Recommendation

**Development-set result (Dataset V1). Not a production decision. No production model or prompt
change is made from this task.** Dataset V1 remains development / model-selection / prompt-
development data. Dataset V2 remains the future held-out validation/test set and was not used.

## Category leaders after the ablation

| category | model | basis |
|---|---|---|
| **TOP QUALITY** | **kimi-k3** | Highest classification quality on both prompts — control: Macro F1 0.740 / ECC 0.74 / 100 coverage; treatment (reconciled): Macro F1 0.766. Best per-class balance (Strong F1 0.80, Missing F1 0.85). **Use on the CONTROL prompt** — the rubric-aligned prompt caused a one-job coverage failure (ECC 0.69) and an OR-list regression for kimi-k3 and must be re-run before it is trusted for this model. |
| **BEST COST-QUALITY** | **qwen3.8-max** | Macro F1 0.70–0.71 on either prompt, ECC 0.71, 100 % coverage, 0 retries, **~2.5× faster** (11–14 s mean) than kimi-k3, no reasoning-mandatory or temperature caveat (matches the incumbent transport). The rubric prompt does not help it (Macro F1 +0.013) but does not hurt reliability. |
| **INCUMBENT CONTROL** | **claude-sonnet-4-5-20250929** | The model most responsive to explicit rubric wording: +0.032 Macro F1, +0.04 ECC, +0.254 OR-list Macro F1, adjacency FP −2, Match-Score MAE −2.84, score↔HMF +0.032 — no coverage/grounding loss. Still 3rd on Macro F1 and below the gate, but a materially better version of itself under Prompt B. |

## Dataset V2 finalists

**Two finalists: `kimi-k3` and `qwen3.8-max`.** (Not all three — the results are not "too close to
decide": kimi-k3 leads classification quality by a clear margin; qwen3.8-max is the clean
cost/latency/operational choice; Sonnet is dominated on quality by both under the identical
contract.)

- **`kimi-k3`** — carry as the quality finalist. Flags travel with it: `reasoning_comparability_flag`
  (mandatory low-effort reasoning), `temperature_comparability_flag` (temperature = 1), mainland-only
  Moonshot endpoint, and the Round 2A one-job coverage blip under a longer prompt.
- **`qwen3.8-max`** — carry as the cost-quality finalist. No caveats; fastest credible model;
  ~2.5× lower latency than kimi-k3; ECC parity or better.
- **`claude-sonnet-4-5-20250929`** — remains the **control** through Dataset V2, not a finalist.
- **`qwen3.8-flash`** — dropped (Round 1B regression; not re-tested here).
- **`deepseek-v4-pro`** — remains eliminated.

## Prompt recommendation

**Primary prompt for Dataset V2 = the CONTROL (`job-fit-v3-matchable-only`).** Carry
**`job-fit-v3-rubric-aligned-v1` as a SECONDARY factor** to evaluate on Dataset V2:
- it materially improves Sonnet and is directionally correct on adjacency and project errors for
  most models;
- it is neutral-to-slightly-positive for qwen3.8-max (Macro F1 +0.013, no reliability cost);
- for kimi-k3 it needs a coverage-confirming re-run (the one-job empty-output failure) and a fix or
  removal of the **compound rule**, which regressed all three models (slice Macro F1 −0.02 to −0.11)
  and the **OR-list rule**, which over-triggered for kimi-k3.

**Do NOT adopt the treatment prompt to production from this task.** A Round 2B (compound-rule and
OR-list-rule iteration, plus a kimi-k3 coverage re-run) is the natural follow-up before the prompt
factor goes to Dataset V2.

## Is prompt / rubric communication now causally supported as a material bottleneck?

**Yes — causally supported, but modest and partial, not the sole or dominant cause.**
- **Causally supported:** changing only the instruction block moved the targeted calibration errors
  in the predicted direction (adjacency FP 3→1 for qwen3.8-max and Sonnet; Missing→Partial 8→4 and
  5→2; Sonnet OR-list Macro F1 +0.254; Sonnet Strong recall +0.077; kimi-k3 Partial→Strong 12→6).
- **Modest / partial:** Macro F1 gains are +0.013 / +0.027 / +0.032 — none reaches the +0.05
  "clearly successful" bar; no model clears the quality gate; **Partial precision still < 0.60 for
  every model**; the compound rule regressed all three; kimi-k3 lost coverage.
- **Not proven as the dominant cause.** No ~93 %-causal attribution. `PROMPT_CAUSE_PROVEN` is not
  claimed. The remaining gap likely involves model capability, genuine dataset difficulty (compound
  and formal-work requirements), and rule wording that still needs iteration.

**Practical read:** rubric communication is a real, cheap-to-address lever that is worth carrying
into Dataset V2 as a secondary factor — but the model choice (kimi-k3 vs qwen3.8-max) and further
rule iteration matter more than adopting Prompt B as-is.
