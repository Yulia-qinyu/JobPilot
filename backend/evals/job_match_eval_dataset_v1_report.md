# JobPilot Evaluation Dataset V1 — Chinese-Language Localization Complete

## Collection Summary

- Final jobs: **30**
- Mainland China jobs: **30 (100%)**
- Overseas / Hong Kong / Macau / Taiwan jobs: **0**
- Official or company-controlled source URLs: **30 / 30**
- Companies represented: **6**
- Localization replacements: **9 English-heavy rows removed, 9 Chinese rows added**
- Human annotation fields: **blank**
- Phase 3 / Match Score runs: **0**
- Production or local application state changes: **0**

## Language Distribution

- Chinese-language jobs: **27 (90.0%)**
- English-language jobs: **3 (10.0%)**

A row is classified as Chinese when the substantive responsibilities and requirements contain at least as many CJK characters as Latin alphabetic characters. All 27 classified Chinese rows were also manually spot-checked for Chinese-dominant substantive content.

### English controls retained

- `veeva:8ae64dee-34a9-4e69-84ef-b91bcde3f35f` — Veeva · Senior Product Manager - AI Agent: retained as a cross-language AI Product control.
- `greenhouse:4186650005` — SES AI · Data Product Manager: retained as a cross-language Data Product control.
- `xsolla:252b30e5-ce58-4a32-88b3-07ee83d06e67` — Xsolla · AI-First Engineering Intern: retained as a cross-language mismatched control.

### English-heavy rows replaced

- `ashby:67d9ff10-76c3-46f3-9eeb-41c6ef176571` — Alpha Life Sciences · Technical Product Manager (CN)
- `bjak:ab741f0f-44d1-44a8-aa6a-368cb592fca2` — BJAK · Product Manager - AI Neobank App
- `bjak:0c6aaf37-70df-4260-9424-11762d260c8d` — BJAK · Product Owner, AI Email App
- `bjak:705d2156-d34f-4f2b-9266-f78de0e09c60` — BJAK · Product Owner, AI Internal Systems
- `bjak:897e70fa-6023-463a-8ec4-8b6723685120` — BJAK · Technical Product Manager, AI Systems
- `patsnap:2711679` — PatSnap · AI Product Manager (Intellectual Property / AI Agent)
- `greenhouse:7736914003` — Tomofun · Product Manager 产品经理
- `xsolla:0affadcf-dd1d-4649-9ab9-0244a585ee9c` — Xsolla · Senior Product Manager — White-Label App Store Platform
- `greenhouse:4186612005` — SES AI · Battery AI/ML Engineer

### Chinese replacement sources

- `tencent:1978467627152072704` — 腾讯 · 微信输入法-AI产品经理 · 广州
- `tencent:2088450750270324736` — 腾讯 · AI产品经理-AI平台（Agent）方向 · 深圳
- `tencent:2036621556322562048` — 腾讯 · 腾讯会议-AI产品经理-ASR方向 · 深圳
- `tencent:2052527703940313088` — 腾讯 · 证券-AI产品经理-金融AI应用体验方向 · 深圳
- `tencent:2047239002926510080` — 腾讯 · 金融科技-AI数据产品经理-数据开发方向 · 深圳
- `baidu:ff9ed74c-8ec5-41f6-8a4c-1950500bd9f2` — 百度 · 大模型产品经理（J72652） · 北京
- `baidu:aa3be39c-798a-4d92-a5af-1c84fa63b049` — 百度 · 大模型应用平台产品经理（J85776） · 北京
- `baidu:f9302c30-aace-449e-8a6d-97c53f4dbf53` — 百度 · 大模型策略产品经理（J97330） · 北京
- `huawei:28183` — 华为 · AI大模型架构师（训练/推理） · 北京

The replacements use public job-detail content from Tencent Careers, Baidu Careers, and Huawei Careers. No login, CAPTCHA bypass, private session, browser fingerprinting, or anti-bot workaround was used.

## Role Distribution

- ai_product: **15**
- general_product: **5**
- data_product: **4**
- mismatched_control: **3**
- strategy_growth_fintech: **3**

The corpus retains the intended evaluation shape: AI Product is the largest group, adjacent product roles provide comparison coverage, and three mismatched controls remain available. `role_category` is composition metadata only; it is not a Match Score or human fit label.

## Company Distribution

- 腾讯: **14**
- 百度: **12**
- Veeva: **1**
- SES AI: **1**
- Xsolla: **1**
- 华为: **1**

Six companies remain represented. Baidu and Tencent are intentionally prominent because their official Mainland China career pages exposed complete Chinese responsibilities and requirements without access-control bypasses.

## City Distribution

- 北京: **16**
- 深圳: **10**
- 上海: **2**
- 广州: **2**

All city values were validated against the dataset's Mainland China city allowlist. Beijing remains the dominant location as requested.

## Recruitment Type Distribution

- experienced: **22**
- internship: **3**
- campus: **3**
- full-time: **2**

Publicly accessible Chinese campus AI Product postings remained scarce. The corpus therefore includes internships and early-career roles where available, but still contains experienced roles; this is a known representativeness limitation.

## Dataset Quality Cleanup

- Rows reviewed after localization: **30 / 30**
- Unique job IDs: **30 / 30**
- Unique source URLs: **30 / 30**
- Rows missing meaningful responsibilities: **0**
- Rows missing meaningful candidate requirements: **0**
- Requirements containing interview-process / benefits boilerplate patterns: **0**
- Obvious semantic duplicate clusters above 4-gram Jaccard 0.72: **0**
- Highest pairwise normalized 4-gram Jaccard: **0.0955** (`baidu:423c0fa3-a0f3-4def-a882-7466d3685b79` vs `baidu:1270fb70-730e-4569-9385-b013690e607d`)

The earlier semantic-duplicate cleanup remains in effect. The localization pass did not translate, reconstruct, or invent source text: Chinese replacements preserve the official responsibilities and requirement wording, with structured education/experience fields populated only where the source explicitly stated them.

## Missing-field Policy

`graduation_year_requirement`, `education_requirement`, `experience_requirement`, `salary_text`, and `preferred_requirements_text` remain null when not explicitly stated. Missing values are not inferred. All future human-annotation fields remain empty.

## Remaining Dataset Biases

- Company concentration is high: Tencent and Baidu provide most rows because they expose stable, complete Chinese official job details.
- Campus and fresh-graduate AI Product roles are underrepresented relative to the desired production mix; accessible official listings skew experienced.
- Beijing and Shenzhen dominate geographic coverage.
- The three English controls are useful for cross-language behavior checks but do not represent the primary Chinese production distribution.
- Snapshot URLs and postings may later expire even though they were publicly verifiable during collection.

## Validation Statement

- **No ground-truth labels were generated.**
- **No Match Score was calculated.**
- **No Phase 3 evaluation was run.**
- **No production or local JobPilot application state was modified.**
- **No access controls were bypassed.**
