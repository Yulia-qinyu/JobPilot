# JobPilot Ground Truth Annotation Pilot V1 — Review Guide

## 目的与边界

这份 Pilot 让人工评审者以 **ACCEPT / EDIT / REJECT** 为主完成复核。CSV/JSON 中的 `*_suggestion` 全部是 AI 建议，不是 Ground Truth；所有 `human_*` 字段保持空白，所有 `review_status` 初始为 `pending`。

可用证据仅来自 JSON 中的 bounded evidence catalog：`resume_extracted`、`manual_confirmed` 和已确认求职身份。不得使用 `manual_unconfirmed`、推测、未记录的经验、技能、年限或 ownership。

## 1. 一个 requirement 的边界

一个 requirement 应当能够被独立判断。若一句话包含不同证据路径或不同重要性，应拆分；同一能力的自然组合不必拆成许多小词。

真实例子：

- 腾讯 Agent 岗的“**一年以上 AI/Agent 产品经验，有完整落地项目经历；计算机科学或相关技术领域的本科及以上学历**”拆为年限、完整落地、学历三项，因为三者分别需要时长、项目和教育证据。
- 腾讯增长岗的“**通过数据分析与 AB 实验驱动产品迭代**”拆为数据分析和 AB 实验，因为候选人对前者有直接证据、后者没有。
- 华为的“**逻辑/概率思维、分析、归纳、沟通和解决问题**”保留为一个综合软能力要求；继续拆成五项会造成过细、重复判断。

不得从岗位职责推断候选资格，不得补写 JD 没有明确表达的隐含门槛。

## 2. Critical / Important / Preferred

- **Critical**：明确的阻断性门槛，如最低学历、最低工作年限、明确语言或资格要求。不要仅因为一项能力听起来重要就标 Critical。
- **Important**：做好岗位所需的核心能力、知识或经验。
- **Preferred**：JD 明确写为“优先 / 加分 / preferred / plus”的条件。

真实例子：百度 AI 产品实习岗的“本科及以上学历在读”是 Critical；同句中的“计算机、人工智能相关专业优先”单独拆为 Preferred。腾讯 Agent 岗“一年以上”是 Critical，而“Agent 评测经验者优先”是 Preferred。

## 3. Strong / Partial / Missing

- **Strong**：已验证证据直接且充分支持要求。
- **Partial**：存在相关证据，但只覆盖部分、方向相邻、深度/范围较弱，或缺少要求的年限。
- **Missing**：没有可用的已验证支持证据；不表示候选人一定没有该能力。

真实例子：腾讯证券 AI 产品岗要求“3年以上互联网产品经验”。候选人有直接 AI 产品项目和实习，但时长不足，因此建议 Partial，不得把项目自动折算为三年职业经验。百度创意策略岗要求短剧/漫剧资深经历，当前目录没有相关事实，因此建议 Missing。

## 4. 硬要求

年限、学历、毕业届别、资格、证书和明确语言门槛必须逐项验证。相邻项目经验不能证明指定就业年限。百度通用产品实习岗“实习不少于五个月”描述的是未来可用性；历史五个月实习不等于已确认未来可用性，所以建议 Missing，并列入歧义复核。

## 5. Evidence grounding

每个 Strong / Partial 必须引用至少一个稳定 `evidence_id`，并用一句话解释证据如何连接要求。理由不能只复述证据。Missing 通常保持空 evidence ID，并说明当前缺少哪类已验证支持。

例：腾讯 AI 数据产品岗“熟练 SQL”引用 `resume_extracted:18` 和 `resume_extracted:resume:1:skills:4`，因为一个证明 SQL 实践，一个证明技能记录。其“Prompt、RAG、Agent 实践”只建议 Partial，因为 RAG/Agent 有证据，但 Prompt 工程没有单独事实。

## 6. Overall Fit 1–5

- **5 — Very Strong Fit**：大多数重要要求被强支持，未见明显硬门槛。
- **4 — Good Fit**：总体匹配，存在可管理的 gap。
- **3 — Mixed / Plausible Fit**：有实质相关性，但若干重要要求较弱或缺失。
- **2 — Low Fit**：存在部分重合，但关键要求明显不足。
- **1 — Clearly Unsuitable**：根本岗位方向不匹配或存在重大硬门槛。

Overall Fit 是人工判断标签，不能由生产 Match Score 公式机械推导。本 Pilot 没有计算 Match Score。

## 7. ACCEPT / EDIT / REJECT

逐条查看 AI 建议后：

1. **ACCEPT**：建议完全可接受；将对应 human 字段填写为确认值，并把 `review_status` 改为 `accepted`。
2. **EDIT**：粒度、importance、match 或证据需要调整；填写修订后的 human 字段，状态为 `edited`。
3. **REJECT**：该 requirement 不应存在或建议不可用；说明原因并设为 `rejected`。

不要直接覆盖 `*_suggestion`，这样才能保留建议与人工结果之间的审计轨迹。Job-level Overall Fit 可在 JSON 的 job 层复核；CSV 为便于筛选，在每条 requirement 上重复显示建议值，但人工值仍需明确填写。
