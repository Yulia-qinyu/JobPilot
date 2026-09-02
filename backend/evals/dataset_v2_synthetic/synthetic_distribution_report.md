# Dataset V2 Synthetic Challenge Set — Distribution Report

- **Jobs:** 50  ·  **Requirements:** 201
- **is_synthetic = true** on every job; **dataset_role = synthetic_behavioral_stress_test**
- Separate from V2-Real. Synthetic metrics MUST NOT be merged with real-world metrics.

## Scenario categories

| category | target | actual |
|---|---|---|
| technology_adjacency | 10 | 10 |
| partial_missing_boundary | 8 | 8 |
| project_vs_formal_work | 8 | 8 |
| strong_partial_boundary | 8 | 8 |
| role_core_mismatch | 6 | 6 |
| compound | 5 | 5 |
| or_alternative | 5 | 5 |

## Career stage

| stage | count | target |
|---|---|---|
| campus_new_grad | 15 | 15 |
| early_career | 20 | 20 |
| experienced | 15 | 15 |

## Role family

| family | count |
|---|---|
| ai_product | 23 |
| platform_enterprise_product | 8 |
| data_product | 6 |
| strategy_growth_fintech_product | 6 |
| mismatched_control | 5 |
| general_product | 2 |

## Requirement taxonomy (V2, frozen)

| type | count |
|---|---|
| matchable | 98 |
| eligibility | 51 |
| knowledge | 28 |
| subjective | 24 |

## Expected Strong / Partial / Missing (matchable only)

| label | count | share |
|---|---|---|
| Strong | 50 | 51% |
| Missing | 25 | 26% |
| Partial | 23 | 24% |

**Partial-not-dominant check:** Partial share = 24%, dominant label = Strong → PASS

## Expected eligibility status

| status | count |
|---|---|
| Supported | 35 |
| PotentialGap | 9 |
| Unknown | 7 |

## AI-subdomain coverage

| subdomain | count |
|---|---|
| llm_applications | 12 |
| ai_commercialisation | 9 |
| enterprise_ai | 9 |
| ai_infrastructure | 7 |
| agent | 6 |
| rag_knowledge_systems | 6 |
| recommendation_search | 6 |
| ai_platform | 5 |
| ai_tools | 3 |
| multimodal | 3 |
| speech_asr | 3 |
| ai_consumer_products | 2 |
| ai_productivity | 1 |

Missing subdomains: none — all 13 covered

## Scenario-requires-manual-review jobs

D03, D06
