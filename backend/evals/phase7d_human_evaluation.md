# Phase 7D Human Product Evaluation

> Deterministic A/B artifact. Human labels are intentionally blank. Claude personalization calls: 0.

## A. OFF vs ON A/B

| Title | Public Relevance | OFF Position | ON Position / Band | Candidate Reasons | Candidate Risks | Evidence Refs | Helpful | Grounded | Preferred |
|---|---|---|---|---|---|---|---|---|---|
| AI Agent Product Manager | High | 1 | 7 / Relevant | 存在可支持的Agent相关经历 · 存在可支持的AI 产品相关经历 · 对应我已设置的目标岗位方向 | 可能存在 5+ 年经验门槛差距 | resume_extracted:28, manual_confirmed:41, target_role:1 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Agent Platform Product Manager | High | 2 | 1 / Strong | 存在可支持的Agent相关经历 · 存在可支持的AI 产品相关经历 · 存在可支持的平台相关经历 · 对应我已设置的目标岗位方向 | — | resume_extracted:28, manual_confirmed:41, resume_extracted:63, target_role:1 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Senior AI Product Manager — LLM | High | 3 | 2 / Strong | 存在可支持的AI 产品相关经历 · 存在可支持的大模型相关经历 · 对应我已设置的目标岗位方向 | — | resume_extracted:28, manual_confirmed:41, target_role:1 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| AI Product Manager — Evaluation | High | 4 | 3 / Strong | 存在可支持的AI 产品相关经历 · 存在可支持的实验 / 评测相关经历 · 对应我已设置的目标岗位方向 | — | resume_extracted:28, manual_confirmed:41, target_role:1 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Enterprise Agent Product Manager | High | 5 | 4 / Strong | 存在可支持的Agent相关经历 · 存在可支持的AI 产品相关经历 · 对应我已设置的目标岗位方向 | — | resume_extracted:28, manual_confirmed:41, target_role:1 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| AI Workflow Product Owner | High | 6 | 5 / Strong | 存在可支持的AI 产品相关经历 · 对应我已设置的目标岗位方向 | — | resume_extracted:28, manual_confirmed:41, target_role:1 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| AIGC Product Manager | High | 7 | 6 / Strong | 存在可支持的AI 产品相关经历 · 对应我已设置的目标岗位方向 | — | resume_extracted:28, manual_confirmed:41, target_role:1 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| AI Data Product Manager | Medium | 8 | 16 / Relevant | 存在可支持的数据相关经历 | 可能存在 5+ 年经验门槛差距 | resume_extracted:52, resume_extracted:63 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Platform Product Manager | Medium | 9 | 8 / Relevant | 存在可支持的平台相关经历 | — | resume_extracted:63 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| FinTech AI Product Manager | Medium | 10 | 9 / Relevant | 存在可支持的FinTech相关经历 | — | resume_extracted:52 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Product Manager — Developer Tools | Medium | 11 | 11 / Relevant | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Product Manager — Analytics | Medium | 12 | 10 / Relevant | 存在可支持的数据相关经历 | — | resume_extracted:52, resume_extracted:63 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Growth Product Manager | Medium | 13 | 12 / Relevant | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Product Strategy Manager | Medium | 14 | 13 / Relevant | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Product Operations Manager | Low | 17 | 24 / Neutral | — | 可能存在 5+ 年经验门槛差距 | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| AI Solutions Consultant | Low | 18 | 19 / Neutral | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Applied AI Engineer | Low | 19 | 20 / Neutral | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| AI Infrastructure Engineer | Low | 20 | 18 / Neutral | 存在可支持的平台相关经历 | — | resume_extracted:63 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Machine Learning Engineer | Low | 21 | 21 / Neutral | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Algorithm Researcher | Low | 22 | 22 / Neutral | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Engineering Manager — Agent Platform | Low | 23 | 17 / Neutral | 存在可支持的Agent相关经历 · 存在可支持的平台相关经历 | — | resume_extracted:28, resume_extracted:63 | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| AI UX Designer | Low | 24 | 25 / Neutral | — | 可能存在 5+ 年经验门槛差距 | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Content Operations — AIGC | Low | 25 | 23 / Neutral | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| General Product Manager | Medium | 15 | 14 / Relevant | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |
| Commercialization Product Manager | Medium | 16 | 15 / Relevant | — | — | — | Yes / Neutral / Harmful | Yes / Partial / No | OFF / ON / Same |

## B. Search Intent Conflict Cases

| Current Search | Saved Preference | Result | Expected Priority | Actual | Current Intent Preserved |
|---|---|---|---|---|---|
| 上海 FinTech Product | 北京 AI Product | Shanghai FinTech Product | Current search first | Public band remains authoritative | Yes / No |
| AI Agent，不要银行 | Banking | Banking AI Product | Excluded / no boost | Low remains Neutral | Yes / No |
| Growth Product | Platform Product | Growth Product | Growth first | Exact current role remains first | Yes / No |

## C. Evidence Grounding

| Reason | Evidence Ref | Evidence Text Summary | Supported? |
|---|---|---|---|
| 存在可支持的Agent相关经历 | resume_extracted:28 | Built an AI Agent and LLM workflow | Yes / No |
| 存在可支持的AI 产品相关经历 | resume_extracted:28 | Built an AI Agent and LLM workflow | Yes / No |
| 存在可支持的AI 产品相关经历 | manual_confirmed:41 | Designed an AI product evaluation flow | Yes / No |
| 存在可支持的Agent相关经历 | resume_extracted:28 | Built an AI Agent and LLM workflow | Yes / No |
| 存在可支持的AI 产品相关经历 | resume_extracted:28 | Built an AI Agent and LLM workflow | Yes / No |
| 存在可支持的AI 产品相关经历 | manual_confirmed:41 | Designed an AI product evaluation flow | Yes / No |
| 存在可支持的平台相关经历 | resume_extracted:63 | Designed a data product platform | Yes / No |
| 存在可支持的AI 产品相关经历 | resume_extracted:28 | Built an AI Agent and LLM workflow | Yes / No |
| 存在可支持的AI 产品相关经历 | manual_confirmed:41 | Designed an AI product evaluation flow | Yes / No |
| 存在可支持的大模型相关经历 | resume_extracted:28 | Built an AI Agent and LLM workflow | Yes / No |

## D. Candidate Constraint Cases

| Candidate Fact | Requirement | Result | Decision Correct |
|---|---|---|---|
| 6 verified years | 5+ years required | Supported | Yes / No |
| 1 verified year | 5+ years required | PotentialGap | Yes / No |
| No verified years | 5+ years required | Unknown | Yes / No |
| Verified Master degree | Bachelor required | Supported | Yes / No |
| No verified education | Bachelor required | Unknown | Yes / No |

## E. OFF Privacy Boundary

```text
Candidate context provider calls while OFF = 0
Claude personalization calls = 0
Source refetch count on toggle = 0
Automatic Phase 3 calls = 0
```

## Human Metrics

- Personalization Preference Rate:
- Harmful Personalization Rate:
- Evidence Grounding Accuracy:
- Current Intent Override Violations:
- Candidate Constraint Precision:
- Candidate Constraint False Gap Count:
