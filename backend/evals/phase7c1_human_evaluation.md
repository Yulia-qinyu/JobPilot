# Phase 7C.1 Human Product Evaluation

> Deterministic regression artifact. Claude calls: 0. Human labels are intentionally blank.

## A. Intent Preservation

| Raw Query | Parsed Role Family | Explicit Concepts Preserved | Required Clarification? | Optional Refinements | Intent Fully Preserved | Clarification Decision Correct |
|---|---|---|---|---|---|---|
| 我想看看大模型平台方向 | — | 大模型应用, AI 平台 | No | — | Yes / Partial / No | Yes / No |
| 多模态 AI 产品 | ai_product | 多模态 | No | business_scenario | Yes / Partial / No | Yes / No |
| AIGC 内容产品经理 | ai_product | AIGC, 内容 / 创作者 | No | — | Yes / Partial / No | Yes / No |
| ToB AI 产品经理 | ai_product | ToB / 企业服务 | No | ai_direction | Yes / Partial / No | Yes / No |
| 增长产品经理 电商 | growth_product | 电商 | No | — | Yes / Partial / No | Yes / No |
| AI 产品，出海和电商都可以 | ai_product | 电商, 出海 / 国际化 | No | ai_direction | Yes / Partial / No | Yes / No |

## B. Clarification

| Raw Query | Decision | Question / Tag Group | Clarification Decision Correct |
|---|---|---|---|
| 帮我找 AI 工作 | Required | job_function | Yes / No |
| 北京 AI Agent 产品经理 大厂 | Optional | business_scenario | Yes / No |
| 北京应届 AI 产品，不要运营 | Optional | ai_direction, business_scenario | Yes / No |
| 腾讯北京产品 | Required | role | Yes / No |

## C. Ranking Regression — AI Agent 产品经理

| Title | Classified Role Family | Relevance Band | Reason | Ranking Correct |
|---|---|---|---|---|
| AI Product Manager | ai_product | High | AI Product · 产品 · Agent · AI Agent · ai · AI Agent · 年限要求未明确 | Yes / No |
| Agent 产品经理 | ai_product | High | AI Product · 产品 · Agent · AI Agent · AI Agent · 年限要求未明确 | Yes / No |
| Senior Product Manager, Agent Platform | general_product | Medium | 产品 · Agent · AI Agent · AI Agent · 年限要求未明确 | Yes / No |
| Engineering Manager, Agent Cloud Platform | engineering | Low | Agent · AI Agent · AI Agent · 年限要求未明确 · 岗位类型与本次目标方向不一致 · 岗位职能与本次目标方向不一致 | Yes / No |
| AI Infrastructure Engineer, Agent Runtime | engineering | Low | Agent · AI Agent · ai · AI Agent · 年限要求未明确 · 岗位类型与本次目标方向不一致 · 岗位职能与本次目标方向不一致 | Yes / No |
| Applied AI Engineer | engineering | Low | Agent · AI Agent · ai · AI Agent · 年限要求未明确 · 岗位类型与本次目标方向不一致 · 岗位职能与本次目标方向不一致 | Yes / No |

## D. Hard Signal Regression

| Case | Source Text | Extracted Hard Signal | Hard Signal Decision Correct |
|---|---|---|---|
| True experience | Candidates must have at least 6 years of product experience | 明确要求 6+ 年经验 | Yes / No |
| True education | Bachelor's degree required | 明确要求本科及以上学历 | Yes / No |
| Responsibility | As a Production AI Ops Manager, you will design and develop production systems. | None | Yes / No |
| You will | You will design and develop reliable AI services | None | Yes / No |
