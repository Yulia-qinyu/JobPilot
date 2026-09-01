# Round 1B — Pareto Frontier (with Sonnet Comparable Control; no weighted composite score)

Pareto-style review across four axes, per the manifest `shortlist_policy`. A model is **dominated**
if another model is at least as good on every axis and strictly better on one. No arbitrary weights.
**The model reference is now `SONNET_ROUND1B_COMPARABLE_CONTROL`** (same lean Section A + Section D
contract as the candidates). `SONNET_PRODUCTION_BASELINE` is shown separately as the
current-production-system state.

## Axis values (all Round 1B rows under the SAME contract)

| model | QUALITY (Macro F1 · Strong R · Partial P · Missing R · OR-list / adj / project) | RELIABILITY (ECC · coverage · schema · grounding) | EFFICIENCY (mean latency · total tokens · verified cost/job) | PRODUCT FIT (Chinese-JD Macro F1 · ops complexity · reasoning overhead · transport · stability) |
|---|---|---|---|---|
| **SONNET_ROUND1B_COMPARABLE_CONTROL** | 0.676 · **0.558** · 0.462 · 0.722 · **0.30** / 0.40 / 0.64 | 0.66 · 100/100 · 30/30 · 1.00 | 18.9 s · 151.3 k · **$0.0255 (verified)** | 0.669 · Anthropic (incumbent, simplest) · none · temp 0 · stable, 0 retries |
| **qwen3.8-max** | 0.702 · 0.750 · 0.512 · 0.556 · 0.46 / 0.40 / 0.62 | **0.71** · **100/100** · **30/30** · 1.00 | **13.6 s** · 108.5 k · pending | 0.709 · Alibaba DashScope mainland (region-locked key) · none (single-pass) · temp 0 · stable, 0 retries |
| **qwen3.8-flash** | 0.659 · 0.788 · 0.474 · 0.500 · 0.46 / 0.20 / 0.64 | 0.68 · 100/100 · 30/30 · 1.00 | **11.4 s** · **106.6 k** · pending | 0.672 · same as Qwen Max · none · temp 0 · stable, 0 retries |
| **deepseek-v4-pro** | 0.706⚠️ · 0.926⚠️ · 0.417⚠️ · 0.500⚠️ · 0.56(9) / 0.00 / 0.76(21) | **0.35** · **44/100** · **19/30** · 1.00 | **48.0 s** · **182.2 k** (83 k reasoning) · pending | 0.679(40) · DeepSeek OpenAI-compat · **MANDATORY reasoning, not disableable** · temp 0 · **UNSTABLE** (multi-minute transport stalls; 4 launch attempts) |
| **kimi-k3** | **0.740** · **0.827** · **0.567** · **0.778** · **0.74 / 0.60 / 0.65** | **0.74** · **100/100** · **30/30** · 1.00 | 28.1 s · 107.6 k · pending | **0.752** · Moonshot OpenAI-compat mainland · **MANDATORY reasoning** (low effort; +3.4 k tokens, +9 s) · **temp 1 required** · stable (1 transient retry) |

⚠️ DeepSeek QUALITY figures are over the 44/100 requirements it answered — not comparable.

## Dominance analysis (vs the Sonnet comparable control)

- **`deepseek-v4-pro` — DOMINATED (all axes).** ECC 0.35 (worst), 44 % coverage (worst), 48 s
  latency (worst), 182 k tokens (worst), unstable transport. High Strong precision/recall on the
  minority it answers does not rescue a system that leaves 56 % of requirements unscored.
  **Eliminated.**
- **`SONNET_ROUND1B_COMPARABLE_CONTROL` — WEAKLY non-dominated, but clearly not a leader.**
  - vs **kimi-k3**: kimi beats it on Macro F1 (+0.064), ECC (+0.08), Chinese-JD (+0.082),
    ρ(score,HMF) (+0.076), OR-list (0.74 vs 0.30), adjacency, Strong recall (0.827 vs 0.558),
    Missing recall. Sonnet-control retains only **latency** (18.9 s vs 28.1 s) and **Strong
    precision** (0.936 vs 0.782). → not strictly dominated by kimi (faster), but strictly worse on
    every quality/reliability axis.
  - vs **qwen3.8-max**: qwen-max beats it on Macro F1 (+0.026), ECC (+0.05), Partial F1, Chinese-JD
    (+0.039), latency (13.6 s vs 18.9 s), tokens (108 k vs 151 k), cost. Sonnet-control retains
    **Missing recall** (0.722 vs 0.556), **ρ(score,HMF)** (0.647 vs 0.609), **Strong precision**
    (0.936 vs 0.830), and **compound** slice. → not strictly dominated (Missing-recall / HMF-corr
    edges), but behind on the primary metrics.
  - **Verdict:** the incumbent survives on the frontier only via niche edges (latency vs kimi;
    Missing-recall + HMF-corr vs qwen-max) — it is the **weakest full-coverage model on Macro F1
    except qwen-flash, and last on ECC**. Retained as the **control**, not a contender.
- **`qwen3.8-flash` — WEAKLY non-dominated (cheapest/fastest only).** Lowest latency (11.4 s) and
  tokens (106.6 k), so not strictly dominated. But it is a **Macro F1 regression (−0.017 vs the
  comparable control)**, and `qwen3.8-max` beats it on essentially every quality/reliability metric
  for +2 k tokens / +2 s. Reason to keep it in view: it may recover under a rubric-aligned prompt.
- **`qwen3.8-max` — NON-DOMINATED.** Best EFFICIENCY of the credible models (13.6 s, 108 k, and it
  beats the Sonnet control on latency AND tokens AND cost-equivalent). Best Partial F1 (0.603).
  100 % coverage, 0 retries, single-pass, `temperature=0` — **no reasoning or temperature
  comparability caveat** (matches the incumbent's transport profile exactly). Genuine, if small,
  Macro F1 improvement (+0.026) over the same-contract Sonnet. Weaknesses: Missing recall (0.556)
  and ρ(score,HMF) (0.609, below the Sonnet control).
- **`kimi-k3` — NON-DOMINATED and QUALITY-leading.** Best Macro F1 (0.740, **+0.064 meaningful** vs
  the comparable control), best ECC (0.74), best Chinese-JD (0.752 — only model meeting that
  sub-gate), best Missing recall, best OR-list and adjacency, best directional profile (S→P 9,
  M→P 4), best ρ(score,HMF) (0.723). Costs: ~1.5× the Sonnet control's latency (28 s), mandatory
  low-effort reasoning (+3.4 k tokens), `temperature=1`, mainland-only endpoint. Token total still
  ~29 % below the Sonnet control.

## Frontier

```
QUALITY ↑
        kimi-k3  ●───────────────  (mF1 0.740 / ECC 0.74 / Chinese 0.752 ; 28 s, 108 k, temp=1, mand-reasoning)   ← quality + Chinese leader
                  \
                   \
        qwen3.8-max ●──────────    (mF1 0.702 / ECC 0.71 ; 13.6 s, 108 k, temp=0, single-pass)   ← best cost-quality; beats Sonnet control on speed+tokens+mF1
                     \
   Sonnet Comparable  ○ .........  (mF1 0.676 / ECC 0.66 ; 18.9 s, 151 k, $0.0255/job)  ← weakly non-dominated (niche edges only); the CONTROL
     Control          \
       qwen3.8-flash ●            (mF1 0.659 / ECC 0.68 ; 11.4 s, 106.6 k)  ← weakly non-dominated (cheapest); still a regression
                       .
       deepseek-v4-pro ✗          (ECC 0.35 ; 48 s, 182 k ; unstable)   ← dominated on every axis, ELIMINATED
                          → EFFICIENCY (faster / cheaper)

(separate, not on this frontier: SONNET_PRODUCTION_BASELINE — mF1 0.692 / ECC 0.62 / 91-100 coverage / full 7-field schema —
 current production system state, NOT the model control.)
```

**Non-dominated set:** `kimi-k3`, `qwen3.8-max`, `SONNET_ROUND1B_COMPARABLE_CONTROL` (niche edges),
`qwen3.8-flash` (cheapest corner only). **Dominated / eliminated:** `deepseek-v4-pro`.

## Product-fit / operational notes

- **Chinese product fit** (Dataset V1 27/30 Chinese-dominant): `kimi-k3` leads Chinese-JD Macro F1
  (0.752, +0.082 over the Sonnet control); `qwen3.8-max` second (0.709, +0.039). The Sonnet control
  is **last** on Chinese-JD Macro F1 among full-coverage models (0.669).
- **Operational complexity:** the Sonnet control is the simplest (incumbent Anthropic, `temperature=0`,
  no reasoning caveat). `qwen3.8-max/flash` and `kimi-k3` use mainland-China OpenAI-compat endpoints
  with region-locked keys. `kimi-k3` adds `temperature=1` + mandatory reasoning. `deepseek-v4-pro`
  is operationally unfit (repeated stalls + coverage collapse).
- **Reasoning overhead:** `kimi-k3` low-effort reasoning is cheap (+3.4 k tokens, +9 s vs Qwen).
  `deepseek-v4-pro` mandatory full reasoning is ruinous (+83 k tokens, +34 s, eats the answer
  budget).
