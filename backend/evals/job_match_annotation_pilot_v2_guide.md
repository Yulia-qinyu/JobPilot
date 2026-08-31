# JobPilot Ground Truth Annotation Pilot V2 — Review Guide

## 目的与边界

这份 Pilot 让人工评审者以 **ACCEPT / EDIT / REJECT** 为主，在 **Requirement Taxonomy V2** 下复核 AI 预标注。CSV/JSON 中的 `ai_*` 全部是 AI 建议，不是 Ground Truth；所有 `human_*` 字段保持空白，所有 `review_status` 初始为 `pending`。

Pilot V2 复用 Pilot V1 的**同 10 个岗位**与**同一份冻结候选人证据快照**，因此 V1 与 V2 可直接比较。可用证据仅来自 JSON 中的 bounded evidence catalog：`resume_extracted`、`manual_confirmed` 和已确认求职身份。不得使用 `manual_unconfirmed`、推测、对话记忆、常识假设或外部信息。

本 Pilot 未运行任何 baseline、模型 benchmark、生产 Phase 3 或 Match Score 计算，也未改动任何产品状态。

## 1. 三分类法（V2 核心）

每条 canonical requirement 必须**且只能**属于以下之一：

### eligibility — 明确资格 / 阻断门槛

例：学历、毕业届别、最低工作年限、证书、工作许可、强制语言要求，以及“可连续实习 N 个月”这类未来可用性门槛。

标注字段：
- `requirement_type = eligibility`
- `ai_eligibility_status ∈ {Supported, PotentialGap, Unknown}`
- `score_included = false`
- **没有** Strong / Partial / Missing 标签
- `eligibility_category ∈ {degree, graduation_cohort, experience_years, certification, work_authorization, language, other}`

eligibility 复用现有确定性 EligibilityService 语义，不进入语义 matcher，不计入 Match Score。

### matchable — 可由履历证据合理核验的能力 / 经验

例：AI 产品经验、Agent 交付、RAG 实现、SQL、数据分析、金融行业经验、增长经验、跨职能交付。

标注字段：
- `requirement_type = matchable`
- `ai_match_label ∈ {Strong, Partial, Missing}`
- `ai_evidence_ids`（Strong / Partial 必须 ≥ 1 个，Missing 必须为空）
- `ai_grounding_reason`（一句话解释证据如何连接要求，不得只复述证据）
- `score_included = true`

只有 matchable 进入 Phase 3 语义 matcher，只有 matchable 计入 Match Score（分子与分母）。

### knowledge — 主要表达理论理解 / 原理 / 机制 / 架构概念 / 能力边界

例：理解 RAG 原理、理解 Agent 架构、理解 Transformer 原理、理解 LLM 能力边界、理解 RLHF、理解大模型推理优化技术。

标注字段：
- `requirement_type = knowledge`
- `ai_match_label = N/A`（**没有** Strong / Partial / Missing）
- `ai_evidence_ids = []`（**必须为空**）
- `knowledge_topics`、`knowledge_text`
- `score_included = false`

knowledge 不进入 matcher、不计入 Match Score（分子与分母都不计）、不作为“暂无匹配证据”展示、不用于生成简历改写，只作为**面试准备主题**。

### subjective expectation — 非评分主观期望

例：“对 AI 有极高热情”、“极强学习意愿”、“热爱互联网”、“对产品设计有饱满热情”。

- 既不是 knowledge，也不是 eligibility，也不是 matchable。
- 不计分。仅在 `subjective_expectations` 中保留为非评分上下文。
- 不要把主观态度强行塞进 knowledge 或 Match Score。

## 2. 分类原则：Evidence Verifiability（不是关键词）

对每条要求问一句：

> “这条要求能否由允许的候选人履历证据**合理且稳定地**核验？”

- 能核验实践 / 经验 / 能力 → **matchable**
- 是明确资格 / 阻断门槛 → **eligibility**
- 主要是理论理解 / 原理 / 机制 / 能力边界 → **knowledge**
- 只是态度 / 热情 / 意愿 → **subjective**

对照示例（固定产品判定）：

| JD 表述 | 分类 |
|---|---|
| 熟练使用 SQL | matchable |
| 有 RAG 项目经验 / RAG 实践经验 | matchable |
| 理解 RAG 原理 / 深入理解 Agent 架构 / 理解大模型推理优化技术 | knowledge |
| 3 年以上 AI 产品经验 | eligibility（experience_years），不再另建同义 matchable |
| 计算机相关本科及以上学历 | eligibility（degree） |
| 有金融行业经验优先 | matchable + Preferred |
| 对 AI 有极高热情 | subjective（非评分） |
| 熟悉大模型并有 RAG 实践经验 | 实践部分 matchable；仅当明确要求原理 / 机制 / 能力边界时才拆出 knowledge |

## 3. 复合要求拆分

**仅当**源 JD 明确支持多个可独立判断的要求时才拆分，且每个结果都必须可追溯到明确 JD 文本。

- “有 Agent 产品经验，并深入理解 Agent 架构” → matchable（Agent 产品经验）+ knowledge（Agent 架构理解）。
- “对 AI 产品充满热情，有深度使用经验” → subjective（热情）+ matchable（深度使用经验）。
- “本科及以上学历，计算机、人工智能等相关专业优先” → eligibility（学历门槛）+ matchable Preferred（专业偏好）。

不得凭空制造：不得从“理解 Agent 原理”推出“有 Agent 项目经验”。

## 4. eligibility 标签

- **Supported**：已验证事实支持该门槛（如已验证学历、已确认届别）。
- **PotentialGap**：已验证事实与门槛存在明确冲突（如已验证学历低于要求；应届身份与明确多年职业年限要求冲突）。
- **Unknown**：当前证据不足以确认，但**没有**明确冲突。**缺少证据 ≠ 不满足**，不得因缺证据自动判 PotentialGap。

年限门槛使用 eligibility 语义，不使用 Phase 3 的 Partial；不得把项目 / 实习折算成职业年限。

## 5. matchable 标签

- **Strong**：已验证证据直接且充分支持要求。
- **Partial**：有相关证据，但只覆盖部分、方向相邻、深度 / 范围较弱，或缺少要求的时长 / 专项。
- **Missing**：没有可用的已验证支持证据。

**Missing ≠ 候选人做不到**：只表示当前冻结证据里没有支持事实。

## 6. knowledge 语义

**knowledge 缺失 ≠ 候选人没有该知识**：knowledge 不评分，因为简历式证据无法稳定证明理论掌握深度。knowledge 只产出 `knowledge_topics` / `knowledge_text`，供面试准备使用，不产生 Strong / Partial / Missing，不产生 Gap，不驱动简历改写。

## 7. `score_included` 语义

`score_included = true` **仅** matchable。eligibility、knowledge、subjective 均为 `false`。Match Score 的分子与分母都只由 matchable 组成。eligibility 在单独的“岗位资格”区核验；knowledge 在单独的“岗位知识要求 / 准备主题”区展示。

## 8. Canonical Requirement ID（`reqv2_*`）

每条 canonical requirement 的 `requirement_id` 由生产 Phase 8C 的确定性函数
`RequirementCatalogBuilder.stable_requirement_id(source_text, normalized_requirement, requirement_type, source_section)`
生成，格式为 `reqv2_<16hex>`。它是 `(NFKC-casefold(source_text), NFKC-casefold(normalized_requirement), requirement_type, source_section, 0)` 的 SHA-256 前缀，与展示顺序、importance、标签无关。

Ground Truth V2 之后可直接用 `requirement_id` 与生产的
`structured_jd.requirements[].requirement_id`、`requirement_matches[].requirement_id`、
`score_basis.included_requirement_ids` 对齐，无需任何文本 / 模糊 join。

human 复核若调整了 `source_text` / `normalized_requirement` / `requirement_type` / `source_section`，请在 `human_notes` 注明，ID 需按同一函数重算。

## 9. Overall Fit 1–5（人工判断，保持空白）

- 5 = Very Strong Fit
- 4 = Good Fit
- 3 = Mixed / Plausible
- 2 = Low Fit
- 1 = Clearly Unsuitable

`human_overall_fit` 保持空白，由人工填写。**不得**由 Match Score 或任何公式机械推导。`ai_overall_fit_suggestion` 沿用 Pilot V1 的岗位级建议值，仅供参考；V2 下 eligibility / knowledge 已分离，人工应重新判断。

## 10. 允许的证据边界

冻结证据快照（`candidate_evidence_snapshot`，30 项）：
- 允许：`resume_extracted`、`manual_confirmed`、已确认求职身份 / 结构化候选人事实。
- 禁止：`manual_unconfirmed`、`unknown`、AI 推断 / 推测事实、对话记忆、常识、外部信息。
- `resume_hash` / `experience_bank_hash` 与 Pilot V1 完全一致，未做任何 Profile 改动。

## 11. 人工最终决策流程（ACCEPT / EDIT / REJECT）

逐条查看 `ai_*` 建议后：

1. **ACCEPT**：建议完全可接受 → 填写对应 `human_*` 确认值，`review_status = accepted`。
2. **EDIT**：taxonomy、粒度、importance、标签、证据或 topic 需调整 → 填写修订后的 `human_*`（`human_taxonomy_decision`、`human_match_label` 或 `human_eligibility_status`、`human_evidence_ids`、`human_grounding_reason`、`human_edit`），`review_status = edited`。
3. **REJECT**：该 requirement 不应存在或建议不可用 → `human_accept_reject = reject` 并在 `human_notes` 说明，`review_status = rejected`。

不要覆盖 `ai_*` 字段，以保留建议与人工结果之间的审计轨迹。

优先复核 `job_match_annotation_pilot_v2_need_human_review.csv` 中列出的低置信 / 有歧义项；其余行大多可快速 ACCEPT。岗位级 Overall Fit 在 JSON 的 job 层复核。
