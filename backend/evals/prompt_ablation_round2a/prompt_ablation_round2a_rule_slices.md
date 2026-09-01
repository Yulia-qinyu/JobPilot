# Prompt Ablation Round 2A — Rule-Specific Slice Analysis

Pre-registered slices (definitions reused verbatim from
`job_match_baseline_claude_current_v1_error_slices.csv` + the Round 1B runner; **not re-derived
after seeing results**). Control = Round 1B same-contract; Treatment = `job-fit-v3-rubric-aligned-v1`.

## OR-list slice (n = 18 requirements; targets Rule 1)

| model | control acc / Macro F1 | treatment acc / Macro F1 | Δ acc / Δ Macro F1 | control errs → treatment errs | directional change |
|---|---|---|---|---|---|
| qwen3.8-max | 0.444 / 0.458 | 0.500 / 0.522 | +0.056 / **+0.064** | 10 → 9 | M→P 4→3, S→P 5→5, P→S 1→1 |
| kimi-k3 | 0.778 / 0.736 | 0.611 / 0.562 | **−0.167 / −0.174** | 4 → 7 | M→P 3→4, P→S 1→2, S→P 0→1 |
| claude-sonnet-4-5 | 0.333 / 0.300 | 0.556 / 0.554 | **+0.222 / +0.254** | 12 → 8 | M→P 4→2, S→P 8→5 |

**Mixed.** Sonnet improved sharply (it had the worst OR-list handling and the rule helped most).
qwen3.8-max improved modestly. **kimi-k3 regressed** — it already handled OR-lists well (0.736) and
the explicit rule appears to have over-triggered alternative-branch crediting.

## Technology-adjacency slice (n = 5 requirements, all GT = Missing; targets Rule 2)

| model | control acc | treatment acc | Δ | adjacency false-positives (GT Missing → Partial/Strong) |
|---|---|---|---|---|
| qwen3.8-max | 0.40 | **0.80** | +0.40 | 3 → **1** |
| kimi-k3 | 0.60 | 0.60 | 0.00 | 2 → 2 |
| claude-sonnet-4-5 | 0.40 | **0.80** | +0.40 | 3 → **1** |

**Improved for 2/3.** The adjacency guardrail cut adjacency false-positives by two for both
qwen3.8-max and Sonnet (the models that were over-crediting general LLM/RAG evidence). kimi-k3 was
already the best here and did not move. (n = 5 — small; treat as directional.)

## Project-based-evidence slice (targets Rule 3)

| model | control n / acc / Macro F1 | treatment n / acc / Macro F1 | Δ acc / Δ Macro F1 | project over-credited (C → T) | project under-credited (C → T) |
|---|---|---|---|---|---|
| qwen3.8-max | 68 / 0.662 / 0.616 | 67 / 0.672 / 0.667 | +0.010 / +0.051 | 14 → 10 | 4 → **9** |
| kimi-k3 | 63 / 0.651 / 0.536 | 57 / 0.737 / **0.690** | **+0.086 / +0.154** | 16 → 9 | 4 → 2 |
| claude-sonnet-4-5 | 62 / 0.645 / 0.638 | 69 / 0.725 / **0.705** | **+0.080 / +0.067** | 5 → 5 | 8 → 7 |

**Improved for kimi-k3 and Sonnet** (both reduced over-crediting of project evidence where formal
work experience was requested, without over-swinging to under-credit). **qwen3.8-max over-corrected**
— project over-credited fell 14→10 but project *under*-credited rose 4→9, so the model now demotes
valid project evidence too aggressively; net slice Macro F1 up only +0.051.

## Formal-work-experience slice (n = 11 requirements; targets Rule 3)

| model | control acc | treatment acc | Δ | control errs → treatment errs |
|---|---|---|---|---|
| qwen3.8-max | 0.455 | 0.455 | 0.00 | 6 → 6 |
| kimi-k3 | 0.727 | 0.636 | −0.091 | 3 → 4 |
| claude-sonnet-4-5 | 0.364 | 0.455 | +0.091 | 7 → 6 |

**Roughly flat / small.** n = 11. Sonnet nudged up, kimi nudged down, qwen unchanged.

## Compound-requirement slice (n = 13 requirements; targets Rule 4)

| model | control acc / Macro F1 | treatment acc / Macro F1 | Δ acc / Δ Macro F1 |
|---|---|---|---|
| qwen3.8-max | 0.615 / 0.627 | 0.538 / 0.561 | **−0.077 / −0.066** |
| kimi-k3 | 0.615 / 0.626 | 0.583 / 0.604 | −0.032 / −0.022 |
| claude-sonnet-4-5 | 0.692 / 0.683 | 0.615 / 0.578 | **−0.077 / −0.105** |

**Regressed for all three.** The "narrowest unmet subclaim" rule pushed models to downgrade
compound requirements more often, but on this slice that produced *more* Strong→Partial and
Partial→Missing errors than it fixed. The compound rule as worded is net-negative on Dataset V1.

## Rule-by-rule verdict

| rule | intended effect | observed |
|---|---|---|
| 1 — OR-list semantics | fewer false downgrades on OR-lists | **helps the models that were weak (Sonnet ++, qwen +), hurts the model that was already strong (kimi −)** |
| 2 — adjacency guardrail | fewer GT-Missing → Partial false positives | **works: adjacency FP 3→1 for qwen & Sonnet; kimi flat (already good)** |
| 3 — project vs formal work | Strong for complete projects on direction reqs; ≤ Partial when formal work explicitly required | **helps kimi & Sonnet; qwen over-corrects (under-credits projects: 4→9)** |
| 4 — compound / narrowest unmet subclaim | fewer Strong on partially-supported compounds | **net-negative on Dataset V1 for all three (slice Macro F1 −0.02 to −0.11)** |
| 5 — Strong/Partial/Missing calibration | Partial stops being a generic uncertainty bucket | **partial success: Partial→Strong inflation drops for kimi (12→6); Missing→Partial drops for qwen (8→4) & Sonnet (5→2); Strong→Partial drops only for Sonnet (23→18). Partial precision still < 0.60 for every model.** |
