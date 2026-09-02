# Finalist Cost / Production-Economics Analysis (T5.5)

_Reads only the frozen T5 prediction artifacts. **Zero new API calls.** No prediction / GT / prompt / production change._

## 1. Pricing basis

**Unit prices are UNAVAILABLE / UNVERIFIABLE in this environment.** There is no pricing in the repo config (prior eval artifacts record `cost_status = PENDING_OFFICIAL_PRICING_VERIFICATION`), and `qwen3.8-max` / `kimi-k3` list prices cannot be established from local config or accessible provider documentation. Per the task rule *do not invent prices*, dollar cost is expressed as a **price-parameterised formula** plus a clearly-flagged **placeholder sensitivity grid**; every price-independent economic quantity is reported as measured.

| | provider / region | model | endpoint |
|---|---|---|---|
| A | Alibaba DashScope · mainland | qwen3.8-max | dashscope.aliyuncs.com/compatible-mode/v1 |
| B | Moonshot AI · mainland | kimi-k3 | api.moonshot.cn/v1 |

`cost_per_call_usd = (uncached_input·Pin + cached_input·Pcache + output·Pout) / 1e6`  — supply verified `Pin / Pcache / Pout` (USD per 1M tokens) for each provider to obtain a bill.

## 2. Actual token-usage coverage

**116 / 116 calls carry complete usage metadata** (prompt, completion, total; cached-input nested in `prompt_tokens_details`; reasoning nested in `completion_tokens_details` for kimi). No field is missing; no token count is estimated. qwen does **not** report reasoning tokens (none used).

### Per-job token workload (mean)

| | qwen · V2-Real | kimi · V2-Real | qwen · V2-Synthetic | kimi · V2-Synthetic |
|---|---|---|---|---|
| prompt tokens | 3400.6 | 3048.1 | 3162.9 | 2815.1 |
| · of which cached | 3072 (90%) | 192 (6%) | 1024 (32%) | 389.1 (14%) |
| completion tokens | 1002.5 | 970.1 | 613.3 | 596.8 |
| · of which reasoning | 0 | 98 | 0 | 79.6 |
| total tokens | 4403.1 | 4018.2 | 3776.2 | 3411.9 |

**Overall 58-call run per model** — qwen: prompt 185,351 (cached 41%), completion 38,683 (reasoning 0), total 224,034, mean/call 3862.7.  kimi: prompt 165,140 (cached 13%), completion 37,603 (reasoning 13%), total 202,743, mean/call 3495.6.

## 3. Cost per model / per job / projected (placeholder price grid)

⚠️ **GP-A / GP-B / GP-C are ILLUSTRATIVE placeholder prices, NOT qwen3.8-max or kimi-k3 pricing.** They demonstrate the calculation and its sensitivity. Numbers below are `USD` under those placeholders only.

| model · dataset | price point | cost / job | cost / 100 jobs | cost / 1,000 jobs | input comp. | output comp. |
|---|---|---|---|---|---|---|
| qwen · real | GP-A low | $0.00164 | $0.164 | $1.64 | $0.00044 | $0.00120 |
| qwen · real | GP-B mid | $0.00533 | $0.533 | $5.33 | $0.00132 | $0.00401 |
| qwen · real | GP-C high | $0.01532 | $1.532 | $15.32 | $0.00329 | $0.01203 |
| qwen · synthetic | GP-A low | $0.00169 | $0.169 | $1.69 | $0.00096 | $0.00074 |
| qwen · synthetic | GP-B mid | $0.00533 | $0.533 | $5.33 | $0.00287 | $0.00245 |
| qwen · synthetic | GP-C high | $0.01454 | $1.454 | $14.54 | $0.00719 | $0.00736 |
| kimi · real | GP-A low | $0.00233 | $0.233 | $2.33 | $0.00116 | $0.00116 |
| kimi · real | GP-B mid | $0.00737 | $0.737 | $7.37 | $0.00348 | $0.00388 |
| kimi · real | GP-C high | $0.02035 | $2.035 | $20.35 | $0.00871 | $0.01164 |
| kimi · synthetic | GP-A low | $0.00173 | $0.173 | $1.73 | $0.00101 | $0.00072 |
| kimi · synthetic | GP-B mid | $0.00541 | $0.541 | $5.42 | $0.00303 | $0.00239 |
| kimi · synthetic | GP-C high | $0.01473 | $1.473 | $14.73 | $0.00757 | $0.00716 |

Production projection uses **actual mean held-out token consumption per job** as the workload estimate (V2-Real ≈ 8 requirements-set → ~4.0–4.4k tokens/call; V2-Synthetic ≈ 2 matchable reqs/job → ~3.4–3.8k). A real production job's requirement count sits between these. **These are workload-based projections, not guaranteed bills.**

### Effective billable input tokens (cache-discount adjusted, 58-call run)

| cache treatment | qwen effective input | kimi effective input |
|---|---|---|
| no_discount | 185,351 | 165,140 |
| typical_0.25 | 128,519 | 149,396 |
| aggressive_0.10 | 117,153 | 146,247 |
| output tokens (billed as output) | 38,683 | 37,603 |

**qwen's Prompt-C instruction block is stable across calls → 41% overall / 90% on V2-Real prompt-cache hit. kimi's cache hit is 13% overall / 6% on V2-Real.** Under any documented context-cache discount, qwen's effective billable input is materially lower than kimi's despite qwen's longer nominal prompt; kimi additionally bills ~13% of completion as reasoning tokens (qwen: none). Output-token volume is near-parity.

## 4. Cost per correct requirement (token-denominated — price-independent)

| | qwen + Prompt C | kimi + Control |
|---|---|---|
| V2-Real correct requirements | 26 / 32 | 27 / 32 |
| jobs w/ successful structured output | 8 / 8 | 8 / 8 |
| raw total tokens / correct requirement | 1354.8 | 1190.6 |
| raw total tokens / job with structured output | 4403.1 | 4018.2 |
| cache-adjusted billable tokens / correct req (typical 0.25 cache) | 645.9 | 1147.9 |
| cache-adjusted billable tokens / correct req (aggressive 0.10 cache) | 504.1 | 1139.4 |

**On raw tokens** kimi is ~12% leaner per correct V2-Real requirement (1,191 vs 1,355). **On cache-adjusted billable tokens** the order flips: qwen ≈ 600–670 vs kimi ≈ 1,140–1,150 per correct requirement — roughly **half**, because ~90% of qwen's V2-Real input is cache-served.

### Incremental quality vs incremental spend (V2-Real)

- kimi's nominal V2-Real advantage = **+1 correct requirement out of 32** → +0.0223 Macro F1, +0.0313 ECC. Partial F1 is a tie (0.8235 vs 0.8276).
- With N = 8 jobs / 32 rows, one label flip ≈ 0.03 Macro F1 — the difference is **inside the noise**. There is **no reliable additional V2-Real quality to "buy"** by choosing the more token-heavy raw config.
- Direction of spend: on **effective billable tokens** qwen is the cheaper config (cache-served input); on **raw tokens** kimi is marginally leaner. A definitive $ figure needs verified unit prices.

## 5. Latency comparison

| | qwen + Prompt C | kimi + Control |
|---|---|---|
| V2-Real mean / p95 | **15.3s** / 17.8s | 34.1s / 58.8s |
| V2-Synthetic mean / p95 | **10.0s** / 13.3s | 22.4s / 30.1s |

qwen + Prompt C is **~2.2× faster** per call and has a far tighter p95 (17.8s vs 58.8s on V2-Real).

## 6. Reliability comparison

| | qwen + Prompt C | kimi + Control |
|---|---|---|
| first-pass success (58 calls) | **58/58** | 57/58 |
| final OK (58) | 58/58 | 58/58 |
| structured-output parse OK (58) | 58/58 | 58/58 |
| total retries (58) | 0 | 3 |
| transient failures | 0 | 1 (V2-Real HTTP 429 engine_overloaded, recovered on retry) |

Both reach 100% final structured-output success; qwen did so with zero retries.

## 7. Quality-vs-cost interpretation (quality-floor / product-efficiency framing)

**Quality floor — both configs pass:** V2-Real Macro F1 0.87 / 0.89, ECC 0.81 / 0.84, grounding 1.00, unsupported 0.00, structured-output 100%. Both are acceptable.

Among acceptable configs, the trade-off:

| dimension | verdict |
|---|---|
| V2-Real quality difference materially meaningful? | **No** — +1/32 correct requirement, inside N=8 noise (statistical tie). |
| Faster? | **qwen + Prompt C** (~2.2×). |
| More operationally reliable? | **qwen + Prompt C** (58/58 first-pass, 0 retries). |
| Cheaper for the observed workload? | **qwen + Prompt C on effective (cache-adjusted) billable tokens**; kimi marginally leaner on raw tokens. Exact $ pending verified prices; direction favours qwen because ~90% of its V2-Real input is cache-served and it emits no reasoning tokens. |
| Does the pricier option buy enough extra quality? | **No** — there is no reliable extra V2-Real quality to buy, and the synthetic stress test favours qwen (probe Macro F1 0.90 vs 0.84; technology-adjacency 1.00 vs 0.33). |
| Better production trade-off? | **qwen3.8-max + Prompt C.** |

## Recommendation vs T5

**Unchanged — and strengthened.** T5 recommended qwen3.8-max + Prompt C on robustness + latency + reliability, with a V2-Real classification tie. The cost layer adds: qwen is also cheaper on cache-adjusted billable tokens (or at worst near-parity), with a much tighter latency p95 and zero transient failures. kimi-k3 + Control remains a viable fallback (marginally leaner raw tokens, slightly higher V2-Real Strong-recall and lower Match-Score MAE), but does not offer a quality increment that justifies its ~2.2× latency and weaker adjacency robustness.

## Limitations

- **No verified unit prices** — all USD figures are placeholder-parameterised; the human must substitute verified DashScope-mainland and Moonshot-mainland list prices (and confirm list vs promotional).
- Cache-discount rates are provider-specific and not verified here; the effective-token comparison is shown at 1.00 / 0.25 / 0.10 multipliers.
- Workload basis = held-out mean tokens/call; a production job's requirement count (and thus tokens) will differ — V2-Real (~8 reqs) and V2-Synthetic (~2 matchable reqs) bracket it.
- N = 8 V2-Real jobs — cost-per-correct-requirement inherits that low statistical power.
- Latency measured from this environment to mainland endpoints; production network path may differ.
- No new calls, so no independent verification of steady-state cache behaviour or rate-limit headroom.
