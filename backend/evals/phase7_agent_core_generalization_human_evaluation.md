# Phase 7 Agent Core Generalization — Human Evaluation

> Human labels are intentionally blank. This artifact uses the offline deterministic path; partial coverage or high-impact semantic relations consume at most one semantic-planner call in a configured runtime.

## A. Generalized Intent

| # | Raw Query | Function | Industry | Domain | Location | Recruitment | Explicit Concepts | Method / Coverage | Required Clarification | Optional Refinement | Intent Correct | Question Useful | Options Useful |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 北京 AI Agent 产品经理 | product_management | — | ai, ai_agent | 北京 | — | 北京 · Agent 产品 · 产品经理 · AI Agent · AI · Agent | deterministic / complete | — | business_scenario |  |  |  |
| 2 | 北京 银行 应届 投资 | investment | banking | — | 北京 | graduate | 北京 · 投资 · 银行 · 应届 | deterministic / complete | — | 你更关注哪类投资方向？ |  |  |  |
| 3 | 上海 数据分析 电商 | data_analytics | ecommerce | — | 上海 | — | 上海 · 数据分析 · 电商 | deterministic / complete | — | — |  |  |  |
| 4 | 北京 战略咨询 应届 | strategy_consulting | — | — | 北京 | graduate | 北京 · 战略咨询 · 应届 | deterministic / complete | — | — |  |  |  |
| 5 | 深圳 大模型 算法 | algorithm_research | — | llm | 深圳 | — | 深圳 · 算法 · 大模型 | deterministic / complete | — | — |  |  |  |
| 6 | 北京 消费品 市场营销 | marketing | consumer_goods | — | 北京 | — | 北京 · 市场营销 · 消费品 | deterministic / complete | — | — |  |  |  |
| 7 | 上海 风控 银行 | risk_management | banking | risk_control | 上海 | — | 上海 · 风控 · 银行 | deterministic / complete | — | — |  |  |  |
| 8 | 北京 产品运营 电商 | operations | ecommerce | — | 北京 | — | 北京 · 产品运营 · 电商 | deterministic / complete | — | — |  |  |  |
| 9 | 帮我找金融工作 | — | financial_services | — | — | — | 金融工作 | deterministic / ambiguous | 你更偏向哪类金融岗位？ | — |  |  |  |
| 10 | 帮我找 AI 工作 | — | — | ai | — | — | AI | deterministic / ambiguous | 你更偏向哪类 AI 岗位？ | — |  |  |  |
| 11 | 腾讯北京产品 | — | — | — | 北京 | — | 北京 · 产品 · 腾讯 | deterministic / ambiguous | role | — |  |  |  |
| 12 | 量化一级市场投资 北京 | investment | — | primary_market | 北京 | — | 北京 · 投资 · 一级市场 · 量化 | deterministic / partial | — | 你更关注哪类投资方向？ |  |  |  |
| 13 | 我想做偏一级市场、科技方向的投资岗位 | investment | — | primary_market, technology | — | — | 投资 · 一级市场 · 科技方向 | deterministic / complete | — | 你更关注哪类投资方向？ |  |  |  |
| 14 | 上海 FinTech 产品经理 | product_management | — | — | 上海 | — | 上海 · FinTech 产品 · 产品经理 · FinTech | deterministic / complete | — | — |  |  |  |
| 15 | 北京 社招 AI 产品经理 字节跳动 | product_management | — | ai | 北京 | experienced | 北京 · AI 产品 · 产品经理 · AI · 字节跳动 · 社招 | deterministic / complete | — | ai_direction / business_scenario |  |  |  |
| 16 | 北京 校招 数据分析 | data_analytics | — | — | 北京 | graduate | 北京 · 数据分析 · 校招 | deterministic / complete | — | — |  |  |  |
| 17 | 杭州 Developer Tools 产品经理 | product_management | — | — | 杭州 | — | 杭州 · 产品经理 · Developer Tools | deterministic / ambiguous | role | — |  |  |  |
| 18 | 深圳 AI 工程师 大模型 | engineering | — | ai, llm | 深圳 | — | 深圳 · 工程师 · 大模型 · AI | deterministic / complete | — | — |  |  |  |
| 19 | 北京 品牌营销 快消 | marketing | consumer_goods | — | 北京 | — | 北京 · 品牌营销 · 快消 | deterministic / complete | — | — |  |  |  |
| 20 | 远程 Enterprise Agent 解决方案 | solution | — | ai_agent | Remote | — | 远程 · 解决方案 · Enterprise Agent · Agent | deterministic / complete | — | — |  |  |  |

## B. Source Planning

| Case | Query | Requested Companies | Selected Sources / Channels | Unsupported | Coverage | Message | Source Plan Correct |
|---|---|---|---|---|---|---|---|
| No company | 北京 AI 产品经理 | — | 字节跳动/campus, 字节跳动/experienced | — | supported | 将搜索当前支持的国内招聘源：字节跳动。 |  |
| One supported | 北京 AI 产品经理 字节跳动 | 字节跳动 | 字节跳动/campus, 字节跳动/experienced | — | full | 将搜索：字节跳动。 |  |
| One unsupported | 北京 AI 产品经理 小米 | 小米 | — | 小米 | unsupported | 当前暂不支持小米官方招聘源的批量搜索。 |  |
| Multiple mixed | 北京 AI 产品经理 字节 小米 腾讯 | 字节跳动, 腾讯, 小米 | 字节跳动/campus, 字节跳动/experienced | 腾讯, 小米 | partial | 将搜索字节跳动；腾讯、小米官方招聘源暂未支持。 |  |
| Campus | 北京 应届 AI 产品经理 | — | 字节跳动/campus | — | supported | 将搜索当前支持的国内招聘源：字节跳动。 |  |
| Experienced | 北京 社招 AI 产品经理 | — | 字节跳动/experienced | — | supported | 将搜索当前支持的国内招聘源：字节跳动。 |  |

## C. Claude Budget

- Deterministically covered query: **0 calls**
- Semantic coverage partial/high-impact relation: **at most 1 call**
- Clarification/refinement click: **0 calls**
- Source planning, acquisition, ranking, personalization: **0 calls**
- Session hard max: **1 intent call**

Human notes:

- 0-call cases correct:
- 1-call cases justified:
- Hard max respected:
