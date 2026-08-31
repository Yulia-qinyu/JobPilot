# JobPilot Evaluation Phase — Ground Truth Annotation Pilot V1 Prepared

## Pilot Status

- Frozen dataset jobs: **30**
- Pilot jobs: **10**
- Chinese-dominant: **9**
- English control: **1**
- Requirement rows: **68**
- Review status: **all pending**
- Human fields populated: **0**

The pilot contains AI-generated annotation suggestions only. It does not constitute human ground truth.

## Selected Jobs and Rationale

- `baidu:0ad545f8-07df-42f1-9a10-28e79d5dc407` — 百度 · AI 产品经理实习生（J103757）（北京，Chinese）：中文 AI 产品实习岗；校招身份、在读学历和专业偏好可验证 Critical/Preferred 拆分。
- `tencent:2088450750270324736` — 腾讯 · AI产品经理-AI平台（Agent）方向（深圳，Chinese）：中文 Agent 平台产品岗；同时包含学历、最低年限、核心 AI 能力和多个优先项。
- `tencent:2052527703940313088` — 腾讯 · 证券-AI产品经理-金融AI应用体验方向（深圳，Chinese）：中文金融 AI 产品岗；可检验 3 年硬门槛、直接项目经历与相邻证券领域证据。
- `veeva:8ae64dee-34a9-4e69-84ef-b91bcde3f35f` — Veeva · Senior Product Manager - AI Agent（上海，English）：唯一英文对照；Senior AI Agent 产品岗，可检验跨语言要求和年限约束。
- `baidu:105aafd8-a50f-4ef6-aad3-d0a729f5e4a8` — 百度 · 产品经理实习生（J104146）（北京，Chinese）：中文通用产品实习岗；要求短但包含学历、实习时长和偏好项。
- `tencent:2047239002926510080` — 腾讯 · 金融科技-AI数据产品经理-数据开发方向（深圳，Chinese）：中文 AI 数据产品岗；覆盖数仓、SQL、数据产品、LLM/RAG/Agent 与金融加分项。
- `tencent:1994013057063473152` — 腾讯 · 企业微信-基础产品经理（广州，Chinese）：中文基础产品岗；包含广义产品能力与单独结构化的 3 年经验要求。
- `baidu:f9302c30-aace-449e-8a6d-97c53f4dbf53` — 百度 · 大模型策略产品经理（J97330）（北京，Chinese）：中文大模型策略岗；检验学历、创意内容领域要求和多个 Preferred 子句。
- `tencent:2083093175941115904` — 腾讯 · 腾讯视频-增长产品经理（北京，Chinese）：中文增长产品岗；检验增长经历、3–5 年门槛、数据分析与 AB 实验的拆分。
- `huawei:28183` — 华为 · AI大模型架构师（训练/推理）（北京，Chinese）：中文 mismatched control；AI 架构师岗位含学历、5 年、语言与深技术硬要求。

### Stratification

- AI Product: **4**
- General Product: **2**
- Data Product: **1**
- Strategy / Growth / FinTech: **2**
- Mismatched Control: **1**
- Jobs with explicit hard requirements: **9** (overlaps with role strata)
- Companies: **4** — 百度、腾讯、Veeva、华为
- Cities: **北京、深圳、上海、广州**

The extra General/Data and Strategy rows fill the 10-job sample while increasing requirement and domain diversity. No near-identical roles were selected.

## Descriptive Statistics

- Requirements: **68**
- Average requirements per job: **6.8**
- Minimum / maximum requirements per job: **3 / 16**
- Importance suggestions: **Critical 14 / Important 40 / Preferred 14**
- Match suggestions: **Strong 36 / Partial 22 / Missing 10**
- Hard requirements (Critical): **14**
- Evidence-backed Strong/Partial suggestions: **58**

These are descriptive counts only. No accuracy, F1, production Match Score, or model comparison was calculated.

## Candidate Evidence Boundary

- Evidence catalog version: `candidate-evidence-v2`
- Bounded pilot catalog: **30 items**
- Allowed: `resume_extracted`, `manual_confirmed`, verified candidate identity
- Excluded: `manual_unconfirmed`, unknown, AI-inferred or speculative facts
- Candidate Profile mutations: **0**

The JSON records the exact frozen candidate evidence snapshot hashes and references stable catalog IDs rather than copying full resume sections into every row.

## Annotation Ambiguities

1. **Project experience vs professional duration** — Direct AI Product projects support relevance, but do not establish “1/2/3/5+ years.” These rows are suggested Partial, not Strong.
2. **Future internship availability** — A historical five-month internship does not prove the candidate can commit five months to a new internship. The availability requirement is suggested Missing pending human confirmation.
3. **Subjective attitude language** — “热爱互联网” and “极高热情” cannot be fully verified from structured facts. Relevant behavior produces at most Partial.
4. **Related vs identical domain expertise** — FinTech education and banking/investment experience are adjacent to securities, but do not prove “deep securities understanding”; suggested Partial.
5. **Compound technical stacks** — LLM/RAG/Agent evidence does not automatically prove Prompt engineering, MCP, inference optimization or RL training. Compound rows are Partial when only part is supported.
6. **Degree plus preferred major** — Degree is separated as Critical while the “相关专业优先” clause is Preferred.
7. **Broad soft skills** — Closely coupled communication/problem-solving phrases are kept together to avoid over-fragmentation, but grounding remains less objective than hard skills.
8. **Chinese-language evidence** — The profile explicitly records English proficiency, while Chinese ability is evident from the Chinese candidate materials but lacks a separate structured language fact. Huawei R01 is flagged for human review despite a Strong suggestion.
9. **From-zero-to-one with measurable outcomes** — Project ownership is verified, but no specific business outcome is recorded for GoFin; suggested Partial rather than Strong.
10. **AI model work vs LLM infrastructure** — General model training/evaluation is adjacent to LLM training and inference infrastructure, not equivalent; labels remain Partial or Missing depending on the requirement.

## Estimated Human Review Workload

- Requirement rows to review: **68**
- Estimated review time per job: **8–12 minutes**
- Estimated pilot total: **80–120 minutes**
- Projected 30-job total at the same density: **4–6 hours**

These are planning estimates, not measured review times. Actual time should be recorded during the pilot before scheduling the remaining 20 jobs.

## Integrity Checks

- Exactly 10 selected jobs: **pass**
- 9 Chinese + 1 English: **pass**
- Every source text is a substring of its frozen JD field: **pass**
- Every Strong/Partial references eligible evidence: **pass**
- Missing rows have empty evidence IDs: **pass**
- `manual_unconfirmed` references: **0**
- Human fields populated: **0**
- All review statuses `pending`: **pass**
- Dataset JSON SHA-256 unchanged: `3654d64c0f94e507e91343706bd79ca6b20f8081ee22880bf537744d88b2b558`
- Dataset CSV SHA-256 unchanged: `5d05580595f2f7b92707857a05ac48a93ad32c845bb0b4d4cd06a0734e788d6b`
- Production Phase 3 runs: **0**
- Production Match Score calculations: **0**
- JobPilot database/application state changes: **0**

## Next Step (Human Only)

Reviewers should ACCEPT, EDIT or REJECT this pilot before any remaining-job annotation, baseline run, model benchmark, prompt change or final ground-truth creation begins.
