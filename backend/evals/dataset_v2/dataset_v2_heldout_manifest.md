# Dataset V2 — Reduced-Scope Held-Out Manifest

_Frozen 2026-09-02T12:45:23.079947+00:00_

| dataset | role |
|---|---|
| Dataset V1 | development / model-selection set (NOT held out) |
| Dataset V2-Real | **small held-out real-world validation set** |
| Dataset V2-Synthetic | behavioral challenge / stress-test set (NOT real-world performance estimation) |

Frozen finalists: `qwen3.8-max + job-fit-v3-rubric-refined-v2`, `kimi-k3 + job-fit-v3-matchable-only`.

## V2-Real

- Jobs: **16** — all provenance level **B (human_provenance_verified)**, `source_url_missing=true`.
- Known companies: {'字节跳动 (ByteDance)': 2, '水滴公司 (Waterdrop)': 1}  ·  company-unknown jobs: 13
- Role family: {'ai_product': 8, 'platform_enterprise_product': 5, 'strategy_growth_fintech_product': 1, 'mismatched_control': 1, 'general_product': 1}
- Career stage: {'campus_new_grad': 7, 'unknown': 8, 'experienced': 1}
- Language: {'zh': 16}
- Requirement candidates (heuristic, taxonomy DRAFT): **187**  → {'matchable': 170, 'eligibility': 11, 'subjective': 5, 'knowledge': 1}
- Matchable rows for GT: **170**  ·  human-reviewed GT: **0 / 170** (template ready, pending lightweight human pass)

## V2-Synthetic

- Jobs: **50**  ·  total probes: **65**
- Human-reviewed probes: **9** (9 high-risk round-1 decisions)
- Representative selected & pending: **12**
- Reviewed-or-selected per scenario category: {'strong_partial_boundary': 3, 'partial_missing_boundary': 3, 'compound': 5, 'technology_adjacency': 3, 'project_vs_formal_work': 2, 'or_alternative': 2, 'role_core_mismatch': 3}
- Scenario-derived-only probes: **56**
- Reporting split (never merged with V2-Real): **all-matchable / human-reviewed probe subset / per-scenario-category**.

## Limitations

- V2-Real is small (16 jobs) and provenance-level B (no source URLs); estimates carry wide uncertainty.
- V2-Real human GT is not yet produced — template only; requires a lightweight human pass.
- V2-Real taxonomy and Importance are heuristic drafts pending human confirmation; ambiguous Importance is a known limitation.
- V2-Synthetic: only 9 of 65 probes are human-reviewed; 12 are selected-and-pending; the rest are scenario-derived, not exhaustively human-verified.
- No exhaustive annotation was attempted — this is a credible AI Product Evaluation Case Study, not a production-grade benchmark.
