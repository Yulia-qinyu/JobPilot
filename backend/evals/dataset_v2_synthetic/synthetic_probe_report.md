# Dataset V2 Synthetic Challenge Set — Probe Report

Read-only analysis over the existing synthetic artifacts. Raw artifacts NOT modified. No model inference.

## Counts

- Total matchable requirements: **98**
- **Probe** matchable requirements: **59**
- Non-probe (filler/realism anchor) matchable requirements: **39**
- Eligibility requirements: 51  ·  of which B-category **eligibility probes**: **6**
- **Total probe requirements (matchable + eligibility): 65**
- Focused review row count: **65**

## Probe expected-label distribution (matchable probes only)

| label | count | share |
|---|---|---|
| Missing | 25 | 42% |
| Partial | 23 | 39% |
| Strong | 11 | 19% |

## Probe distribution by scenario category (matchable + eligibility probes)

| category | probe count |
|---|---|
| project_vs_formal_work | 14 |
| technology_adjacency | 14 |
| partial_missing_boundary | 10 |
| strong_partial_boundary | 10 |
| role_core_mismatch | 7 |
| compound | 5 |
| or_alternative | 5 |

## Focused-review tier sizes (priority order, deduplicated)

| tier | rows |
|---|---|
| A_scenario_requires_manual_review | 2 |
| B_compound_probes | 5 |
| C_or_alternative_probes | 5 |
| D_project_vs_formal_work_probes | 14 |
| E_partial_labelled_probes | 13 |
| F_remaining_probes | 26 |

## Compound GT risk audit (§7 — NOT auto-corrected, human adjudication required)

| scenario | risk | note |
|---|---|---|
| F01 | **HIGH** | Requirement is a genuine AND (SQL 且 A/B 实验). SQL subclaim = Strong (real evidence), A/B-testing subclaim = Missing (zero evidence, not merel… |
| F02 | **MEDIUM** | The 'Agent 设计能力' subclaim was not independently evidenced in the generator (assumed from general LLM delivery), only the 'Agent 专项评测能力' subc… |
| F03 | **MEDIUM** | Neither subclaim ('企业级产品经验' nor '商业化闭环经验') is cleanly Strong in the underlying evidence (both are themselves Partial-grade in the real profi… |
| F04 | **HIGH** | Same structure as F01: LLM-delivery subclaim = Strong, 模型精度调优 subclaim = Missing (zero evidence, adjacency explicitly ruled insufficient els… |
| F05 | **LOW** | Both subclaims ('数据开发经验' and '数据治理全流程经验') have at least partial real evidence (ETL/data-architecture work is real; only the governance bread… |

## High-risk rows requiring priority human attention

- `C02` — 有 RAG 系统的生产环境部署与调优经验 — DATA DEFECT: gt_rationale is EMPTY in the raw synthetic_gt_draft.json (generator key/label dict-mismatch — the evidence key used does not exist under the expected Strong/Partial/Missing bucket, so CAND[...].get(key, "") silently returned an empty string). The expected_label 'Partial' currently has NO stated evidentiary justification. Human must author a real rationale (or correct the label) before this row can be trusted.
- `D08` — 有开放平台 / 插件生态 / MCP 建设经验 — DATA DEFECT: gt_rationale is EMPTY in the raw synthetic_gt_draft.json (generator key/label dict-mismatch — the evidence key used does not exist under the expected Strong/Partial/Missing bucket, so CAND[...].get(key, "") silently returned an empty string). The expected_label 'Missing' currently has NO stated evidentiary justification. Human must author a real rationale (or correct the label) before this row can be trusted.
- `F01` — 熟练使用 SQL 且 具备 A/B 实验设计与执行能力 — Requirement is a genuine AND (SQL 且 A/B 实验). SQL subclaim = Strong (real evidence), A/B-testing subclaim = Missing (zero evidence, not merely weak). The mechanical 'narrowest unmet subclaim -> Partial' draft may understate this: under a strict AND reading, a wholly-absent subclaim arguably means the compound requirement is NOT met at all -> Missing is at least as defensible as the drafted Partial. Human adjudication required. ALSO: DATA DEFECT: gt_rationale is EMPTY in the raw synthetic_gt_draft.json (generator key/label dict-mismatch — the evidence key used does not exist under the expected Strong/Partial/Missing bucket, so CAND[...].get(key, "") silently returned an empty string). The expected_label 'Partial' currently has NO stated evidentiary justification. Human must author a real rationale (or correct the label) before this row can be trusted.
- `F04` — 具备 LLM 应用交付能力 且 模型精度调优能力 — Same structure as F01: LLM-delivery subclaim = Strong, 模型精度调优 subclaim = Missing (zero evidence, adjacency explicitly ruled insufficient elsewhere in this same dataset for the identical capability, e.g. A03/A08/F01-style logic). Mechanical narrowest-subclaim draft = Partial; a strict-AND reading could argue Missing. Human adjudication required. ALSO: DATA DEFECT: gt_rationale is EMPTY in the raw synthetic_gt_draft.json (generator key/label dict-mismatch — the evidence key used does not exist under the expected Strong/Partial/Missing bucket, so CAND[...].get(key, "") silently returned an empty string). The expected_label 'Partial' currently has NO stated evidentiary justification. Human must author a real rationale (or correct the label) before this row can be trusted.
- `D03` — 独立承担过大型 AI Infra 系统的设计、开发与调测 — flagged scenario_requires_manual_review
- `D06` — 有大规模标注体系与训练数据闭环的专项经验 — flagged scenario_requires_manual_review
