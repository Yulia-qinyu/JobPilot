# V2-Synthetic held-out error analysis — kimi-k3 + Control / Prompt A (job-fit-v3-matchable-only)

Behavioral stress-test evidence — **NOT real-world performance estimation. Never merged with V2-Real.**

## A. All-matchable (98 rows; mostly scenario-derived GT)
- Macro F1 **0.8112** · ECC **0.8367** · accuracy 0.8367
- per-class F1: S 0.92 / P 0.7241 / M 0.7895 · grounding 1.0

## B. Human-reviewed probe subset (20 S/P/M rows; B01 eligibility excluded)
- Macro F1 **0.8362** · ECC **0.85** · accuracy 0.85

## C. Per-scenario category (probe subset where available)

| category | probe n | accuracy | errors | dominant confusion | source |
|---|---|---|---|---|---|
| technology_adjacency | 3 | 0.3333 | 2 | Missing->Partial | human_reviewed_probe |
| project_vs_formal_work | 1 | 1.0 | 0 | — | human_reviewed_probe |
| strong_partial_boundary | 3 | 1.0 | 0 | — | human_reviewed_probe |
| partial_missing_boundary | 3 | 0.6667 | 1 | Missing->Partial | human_reviewed_probe |
| or_alternative | 2 | 1.0 | 0 | — | human_reviewed_probe |
| compound | 5 | 1.0 | 0 | — | human_reviewed_probe |
| role_core_mismatch | 3 | 1.0 | 0 | — | human_reviewed_probe |

## Probe disagreements (human-reviewed subset)

- D08 · partial_missing_boundary — GT **Missing** / pred **Partial** — 有开放平台 / 插件生态 / MCP 建设经验
- A01 · technology_adjacency — GT **Missing** / pred **Partial** — 具备图文 / 视频 / 语音多模态大模型产品经验
- A08 · technology_adjacency — GT **Partial** / pred **Strong** — 有模型效果评估经验

- mean latency 22393.2 ms · median 21953.5 · p95 30109.7
- reliability: 50/50 ok · first-pass 50/50 · retries 0
