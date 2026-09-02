# V2-Synthetic held-out error analysis — qwen3.8-max + Prompt C (job-fit-v3-rubric-refined-v2)

Behavioral stress-test evidence — **NOT real-world performance estimation. Never merged with V2-Real.**

## A. All-matchable (98 rows; mostly scenario-derived GT)
- Macro F1 **0.7849** · ECC **0.7959** · accuracy 0.7959
- per-class F1: S 0.8764 / P 0.6875 / M 0.7907 · grounding 1.0

## B. Human-reviewed probe subset (20 S/P/M rows; B01 eligibility excluded)
- Macro F1 **0.903** · ECC **0.9** · accuracy 0.9

## C. Per-scenario category (probe subset where available)

| category | probe n | accuracy | errors | dominant confusion | source |
|---|---|---|---|---|---|
| technology_adjacency | 3 | 1.0 | 0 | — | human_reviewed_probe |
| project_vs_formal_work | 1 | 1.0 | 0 | — | human_reviewed_probe |
| strong_partial_boundary | 3 | 1.0 | 0 | — | human_reviewed_probe |
| partial_missing_boundary | 3 | 0.6667 | 1 | Partial->Missing | human_reviewed_probe |
| or_alternative | 2 | 1.0 | 0 | — | human_reviewed_probe |
| compound | 5 | 1.0 | 0 | — | human_reviewed_probe |
| role_core_mismatch | 3 | 0.6667 | 1 | Missing->Partial | human_reviewed_probe |

## Probe disagreements (human-reviewed subset)

- D03 · partial_missing_boundary — GT **Partial** / pred **Missing** — 独立承担过大型 AI Infra 系统的设计、开发与调测
- G01 · role_core_mismatch — GT **Missing** / pred **Partial** — 有私域社群 / SCRM 运营经验

- mean latency 9974.5 ms · median 9441.7 · p95 13321.2
- reliability: 50/50 ok · first-pass 50/50 · retries 0
