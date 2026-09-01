# Benchmark Round 1 — Fixed-Prompt Model Comparison — Results

Experiment: only the model identifier varies. Same Dataset V1, Ground Truth v2 (`52cda176…`),
100 matchable requirements, frozen 30-item evidence snapshot, `job-fit-v3-matchable-only` prompt
(`e99ed027…`, byte-identical), `fit-analysis-wire-v2` schema, temperature 0, `max_tokens` 4096, one
semantic call per job, production `_normalize_matches`, production `MatchScoreService`, join key
`(job_id, requirement_id)`. Ground Truth loaded only after each candidate's raw predictions were
persisted.

| candidate | status |
|---|---|
| `claude-sonnet-4-5-20250929` | **REFERENCE** — reused from Baseline V1, **not rerun**. Metrics recomputed offline from the frozen `job_match_baseline_claude_current_v1_predictions.json` with identical metric code (matches the frozen baseline exactly). |
| `claude-haiku-4-5-20251001` | **RAN — 30/30 calls, `INTEGRITY_OK`.** |
| `claude-opus-5` | **BLOCKED — not executable under the fixed contract.** All 30 calls rejected HTTP 400 `invalid_request_error`: `` `temperature` is deprecated for this model. `` The production client hard-codes `temperature=0` on every `messages.parse` call; Opus 5 rejects any request containing `temperature`. Sending the fixed contract to Opus 5 would require a **production code change** (forbidden). **Stopped — no silent fix, no retry, no production change.** See `benchmark_round1_integrity_opus-5.json`. 0 tokens billed (rejected pre-inference). |

## Total new semantic calls

- Haiku 4.5: **30** (all succeeded)
- Opus 5: **30 attempted, 0 succeeded** (all HTTP 400 at request validation)
- Reference Sonnet: **0** (reused)
- **Total billed model inference: 30 calls (Haiku only).**

## Three-metric headline (two models; Opus 5 has no data)

| metric | Sonnet 4.5 (reference) | Haiku 4.5 | Δ vs Sonnet |
|---|---|---|---|
| **Macro F1** (primary) | **0.6919** | **0.6785** | **−0.013** — *regression*, "not compelling" band |
| **Effective Correct Coverage** | 0.62 | **0.65** | +0.03 (entirely from 100/100 coverage) |
| requirements reconciled | 91 / 100 | **100 / 100** | +9 |
| job normalization success | 29 / 30 | **30 / 30** | +1 |
| Accuracy (reconciled) | 0.6813 | 0.6500 | −0.031 |

## Per-class comparison

| class | metric | Sonnet 4.5 | Haiku 4.5 |
|---|---|---|---|
| **Strong** | precision | 0.879 | **0.929** |
| | recall | **0.630** | 0.500 ← collapsed |
| | F1 | **0.734** | 0.650 |
| **Partial** | precision | **0.477** | 0.456 |
| | recall | 0.778 | **0.867** |
| | F1 | 0.591 | **0.598** |
| **Missing** | precision | 0.857 | **0.867** |
| | recall | 0.667 | **0.722** |
| | F1 | 0.750 | **0.788** |

## Confusion matrices (GT rows × Prediction cols: Strong / Partial / Missing)

**Sonnet 4.5** (91 reconciled): `[[29,17,0],[4,21,2],[0,6,12]]`
**Haiku 4.5** (100 reconciled): `[[26,26,0],[2,26,2],[0,5,13]]`

Both models compress toward Partial. Haiku compresses **harder**: **26** GT-Strong → Partial vs
Sonnet's 17. Neither model produces a single Strong↔Missing confusion.

## Directional errors

| transition | Sonnet 4.5 | Haiku 4.5 |
|---|---|---|
| **Strong → Partial** | 17 | **26** (worse) |
| Strong → Missing | 0 | 0 |
| Partial → Strong | 4 | **2** (fewer overclaims) |
| Partial → Missing | 2 | 2 |
| Missing → Strong | 0 | 0 |
| **Missing → Partial** | 6 | **5** (slightly better) |

**The central Round 1 question — "does a candidate reduce Strong→Partial without increasing
Missing→Partial?"** Haiku 4.5 does the **opposite**: it *increases* Strong→Partial (17 → 26) while
holding Missing→Partial roughly flat (6 → 5). It is more globally conservative, not better calibrated.

## Slice comparison

| slice | n | Sonnet 4.5 acc | Haiku 4.5 acc |
|---|---|---|---|
| OR-list | 18 | 0.444 | **0.611** |
| technology adjacency (GT Missing) | 5 | 0.200 | **0.600** |
| project-based evidence | ~67–71 | **0.651** | 0.597 |
| formal-work-experience | 11 | 0.364 | **0.545** |
| compound | 13 | **0.750** | 0.462 |
| proficiency / depth | 11 | 0.667 | **0.727** |
| domain-specific | 11 | 0.500 | **0.545** |
| small-matchable jobs (≤3) | 51 | **0.686** | 0.647 |
| one-requirement jobs | 4 | 0.750 | 0.750 |
| mismatched-control jobs | 13 | 0.615 | **0.769** |

Haiku's slice wins (OR-list, adjacency, formal-work, mismatched-control) are all consequences of
being **more conservative** — it says Partial/Missing more often, which happens to be right on
adjacency/OR-Missing rows but wrong on the far larger set of GT-Strong project rows (project slice
*regresses* 0.651 → 0.597; compound regresses 0.750 → 0.462). n on most slices is small (5–18);
treat these as directional, not decisive.

## Adjacency false positives (GT Missing → Partial/Strong on a specialised-capability requirement)

Sonnet 4.5: **4** · Haiku 4.5: **2**. Haiku over-credits technology adjacency less — again a
by-product of global conservatism.

## Project-vs-work

| | Sonnet 4.5 | Haiku 4.5 |
|---|---|---|
| project **under**-credited | 8 | **12** (worse) |
| project **over**-credited | 8 | 7 |

Haiku under-credits direct project evidence more often — consistent with its collapsed Strong recall.

## Grounding

| | Sonnet 4.5 | Haiku 4.5 |
|---|---|---|
| Grounding Rate | 1.000 | 1.000 |
| Unsupported Match Rate | 0.000 | 0.000 |
| Evidence-ID validity | 1.000 | 1.000 |
| Strong/Partial with zero evidence | 0.000 | 0.000 |
| Missing-with-evidence anomaly | 0.000 | 0.000 |

Both models are equally safe on grounding. **Grounding is not a differentiator and is not semantic
correctness** — Haiku, like Sonnet, cites only valid evidence and still mislabels 35 % of reconciled
rows.

## Schema / coverage

| | Sonnet 4.5 | Haiku 4.5 |
|---|---|---|
| raw schema parse success | 30 / 30 | 30 / 30 |
| job normalization success | **29 / 30** | **30 / 30** |
| requirement prediction coverage | 91 / 100 | **100 / 100** |
| duplicate requirement ids | 1 (lost a whole job) | **0** |
| omitted / hallucinated ids | 0 / 0 | 0 / 0 |
| invalid labels | 0 | 0 |

**Haiku 4.5's one clear win:** it did not emit a duplicate `requirement_id`, so it lost no job and
covered all 100 requirements. This is why its ECC (0.65) exceeds Sonnet's (0.62) despite lower
Macro F1.

## Match Score

| | Sonnet 4.5 | Haiku 4.5 | reference |
|---|---|---|---|
| jobs scored | 29 | 30 | — |
| MAE vs GT Match Score | 13.45 | 15.83 | — |
| median abs err | 12 | 16.5 | — |
| max abs err | 50 | 50 | — |
| jobs diff ≥ 20 | 8 | 12 | — |
| jobs diff ≥ 30 | 2 | 5 | — |
| Spearman(model score, GT score) | 0.707 | 0.807 | — |
| **Spearman(model score, Human Match Fit)** | 0.537 | **0.706** | GT ceiling **0.845** |

Haiku's Match Score tracks Human Match Fit **better** (0.706 vs 0.537) — but this is almost entirely
because Haiku scored all 30 jobs (Sonnet's 0.537 excludes the job it lost) and because Haiku's
extra Partials smooth the score. Per-requirement label accuracy is worse; the score-level correlation
gain is a coverage artifact, not a quality signal. MAE vs the GT Match Score is actually **worse**
for Haiku (15.83 vs 13.45).

## Human Match Fit correlations

- GT Match Score vs Human Match Fit: **0.845** (fixed reference ceiling; construct is sound).
- Sonnet 4.5 model score vs Human Match Fit: 0.537 (29 jobs).
- Haiku 4.5 model score vs Human Match Fit: 0.706 (30 jobs).

Even Haiku's 0.706 is well below the 0.845 achievable with correct labels — the residual is matcher
label error, not scoring design.

## Latency / tokens / cost

| | Sonnet 4.5 | Haiku 4.5 |
|---|---|---|
| mean latency / call | 21,068 ms | **10,337 ms** (2.0× faster) |
| P90 latency | 30,584 ms | **14,090 ms** |
| min / max | 8,681 / 35,983 | 4,939 / 18,863 |
| total runtime (30 calls) | 632,497 ms | **310,865 ms** |
| input tokens | 127,696 | 127,696 (identical prompt) |
| output tokens | 31,365 | 29,870 |
| total tokens | 159,061 | 157,566 |
| **verified cost (30 jobs)** | **$0.8536** ($3 / $15 per Mtok) | **$0.2770** ($1 / $5 per Mtok) — **3.1× cheaper** |
| cost / job | $0.0285 | $0.0092 |

Pricing source: Anthropic public pricing, verified 2026-09-01. **Opus 5 cost: `PENDING_VERIFIED_PRICING`** (no run, no trusted local pricing).

## Quality gates (pre-registered — not changed after results)

| gate | threshold | Sonnet 4.5 | Haiku 4.5 |
|---|---|---|---|
| Macro F1 ≥ 0.75 | | ✗ 0.692 | ✗ **0.679** |
| ECC ≥ 0.75 | | ✗ 0.62 | ✗ 0.65 |
| Grounding Rate ≥ 0.98 | | ✓ 1.000 | ✓ 1.000 |
| Unsupported Match Rate ≤ 0.02 | | ✓ 0.000 | ✓ 0.000 |
| Strong recall ≥ 0.75 | | ✗ 0.630 | ✗ **0.500** |
| Strong precision ≥ 0.80 | | ✓ 0.879 | ✓ 0.929 |
| Partial precision ≥ 0.60 | | ✗ 0.477 | ✗ 0.456 |
| Missing recall ≥ 0.667 | | ✓ 0.667 | ✓ 0.722 |
| no catastrophic schema pattern | | ✓ (1 job lost, at the ceiling) | ✓ (0 lost) |

**Neither model passes the Round 1 screening gate.** Haiku 4.5 fails it more clearly (Strong recall
0.50, Macro F1 0.679 — a regression vs the reference).

## Improvement size vs Sonnet (Macro F1 0.692)

Haiku 4.5: **−0.013** → below the `+0.02` "not compelling" band, and negative. **Not an improvement.**
Opus 5: no data.

---

## Pre-registered model-value interpretation

### A. Does Opus materially improve quality over Sonnet?
**Cannot be answered.** `claude-opus-5` is not runnable under the current fixed production matcher
contract — it rejects the hard-coded `temperature=0`. Testing it requires a production/transport
change that is out of scope for this experiment. **Open question.**

### B. Does Haiku retain enough quality to be a viable cheaper model?
**Not as a drop-in replacement.** Macro F1 regressed (−0.013) and Strong recall collapsed (0.63 →
0.50; 26 GT-Strong compressed to Partial). Haiku *is* materially cheaper (3.1×), faster (2×), and
more reliable at the system layer (100/100 coverage, 30/30 normalization, 0 duplicate ids), and its
job-level Match Score correlates better with Human Match Fit (0.706) — but that correlation gain is a
coverage/smoothing artifact, and its per-requirement label quality is worse. **Viable only for a
use case that explicitly accepts lower Strong recall for 3× lower cost; not for label fidelity.**

### C. Is model tier the dominant performance lever?
**The evidence available points to NO.** Moving *down* a tier (Sonnet → Haiku) at the identical
prompt did **not** fix — and slightly worsened — the core structural failures (Partial as an
uncertainty bucket, Strong→Partial compression, OR-list, adjacency). Both tiers exhibit the same
error shape. Moving *up* a tier (Opus 5) could not be tested. A definitive answer needs Opus 5, but
the two data points so far suggest the bottleneck is **prompt / rubric-rule communication**, not raw
model capability.

### D. Or is the next high-value experiment still the Prompt/Rubric Communication Ablation?
**Yes.** Two models at two capability tiers, same fixed prompt, same structural errors → the
indicated next step is the **Prompt/Rubric Communication Ablation** (add OR-list, adjacency,
project-vs-work, narrowest-unmet-subclaim rules to the prompt) on the current reference model
`claude-sonnet-4-5-20250929`. Optionally, first re-attempt `claude-opus-5` via an **eval-only** client
variant that omits `temperature` for models that require it (a TRANSPORT-level change, separately
re-baselined) if the up-tier data point is wanted before the ablation.

## Recommendation for the next experiment

1. **Proceed to the Prompt/Rubric Communication Ablation on `claude-sonnet-4-5-20250929`** — it is the
   highest-value next step and is directly supported by Round 1.
2. **Keep `claude-sonnet-4-5-20250929` as the production model and the reference baseline.** Do not
   adopt Haiku 4.5 (label-quality regression). Do not adopt Opus 5 (not evaluated).
3. **Optionally, before or in parallel:** build an eval-only client that drops `temperature` when the
   target model rejects it, re-run `claude-opus-5` as a *separate* TRANSPORT-variant benchmark with
   its own reference, and only then compare — never fold it into this fixed-contract table.
4. **Do not** treat Haiku's better Match-Score-vs-Human-Match-Fit correlation as a reason to switch —
   it is a coverage artifact.
