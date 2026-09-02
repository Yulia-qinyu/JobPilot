# Dataset V1 — Targeted Taxonomy Correction Candidates (T1)

**Candidates only. Not applied. For human confirmation.** Scanned the 100 currently-`matchable` Dataset V1 requirements for high-confidence taxonomy errors. No full 158-row re-review; no GT / importance / match-label change; no model; no commit. Raw frozen GT untouched.

- **A. matchable → eligibility:** 10
- **B. matchable → subjective:** 10
- **C. matchable → knowledge:** 0 (none high-confidence)
- distinct jobs affected: 18
- jobs that would reach **0 matchable** if all their flagged rows are applied: 北京-AI产品经理(J100665), AI产品经理（J96736）

Every reclassification removes the row from the Match Score numerator **and** denominator (`matchable`-only scoring). Importance weights and the Match Score formula are unchanged.

## A. matchable → eligibility

| req_id | job | requirement_text | conf | JD phrase | job #matchable → after |
|---|---|---|---|---|---|
| `reqv2_ffe72039c28ab86a` | 微信-语音识别算法工程师 | 硕士及以上学历 | very_high | 1.计算机、人工智能、语音信号处理等相关专业，硕士及以上学历优先； | 3 → 2 |
| `reqv2_c947d1b13c08af32` | AI 产品经理实习生（J103757） | 计算机或人工智能相关专业 | high | 本科及以上学历在读，专业不限，计算机、人工智能等相关专业优先 | 2 → 1 |
| `reqv2_0431fe88ab60c3c3` | AI产品经理（J84006） | 计算机或人工智能相关专业 | high | 本科及以上学历，计算机、人工智能等相关专业优先 | 2 → 1 |
| `reqv2_43b703bc49720527` | AI产品经理（J96736） | 计算机、人工智能或数学相关专业 | high | 本科及以上学历，计算机、人工智能、数学或相关专业优先 | 1 → 0 |
| `reqv2_48610f0c3e734912` | 北京-AI产品经理(J100665) | 计算机、人工智能或信息管理相关专业 | high | 本科及以上学历，计算机、人工智能、信息管理等相关专业优先 | 1 → 0 |
| `reqv2_3961432f6ab7ec4d` | 北京-用户产品经理(J100806) | 计算机或信息管理相关专业 | high | 本科及以上学历，计算机、信息管理等相关专业优先 | 2 → 1 |
| `reqv2_6907a4e2deac1add` | 腾讯会议-评测产品经理 | 计算机 / AI / 语言学 / 数据分析 / 人机交互相关专业 | high | 1.本科及以上学历，计算机、人工智能、语言学、数据分析、人机交互或相关专业优先； | 3 → 2 |
| `reqv2_ddd61beb368e5153` | 微信-语音识别算法工程师 | 计算机 / 人工智能 / 语音信号处理相关专业 | high | 1.计算机、人工智能、语音信号处理等相关专业，硕士及以上学历优先； | 3 → 2 |
| `reqv2_9aba33d812261db8` | 北京-策略产品经理(J100784) | 熟练使用 SQL 等数据工具 | high | 具备较强的数据分析能力，熟练使用SQL等数据工具 | 3 → 2 |
| `reqv2_8c4d70d605961309` | 大模型策略产品经理（J97330） | 戏剧影视文学、创意写作或文学相关专业 | high | -本科及以上学历，戏剧影视文学、创意写作、文学等相关专业优先 | 4 → 3 |

> Context: `annotation-rubric-v2` deliberately kept non-blocking degree/major *preferences* ('…优先') as matchable/Preferred and logged it as a **known non-material taxonomy limitation**. These candidates would resolve that acknowledged limitation by routing education background to the eligibility layer.

## B. matchable → subjective

| req_id | job | requirement_text | conf | JD phrase | job #matchable → after |
|---|---|---|---|---|---|
| `reqv2_e913e8618fce3ef0` | 腾讯会议-AI产品经理-ASR方向 | 用户感知力与问题发现解决能力 | high | 3.具备敏锐的用户感知力，对产品体验有极致追求，能够主动发现并解决问题。 | 3 → 2 |
| `reqv2_d51e7d995d268f8f` | 证券-AI产品经理-金融AI应用体验方向 | 产品判断力与用户共情能力 | high | 具备优秀的产品判断力与用户共情能力， | 6 → 5 |
| `reqv2_a7e657643b65384a` | AI大模型架构师（训练/推理） | 快速掌握新技术的能力 | high | 4. 能快速接受和掌握新技术，有较强的独立、主动的学习能力。 | 8 → 7 |
| `reqv2_7ed2b166528d9d17` | 大模型产品经理（J72652） | 沟通推动、协作与表达能力 | high | -具备较强的沟通推动、合作和表达能力，积极乐观，抗压性强 | 4 → 3 |
| `reqv2_bee05a7871209904` | 腾讯云-经营系统产品经理 | 沟通协调与跨团队沟通能力 | high | 2.有良好的沟通协调能力，能胜任跨团队沟通； | 3 → 2 |
| `reqv2_d154fbace582cc6a` | 大模型应用平台产品经理（J85776） | 团队协作与沟通能力 | medium_high | -具备较强团队协作和沟通能力，思维活跃，认真细致、学习能力、适应能力强 | 3 → 2 |
| `reqv2_1dbe0ee8f6b62193` | AI产品经理（J98328） | 逻辑思维与问题解决能力 | medium_high | 具备快速学习、逻辑思维、问题解决能力 | 3 → 2 |
| `reqv2_595484b60afecce0` | 企业微信-基础产品经理 | 逻辑抽象与系统思考能力 | medium_high | 具备很好的逻辑抽象能力，和框架系统思考的能力； | 3 → 2 |
| `reqv2_55b9c7ddc30bd02b` | 腾讯视频-增长产品经理 | 数据敏感度与逻辑能力 | medium_high | 数据敏感度高，逻辑清晰， | 5 → 4 |
| `reqv2_593ead863ea05b72` | 企业微信-基础产品经理 | 观察分析并识别关键问题 | medium | 善于观察和分析，善于发现关键问题，分清主次矛盾， | 3 → 2 |

> Context: the frozen rubric classifies verifiable soft-skill *abilities* as matchable and only *attitude/passion/willingness* as subjective (pilot v1 §1 kept Huawei's composite soft-skill row as one matchable requirement; edit F1 kept 洞察/规律总结 as matchable, '可验证'). These B candidates are bare trait phrases with **no verifiable work anchor** — a rubric-philosophy reclassification for human decision, not clear pre-existing oversights.

## C. matchable → knowledge

No high-confidence cases. The frozen rubric already routed principle/mechanism-understanding requirements into the 16 `knowledge` rows (e.g. changes[] note `j72652_two_knowledge_rows`).

## Job-level impact

| job | current #matchable | flagged | after all applied |
|---|---|---|---|
| AI 产品经理实习生（J103757） | 2 | 1 | 1 |
| 北京-策略产品经理(J100784) | 3 | 1 | 2 |
| 北京-用户产品经理(J100806) | 2 | 1 | 1 |
| 北京-AI产品经理(J100665) | 1 | 1 | 0  ⚠️ 0 matchable |
| AI产品经理（J96736） | 1 | 1 | 0  ⚠️ 0 matchable |
| AI产品经理（J84006） | 2 | 1 | 1 |
| 大模型应用平台产品经理（J85776） | 3 | 1 | 2 |
| AI产品经理（J98328） | 3 | 1 | 2 |
| 大模型策略产品经理（J97330） | 4 | 1 | 3 |
| 大模型产品经理（J72652） | 4 | 1 | 3 |
| AI大模型架构师（训练/推理） | 8 | 1 | 7 |
| 企业微信-基础产品经理 | 3 | 2 | 1 (multi) |
| 腾讯会议-AI产品经理-ASR方向 | 3 | 1 | 2 |
| 腾讯会议-评测产品经理 | 3 | 1 | 2 |
| 证券-AI产品经理-金融AI应用体验方向 | 6 | 1 | 5 |
| 微信-语音识别算法工程师 | 3 | 2 | 1 (multi) |
| 腾讯云-经营系统产品经理 | 3 | 1 | 2 |
| 腾讯视频-增长产品经理 | 5 | 1 | 4 |

**⚠️ Zero-matchable warning:** two campus AI-PM jobs (`AI产品经理（J96736）`, `北京-AI产品经理(J100665)`) currently have exactly **one** matchable requirement — the '相关专业优先' row. Reclassifying it would leave the job with no capability score (denominator = 0). Human review should decide whether the row stays matchable or the job is genuinely capability-unscoreable.

## Excluded on purpose (looked relevant, not high-confidence errors)

- `reqv2_5cfb41f2e516a713` — 一年以上产品工作经验 — Explicit years-of-experience phrasing, BUT a human already reviewed it (changes[] note K1: "'优先'非资格门槛，故非 eligibility；...Partial") and deliberately kept it matchable because the JD frames it as non-blocking '优先'. Not a high-confidence error.
- `reqv2_63b051ca5b06efc5` — 洞察与规律总结能力 — Trait-like, BUT this was full_review_edit F1: the human explicitly ruled 洞察/规律总结 '可验证' (verifiable) and split only '文字品味' out as subjective. Deliberately matchable.
- `reqv2_c88202cea56f40e4` — 逻辑/概率思维、分析归纳、沟通与问题解决能力 — Composite soft-skill row, BUT pilot v1 guide §1 explicitly kept Huawei's '逻辑/概率思维、分析、归纳、沟通和解决问题' as ONE 综合软能力 matchable requirement by design.
- `reqv2_c3091ed2eca6d9f3` — 具备一定技术背景 — Borderline knowledge (source: '对大模型底层技术有一定理解'), BUT the understanding aspect was already split into separate knowledge rows (changes[] note j72652_two_knowledge_rows); the retained row is 'technical background', a verifiable capability.
- `reqv2_49c9c07f1ba12d7b` — 对大模型数据质量与评估有判断力 — B/C-ambiguous (source mentions '对大模型有基本了解' + '有自己的品味和喜好'); not high-confidence for a single target type. Left for the broader review that is out of T1 scope.
