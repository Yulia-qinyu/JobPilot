# JobPilot 岗位匹配（Job Analysis）评测案例研究

> 本文是一份 **AI 产品评测案例研究（AI Product Evaluation Case Study）**，用于展示评测方法与产品判断，
> **不是**生产级或论文级 benchmark。所有结论都带明确的样本量与置信度限定。
> 主语言：中文；`metric` / `model` / 关键术语保留英文以求精确。

---

## 0. 一句话结论

在 **真实 held-out 集（V2-Real, N=8 jobs / 32 requirements）分类质量基本持平**的前提下，
综合 **合成压力测试鲁棒性、technology adjacency 表现、延迟、首次调用成功率、token / cache 经济性**，
最终选择 **Qwen3.8-Max + Prompt C（`job-fit-v3-rubric-refined-v2`）** 作为生产 requirement matcher，
保留 **Kimi K3 + Control（`job-fit-v3-matchable-only`）** 作为 fallback。
**不主张 Qwen 在准确率上"更强"** —— 这是一个产品权衡决策，不是单一 F1 榜单。

---

## 1. 评测目标：这是一个什么样的 AI 决策问题

JobPilot 的 Job Analysis 需要回答："基于候选人**已验证**的经历与技能，Ta 与某个岗位的**能力匹配**程度如何？"

难点在于：这不是一次自由文本生成，而是一个**可核验、可解释、可复算**的结构化判断：

1. 判断必须落到**每一条岗位要求（requirement）**，而不是让 LLM 直接吐一个"整体匹配分"；
2. 每个 Strong / Partial 判断必须**引用候选人证据目录里的真实 evidence id**，不能编造经历；
3. 最终对用户展示的 Match Score 必须由**确定性公式**计算，而不是 LLM 的主观打分；
4. **招聘资格（eligibility）**与**能力匹配（capability match）**必须分层，一个高能力候选人**可以**同时"资格存疑"。

因此评测对象不是"模型聊得好不好"，而是 **requirement-level 语义匹配 + 证据 grounding + 分层语义 + 校准（calibration）**。

---

## 2. 产品与评测背景

### 2.1 Job Analysis 数据流

```
Stored Resume Profile  +  Eligible Evidence  +  Structured JD
        │
        ▼
requirement-level semantic matching   ← 本次评测的核心对象
        │
        ▼
validated evidence references（每个 Strong/Partial 引用 ≥1 个真实 evidence id）
        │
        ▼
deterministic Match Score（Importance 权重 × Match 系数，round_half_up）
        │
        ▼
Strengths / Gaps / 简历改写与准备建议
```

### 2.2 为什么不直接信任 LLM 的"整体匹配分"

- LLM 的整体打分**不可复算、不可审计**，且对 prompt 措辞高度敏感；
- 用户需要知道"**哪一条**要求匹配、**为什么**、**引用了哪段经历**"，一个黑盒分数无法支撑简历改写与面试准备；
- 把评分权交给确定性公式，可以在**不重跑模型**的前提下调整 Importance 权重、复算分数、做敏感性分析。

### 2.3 核心评测对象

| 对象 | 取值 | 是否进入 Match Score |
|---|---|---|
| **RequirementMatch**（matchable 要求） | Strong / Partial / Missing | 是（分子与分母都只由 matchable 组成） |
| **Eligibility**（学历 / 届别 / 明确年限 / 证书 / 语言门槛） | Supported / PotentialGap / Unknown | **否**（单独的"岗位资格"区核验） |
| **Knowledge**（原理 / 机制 / 架构 / 能力边界的理解） | 不评分 | 否（仅作面试准备主题） |
| **Subjective**（热情 / 学习意愿 / 态度） | 不评分 | 否（仅作非评分上下文） |

一个候选人可以是：`Capability Match = 86` 且 `Eligibility = PotentialGap / Ineligible`。**这是刻意设计，不是 bug。**

### 2.4 Requirement Taxonomy V2 的分类哲学

分类依据是 **Evidence Verifiability（证据可核验性）**，不是关键词类别：

> 对每条要求问一句："这条要求能否由允许的候选人履历证据**合理且稳定地**核验？"

- 能核验实践 / 经验 / 能力 → **matchable**
- 是明确资格 / 阻断门槛 → **eligibility**
- 主要是理论理解 → **knowledge**
- 只是态度 / 意愿 → **subjective**

例如"3 年以上 AI 产品经验"是 eligibility（`experience_years`），而不是再造一条同义 matchable；
"有 RAG 项目经验"是 matchable，"理解 RAG 原理"是 knowledge。

---

## 3. 评测问题（Research Questions）

| RQ | 问题 |
|---|---|
| **RQ1** | matcher 能否正确地在 **requirement 级别**分类候选人匹配度？ |
| **RQ2** | 它能否**始终基于已验证证据**、不虚构经历？ |
| **RQ3** | 它能否区分 **direct / adjacent / incomplete** 证据，尤其是 **Partial** 的边界？ |
| **RQ4** | requirement 级别的质量能否产出**有用的岗位级排序**（与 Human Match Fit 的一致性）？ |
| **RQ5** | 模型 / prompt 的改进能否**泛化到开发集之外**的真实岗位？ |
| **RQ6** | 哪个模型在 **答案质量 / 鲁棒性 / 延迟 / 可靠性 / cost·token 效率**上提供最好的 **production trade-off**？ |

---

## 4. 数据集设计（三种角色，严格分离）

### A. Dataset V1 —— 开发 / 模型选择集（NOT held-out）

- **30 个真实岗位**，**158 条 canonical requirements**：eligibility 42 / matchable 100 / knowledge 16；
  另有 **19 条 subjective expectations 单独存储**（不计入 158）。
- **100 条 matchable 的人工 Ground Truth**：Strong 52 / Partial 30 / Missing 18。
- 用途：**baseline 分析、跨模型对比（Round 1A/1B）、prompt 开发（Round 2A/2B）**。
- **明确定位：这是开发 / 模型选择数据，不是 held-out 验证集**；在其上做的调优不能声称已泛化。
- 后续的 **targeted taxonomy correction（8 条已确认）** 与 **lightweight Importance audit（8 条 reference cases）**
  是**评测治理改进**，不代表对全部 158 条做了穷尽式重标注（明确未做）。

  - taxonomy correction：1 条 `matchable → eligibility`（"硕士及以上学历"，纯学历门槛）；
    7 条 `matchable → subjective`（"沟通能力"、"逻辑思维与问题解决能力"、"用户感知力"等纯特质短语）。
  - Importance audit：发现 V1 的 Critical/Important/Preferred **从未被显式人工复核**（无 `human_importance` 字段、
    pre/verified 分布完全一致、changes 记录里 0 条 importance 改动）；对 8 条高敏感度 case 做了 reference
    calibration（5 条 Critical / 3 条 Preferred；其中 5 条由 Important 上修为 Critical）。

### B. Dataset V2-Real —— 小规模 held-out 真实验证集

- 存在 **16 个 provenance-verified 真实岗位**（人工确认从真实招聘页面复制、原文保留、无语义改写；
  部分无法回溯 URL，`source_url_missing = true`）。
- 最终 lightweight held-out 验证：**选 8 个代表性岗位 / 32 条 core matchable requirements / 32 个人工标签 /
  8 个 Human Match Fit 评分**。
- 人工标签分布：**Strong 15 / Partial 16 / Missing 1**；HMF：**[3, 5, 4, 4, 3, 2, 4, 4]**。
- **选择依据是 role-family / career-stage / scenario 多样性，不是模型表现**：
  ai_product 3 · platform_enterprise 2 · strategy_growth_fintech 1 · general_product 1 · mismatched_control 1。
- **显式局限**：N = 8 jobs；32 条 core requirements（非全量）；代表性而非穷尽；单一 annotator；
  Importance 仅做 lightweight 校准；岗位级"分数"是 4 条 core requirement 上的 representative-core score，
  不是完整生产打分。

### C. Dataset V2-Synthetic —— 行为压力测试集（behavioral stress test）

- **50 个合成岗位 / 65 条 probe requirements**（虚构公司名，`is_synthetic = true`）。
- **21 条 representative probes 已人工复核**，其余 **44 条为 scenario-derived**（`gt_source =
  scenario_derived_not_exhaustively_human_verified`）。
- **7 类 scenario category**：technology adjacency / project vs formal work / strong-partial boundary /
  partial-missing boundary / OR alternative / compound requirements / role-core mismatch。
- **明确声明：合成结果是行为压力测试证据，不是真实世界表现估计，且永远不与 V2-Real 指标合并。**

---

## 5. 指标体系（为什么需要多个指标）

单一指标会误导：高 Accuracy 可能掩盖某一类别的崩溃；高 Macro F1 也可能伴随 grounding 问题。因此分四层：

### 5.1 Requirement classification
Accuracy、**Macro F1**（主指标）、Strong / Partial / Missing 各自的 P/R/F1、confusion matrix。

### 5.2 Coverage / execution
- **Coverage**：模型成功给出结构化预测的 requirement 占比。
- **Effective Correct Coverage (ECC)**：**正确预测且成功 reconcile 的 requirement 数 ÷ 期望的 requirement 总数**。
  ECC 同时惩罚"分类错误"和"结构化输出 / join 失败"，是系统级 co-primary 指标。

### 5.3 Grounding
- **Grounding rate**：Strong/Partial 预测中引用了 ≥1 个有效 evidence id 的比例。
- **Unsupported Match rate**：Strong/Partial 预测中 0 引用（"无凭据匹配"）的比例。

### 5.4 Job-level
- **deterministic Match Score MAE**：模型 Match Score 与"人工 GT 推导分数"的平均绝对误差。
- **Spearman(model Match Score, Human Match Fit)**：岗位级排序一致性（V2-Real N=8，仅作 descriptive）。

### 5.5 Operations
mean / median / **p95 latency**、first-pass success、retry rate、structured-output reliability。

### 5.6 Economics
实际 prompt / completion / **cached** / **reasoning** token 用量、cost-per-job 框架、
projected cost / 100 与 / 1,000 jobs、cost-per-correct-requirement。

> **重要**：评测环境**无法核验** DashScope-mainland / Moonshot-mainland 的官方 unit price
> （repo 无 pricing 配置，历史记录均为 `PENDING_OFFICIAL_PRICING_VERIFICATION`），
> 因此**不报告任何编造的生产美元成本**，改用 **token 效率 + 参数化 pricing 方法论**。

---

## 6. Baseline —— Claude Sonnet

- Model：`claude-sonnet-4-5-20250929`；Prompt：`job-fit-v3-matchable-only`。

| metric | 值 |
|---|---|
| Accuracy | ~0.681 |
| Macro F1 | ~0.692 |
| ECC | 0.62 |
| Strong F1 | ~0.734 |
| Partial F1 | ~0.591 |
| Missing F1 | ~0.750 |
| Grounding | 1.00 |
| Unsupported Match | 0.00 |
| HMF Spearman | ~0.537 |

**关键误差模式**：Partial 成为"不确定性垃圾桶"。高频错误：Strong → Partial、Missing → Partial、Partial → Strong/Missing。

**产品洞察**：真正的挑战**不是虚构证据**（grounding 一直是 1.0），而是**证据充分性的校准（calibration of
evidence sufficiency）**—— 模型知道"引用哪段经历"，但不擅长判断"这段经历够不够 Strong"。

---

## 7. 模型对比（冻结的开发集结果）

| config | V1 Macro F1 | V1 ECC | V1 Accuracy | V1 Partial F1 | V1 HMF Spearman |
|---|---|---|---|---|---|
| **Qwen3.8-Max + Prompt C**（`job-fit-v3-rubric-refined-v2`） | ~0.786 | ~0.78 | ~0.78 | ~0.60（首个越过 0.60 的 config） | ~0.704 |
| **Kimi K3 + Control / Prompt A**（`job-fit-v3-matchable-only`） | ~0.740 | ~0.74 | — | — | ~0.723 |

- **Qwen + Prompt C** 被选为**开发集 primary**：首个同时通过 Macro F1 ≥ 0.75 / ECC ≥ 0.75 / Strong P ≥ 0.80 /
  Partial P ≥ 0.60 的 config，且比 Sonnet control 更快、token 更省、无 reasoning/temperature caveat。
- **Kimi K3 + Control** 作为 control / fallback finalist 保留：未加任何 rubric 指令时校准最稳，
  score↔HMF 相关性略高（0.723）；加任何 rubric block 反而让它的 Partial/Strong 边界不稳。

---

## 8. Prompt 消融 / error-driven iteration（A → B → C）

| prompt | 内容 | 结果 |
|---|---|---|
| **A / Control**（`job-fit-v3-matchable-only`） | 冻结的生产指令块 | 基线 |
| **B**（`job-fit-v3-rubric-aligned-v1`，Round 2A） | 加入 5 组规则：technology adjacency / project vs formal work / **OR 列表** / **compound / 最窄未满足子项** / Strong-Partial-Missing calibration | **部分有效、部分回归**：无模型达到 +0.05 Macro F1；compound 规则让所有 3 个模型在 compound slice 回归；OR 规则对 Kimi 明显有害；adjacency 帮到 2/3 |
| **C**（`job-fit-v3-rubric-refined-v2`，Round 2B） | **保留** adjacency guardrail + project-vs-formal-work + calibration；**移除** 脆弱的 OR 规则 + 跨模型回归的 compound 规则 | 对 Qwen3.8-Max 是**大幅开发集提升**（Macro F1 +0.084，SUPPORTED）；对 Kimi 反而 −0.017（任何 rubric block 都扰动其校准） |

**核心产品经验**：**prompt 迭代由观察到的 error slice 驱动，不是盲目堆指令**。Prompt C 是一次
**reduction / refinement**，不是又一次 expansion。

**V1 headline 提升**：Claude baseline ~0.69 Macro F1 → Qwen + Prompt C ~0.79。
**不能把这整段提升都归给 prompt engineering** —— **模型也换了**（Sonnet → Qwen3.8-Max）；
在同一模型（Qwen）上，Prompt C 相对 Qwen control 的净增益是 **+0.084（开发集）**。

---

## 9. Held-out V2-Real 结果

| metric | Qwen + Prompt C | Kimi + Control |
|---|---|---|
| Macro F1 | 0.8697 | 0.8920 |
| ECC / Accuracy | 0.8125 | 0.8438 |
| Strong P / R / F1 | 0.846 / 0.733 / **0.786** | 0.778 / 0.933 / **0.849** |
| Partial P / R / F1 | 0.778 / 0.875 / **0.824** | 0.923 / 0.750 / **0.828** |
| Missing F1（support = 1） | 1.00 | 1.00 |
| Grounding / Unsupported | 1.00 / 0.00 | 1.00 / 0.00 |
| Match Score MAE（vs GT repr-core） | 9.5 | **7.625** |
| HMF Spearman（N=8，descriptive） | **0.7608** | 0.7506 |
| mean / p95 latency | **15.3 s / 17.8 s** | 34.1 s / 58.8 s |
| first-pass success | **8 / 8**（0 retries） | 7 / 8（1× HTTP 429，retry 后恢复） |

### 正确解读

- **真实 held-out 分类结果实质是"平局（tie）"**。Kimi 名义领先 = **32 条里多对 1 条**（+0.022 Macro F1 / +0.031 ECC）。
- **不能说 Qwen "打败" 了 Kimi**，也不能反过来说：在 N=8 jobs / 32 rows 下，**一个标签翻转 ≈ 0.03 Macro F1**。
- **共同 failure**：两个模型都把**"通用 AI 经验 + 相邻行业证据"当成满足"保险场景 AI 要求"**（GT 为 Partial，
  两者都判 Strong）。
- **Qwen 倾向**：对部分通用 PM 强项偏保守（Strong → Partial 4 次）。
- **Kimi 倾向**：对相邻证据偏宽松（Partial → Strong 4 次）。

### RQ5 的回答：开发集提升**没有**完全泛化

Qwen + Prompt C 在 V1 相对 control 的 **+0.084 Macro F1**，在 V2-Real **没有**转化为分类领先
（Qwen 0.870 vs Kimi 0.892，落在噪声内）。**Prompt C 的价值不是真实世界准确率的跃升，而是在
targeted failure mode（technology adjacency）上的鲁棒性**（见 §10）。

---

## 10. 合成压力测试结果

### 人工复核 probe subset（20 条 S/P/M，B01 eligibility 排除）

| metric | Qwen + Prompt C | Kimi + Control |
|---|---|---|
| Macro F1 | **0.903** | 0.836 |
| ECC / Accuracy | **0.90** | 0.85 |

### 最重要的 scenario：technology_adjacency

| | Qwen | Kimi |
|---|---|---|
| accuracy | **1.00** | **0.33** |

**解读**：Prompt C 引入的 **adjacency guardrail 泛化到了它被设计去解决的那一个压力测试 failure mode**
（Kimi 无指令时把"通用 LLM / 模型评估经验"上修为 multimodal / 训练类要求的 Partial/Strong）。
这**比"Prompt C 普遍提升所有真实世界准确率"是更强、也更诚实的证据**。

### All-matchable 合成（98 条，多数为 scenario-derived）

| metric | Qwen | Kimi |
|---|---|---|
| Macro F1 | 0.785 | **0.811** |
| ECC | 0.796 | **0.837** |

**不隐藏这个结果**：该 slice Kimi 略优，**但证据权重更弱**——78/98 的标签是 scenario-derived 而非人工复核。
两个模型都在 `partial_missing_boundary`（0.67）上失手；Qwen 另在 `role_core_mismatch`（0.67）失手一次。

---

## 11. Grounding 发现

两个 finalist 在**所有 slice** 上都达到：**Grounding = 1.00 / Unsupported Match = 0.00**。
即：**做 Strong / Partial 判断时，模型都引用了冻结证据目录里的有效 evidence**——RQ2 通过。

### 评测基础设施修正（不是模型调优）

首次运行时 grounding 指标读到 **0**，原因是本次 harness 从冻结快照构造 `EvidenceCatalog` 时，
`evidence_id` 已内含 `source_type` 前缀，生产序列化又加了一次，导致 prompt 里出现
`resume_extracted:resume_extracted:16` 这样的**双前缀 surface format**；模型忠实地回显了这些 id，
而校验用的是未加倍的形式。**修正方式**：把校验集改成"assembled prompt 里实际出现的 `evidence_source_id` 集合"。
**没有任何模型预测或分类指标被改动**——这是一次 **evaluation-infrastructure correction**。

---

## 12. 延迟 / 可靠性

| | Qwen + Prompt C | Kimi + Control |
|---|---|---|
| V2-Real mean / p95 latency | **15.3 s / 17.8 s** | 34.1 s / 58.8 s |
| V2-Synthetic mean latency | **10.0 s** | 22.4 s |
| first-pass success（58 calls） | **58 / 58** | 57 / 58 |
| retries（58） | **0** | 3（1× HTTP 429 engine_overloaded） |
| final structured-output success | 58 / 58 | 58 / 58 |

**解读**：Qwen **约快 2.2×**，尾延迟（p95）明显更紧。两者最终都可靠，但 Qwen 首次调用更干净。

---

## 13. 成本 / token 经济学（T5.5 实测）

| | Qwen（58 calls） | Kimi（58 calls） |
|---|---|---|
| prompt tokens | 185,351 | 165,140 |
| completion tokens | 38,683 | 37,603 |
| **reasoning tokens** | **0** | **4,763（≈ completion 的 13%）** |
| total tokens | 224,034 | 202,743 |
| prompt cache hit（overall / V2-Real） | **~41% / ~90%** | ~13% / ~6% |
| raw tokens / correct V2-Real requirement | 1,355 | **1,191** |
| **cache-adjusted** billable tokens / correct req（0.25 cache 价） | **~646** | ~1,148 |

- **Raw tokens**：Kimi 略省（Control 指令块比 Prompt C 短，合成集 completion 略少）。
- **Cache-adjusted**：**Qwen 更高效**——Prompt C 指令块跨调用稳定 → 高 cache 命中；且**零 reasoning-token 开销**。
  在任何有 context-cache 折扣的计价下，Qwen 的**有效计费 input** 明显更低。

> **官方 unit price 无法在评测环境核验**，因此：**不报告编造的生产美元成本**；
> 成本以**实际 token 用量**表达；保留**参数化 pricing 公式**
> `cost/call = (uncached_in·Pin + cached_in·Pcache + out·Pout)/1e6`；后续可代入已核验的 provider 价格。
> **模型决策把 token 效率当作 cost proxy，而不是声称一个确切的省钱数字。**

---

## 14. 最终模型选择作为产品决策

### 决策表

| 维度 | 结论 |
|---|---|
| Real held-out 分类质量 | **平局 / Kimi 名义微弱领先**（+1/32 条，落在 N=8 噪声内） |
| 人工复核合成鲁棒性 | **Qwen**（probe Macro F1 0.903 vs 0.836） |
| technology adjacency | **Qwen 明显**（1.00 vs 0.33） |
| Grounding | **平局**（1.00 / 0.00） |
| HMF 排序一致性 | **平局**（0.761 vs 0.751） |
| 延迟 | **Qwen 明显**（~2.2×，p95 更紧） |
| 首次调用可靠性 | **Qwen 略优**（58/58，0 retry） |
| token / cache 效率 | **Qwen 在 cache-adjusted workload 下更优**；确切美元价未定 |
| **生产推荐** | **Qwen3.8-Max + Prompt C** |
| **Fallback** | **Kimi K3 + Control** |

### 两阶段决策哲学

**Stage 1 —— Quality / Safety Gate（两个模型都通过）**
- 分类质量（V2-Real Macro F1 0.87 / 0.89，ECC 0.81 / 0.84）
- grounding = 1.00、unsupported = 0.00
- structured-output reliability = 100%

**Stage 2 —— Product Efficiency（因为 V2-Real 质量实质持平，比这些）**
- targeted robustness（technology adjacency）
- latency
- first-pass reliability
- token / cache economics

**结论**：**Qwen3.8-Max + Prompt C 提供更好的 production trade-off。**
**不主张它是"普遍更准确"的模型**——真实 held-out 分类是平局。

---

## 15. 关键产品 / AI PM 经验

1. **在 requirement 级别评测，而不是只看岗位级分数** —— 只有 requirement 级别的 Ground Truth
   才能支撑简历改写、Gap 提示与面试准备。
2. **把招聘 eligibility 与 capability match 分层** —— 高能力候选人可以同时"资格存疑"，
   把两者揉进一个分数会同时损害两边。
3. **Grounding 好 ≠ calibration 好** —— 模型知道"引用哪段经历"，却不擅长判断"这段经历够不够 Strong"；
   评测必须单独测 calibration。
4. **Partial 是产品语义问题，不只是 LLM 准确率问题** —— 需要在 prompt / rubric 里明确
   "Partial ≠ 不确定"，否则它会退化成不确定性垃圾桶。
5. **Prompt 规则要瞄准观察到的 failure mode** —— Prompt B 盲目加 5 组规则里有 2 组跨模型回归；
   Prompt C 是做减法（移除 OR / compound 规则）后才拿到增益。
6. **Held-out 验证可以推翻开发集的"胜利"** —— Prompt C 在 V1 的 +0.084 Macro F1，在 V2-Real
   没有转化为分类领先；它真正泛化的是 adjacency 鲁棒性。
7. **合成数据集用于 targeted robustness，绝不能当成真实世界准确率** —— 44/65 probe 是 scenario-derived，
   合成指标永远不与 V2-Real 合并。
8. **模型选择是跨 质量 / 鲁棒性 / 延迟 / 可靠性 / 成本 的产品决策，不是单一 F1 榜单** —— 用
   quality-floor + product-efficiency 两阶段框架。
9. **评测 harness 质量本身很重要** —— 一个 evidence-id 双前缀的 measurement bug 一度让 grounding 读成 0，
   差点得出错误的模型结论；修正后无任何预测 / 指标改动。
10. **保留原始 GT / predictions，让 post-run 修正可审计** —— 所有冻结 artifact 保留 hash；
    grounding 修正与单次 429 retry 都在 artifact 里显式记录。

---

## 16. 局限性（作为 AI PM 案例研究的 scope boundary，而非项目弱点）

- **V2-Real N = 8 jobs / 32 rows** —— 真实 held-out 分类比较**只能**是平局（统计功效不足）。
- **单一 annotator**；**Importance 仅 lightweight 校准**（8 条 reference cases，其余仍为
  `importance_not_explicitly_human_verified`）。
- **岗位级"分数"是每岗 4 条 core requirement 上的 representative-core score**，不是完整生产打分。
- **合成集多数标签为 scenario-derived**（44/65），only 21 条人工复核。
- **部分真实岗位的 company / provenance 元数据不完整**（13/16 company unknown，无 source URL）。
- **官方 pricing 未核验** —— 成本以 token 效率 + 参数化公式表达。
- **延迟为评测环境到 mainland endpoint 的实测**，生产网络路径可能不同。
- **这是一份 AI 产品评测案例研究，不是生产级 / 论文级 benchmark。**

---

## 17. 简历 / 面试版本

### A. 简历版（2–3 条）

- 搭建 AI 岗位匹配（Job Analysis）**requirement-level 评测体系**：构建 requirement 级 Ground Truth，
  覆盖分类准确率（Macro F1 / ECC）、证据 **Grounding**、岗位排序（Spearman vs Human Match Fit）
  及 **7 类行为压力测试**；通过多模型对比与 **error-driven Prompt ablation**（A→B→C，做减法而非堆指令），
  将开发集 Macro F1 从约 **0.69**（Claude baseline）提升至约 **0.79**（Qwen3.8-Max + Prompt C）。

- 构建**独立 held-out 真实验证集**（8 jobs / 32 human-reviewed requirements / 8 Human Match Fit）与
  **合成压力测试集**（50 jobs / 65 probes），发现**开发集提升未完全泛化到真实集**（V2-Real 分类实质平局），
  但**针对 technology adjacency 的鲁棒性显著提升（accuracy 1.00 vs 0.33）**；定位"通用 AI + 相邻行业证据
  过度匹配垂直行业要求"等核心 failure modes，并指出真正瓶颈是**证据充分性校准**而非虚构证据。

- 以 **quality-floor + product-efficiency 两阶段框架**做 production model selection：综合真实集质量、
  Grounding、延迟（p95）、首次调用成功率与 **token / cache economics**，在真实集质量基本持平的情况下选择
  **Qwen3.8-Max + Prompt C**（响应约快 **2.2×**、cache-adjusted token 更省、零 reasoning-token 开销），
  并保留 **Kimi K3 + Control** 作为 fallback；同时修复一个会导致错误模型结论的评测 harness measurement bug。

### B. 60–90 秒口头版

> JobPilot 的岗位匹配要回答"候选人已验证的经历与某个岗位有多匹配"。我们没有让 LLM 直接打一个整体分——
> 那不可复算、不可解释——而是让它在 **每一条岗位要求**上判 Strong / Partial / Missing，并强制引用候选人证据目录里
> 的真实 evidence id，最后由确定性公式算 Match Score。
>
> 我为此建了三层数据集：V1 是 30 个真实岗位、100 条 matchable 人工标签，用来选模型和迭代 prompt；
> V2-Real 是**独立的 held-out** 真实小集（8 岗 / 32 条人工标签）；V2-Synthetic 是 50 个合成岗、65 条 probe，
> 专门压测 7 类已知 failure mode。
>
> 关键发现有三个：第一，baseline 的问题不是虚构证据（grounding 一直 100%），而是**证据够不够 Strong 的校准**；
> 第二，我们通过 **error-driven 的 prompt 迭代**（关键是做减法，去掉两条跨模型回归的规则）把开发集 Macro F1
> 从 0.69 拉到 0.79，但**在真实 held-out 上，这个提升没有转化为分类领先——两个 finalist 实质打平**；
> 第三，Prompt C 真正泛化的是 **technology adjacency 的鲁棒性**，合成集上 1.00 vs 0.33。
>
> 所以最终模型选择不是看谁 F1 高——真实集是平局——而是用两阶段框架：先过质量 / 安全门槛，再比鲁棒性、
> 延迟、可靠性、token 经济性。Qwen3.8-Max + Prompt C 约快 2.2×、cache 命中更高、没有 reasoning-token 开销，
> 是更好的产品权衡；Kimi 作为 fallback。

### C. 3 分钟详细版

> **问题定义**：Job Analysis 需要一个可核验、可解释、可复算的匹配判断。难点是把判断落到每一条 requirement，
> 强制证据引用，评分交给确定性公式，并且把招聘 eligibility 和能力 match 分层——一个高能力候选人可以同时资格存疑。
>
> **Taxonomy**：分类依据是"这条要求能否被履历证据稳定核验"，不是关键词——所以"3 年经验"是 eligibility，
> "有 RAG 项目"是 matchable，"理解 RAG 原理"是 knowledge，只有 matchable 进 Match Score。
>
> **数据集**：V1（30 岗 / 158 canonical / 100 matchable 人工 GT）是开发集；V2-Real（8 岗 / 32 条）是
> **独立 held-out**，选岗按角色和职业阶段多样性、不看模型表现；V2-Synthetic（50 岗 / 65 probe / 7 类场景）
> 是压力测试，其中只有 21 条人工复核、44 条是 scenario-derived，**永远不和真实指标合并**。
>
> **指标**：Macro F1 和 ECC 是 co-primary（ECC = 正确且成功 reconcile ÷ 期望总数，同时惩罚分类错误和
> 结构化输出失败）；再加 grounding rate、unsupported match rate、Match Score MAE、Spearman vs Human Match Fit，
> 以及延迟 / 首次成功率 / token 经济性。
>
> **结果**：Claude baseline Macro F1 ~0.69，Partial 是"不确定性垃圾桶"，grounding 却是 100%——说明瓶颈是
> **校准**。我做 A→B→C 的 prompt 迭代：B 盲加 5 组规则，其中 OR 和 compound 两组跨模型回归；C 做减法只留
> adjacency guardrail + project-vs-formal-work + calibration，Qwen 上开发集 +0.084。**但在 V2-Real，Qwen+C
> 0.870 vs Kimi+Control 0.892——实质平局，一个标签翻转就是 0.03 Macro F1**。两个模型都有同一个 failure：
> 把通用 AI + 相邻行业证据当成满足保险场景 AI 要求。Prompt C 真正泛化的是 adjacency：合成集 1.00 vs 0.33。
>
> **决策**：两阶段。Stage 1 两个模型都过质量 / grounding / 可靠性门槛。Stage 2 因为真实集平局，比 targeted
> robustness、延迟、可靠性、token 经济性——Qwen 快 2.2×、cache 命中 90%（V2-Real）、零 reasoning token，
> 是更好的 production trade-off。Kimi 作 fallback。过程中还修了一个 evidence-id 双前缀的 harness bug，
> 它一度让 grounding 读成 0，修正后无任何预测 / 指标改动，全程保留 artifact hash。

### D. 面试官可能追问 + 简要答点

| 追问 | 答点 |
|---|---|
| **N=8 的 held-out 有什么意义？** | 承认统计功效不足；它的作用是"证伪开发集的过度乐观"，不是"证明谁更准"。真实集平局本身就是重要发现——阻止了把开发集 +0.084 当成生产收益。 |
| **既然真实集平局，为什么不选 Kimi（它名义 Macro F1 更高）？** | 因为差距是 +1/32 条、落在噪声内，不构成可"购买"的质量增量；而 Qwen 在 targeted robustness、延迟（2.2×）、首次可靠性、cache 经济性上都更好。这是产品决策，不是 F1 榜单。 |
| **Prompt C 的增益到底来自 prompt 还是换模型？** | V1 从 0.69→0.79 是 prompt + 模型都变了；在同一模型 Qwen 上，Prompt C 相对 control 的净增益是 +0.084（开发集）。held-out 上这个增益表现为 adjacency 鲁棒性，不是整体准确率。 |
| **合成集 all-matchable 上 Kimi 反而更高，怎么解释？** | 不隐藏这个结果。该 slice 78/98 是 scenario-derived 标签，证据权重弱；人工复核的 21 条 probe subset 上 Qwen 0.903 vs Kimi 0.836，且 adjacency 1.00 vs 0.33。 |
| **grounding 100% 是不是太好看了？** | 这是"是否引用了有效 evidence id"，不是"引用得对不对"。模型的问题在校准（够不够 Strong），不在编造——这正是评测要区分的。曾因 harness id 格式 bug 读成 0，修正过程有记录。 |
| **成本为什么没有美元数字？** | 环境无法核验 qwen3.8-max / kimi-k3 的官方 mainland 单价，repo 也无 pricing 配置。按"不编造价格"原则，给出实测 token 用量 + 参数化公式 + placeholder 敏感性网格，代入已核验价格即可得账单。 |
| **如果要再投入，下一步做什么？** | 扩 V2-Real 到 24–30 真实岗、多 annotator、做完整 Importance 校准与全 65 条 probe 人工复核，再复算 Spearman(GT, HMF) 的 construct validity；并把"垂直行业相邻证据过度匹配"做成一个专门的 error slice 持续监控。 |

---

## 18. Artifact 索引

| 阶段 | 关键 artifact |
|---|---|
| Baseline | `job_match_baseline_claude_current_v1_*` |
| 模型对比 | `benchmark_round1/`、`benchmark_cross_provider/`（Round 1A/1B） |
| Prompt 消融 | `prompt_ablation_round2a/`、`prompt_refinement_round2b/`（Round 2A/2B），checkpoint `a82ee17` |
| Taxonomy / Importance 治理 | `importance_audit/`、`dataset_v1_corrected_evaluation_view.json` |
| Held-out GT 冻结 | `dataset_v2/v2_real_lightweight_gt_human_verified.*`、`dataset_v2/final_heldout_gt_manifest.*`、`dataset_v2_synthetic/synthetic_gt_frozen.json` |
| Held-out 评测（T5） | `dataset_v2/heldout/{qwen_prompt_c,kimi_control}/`、`dataset_v2_synthetic/heldout/…`、`finalist_heldout_comparison.{json,md}` |
| 成本经济学（T5.5） | `finalist_cost_analysis.{json,md}`、`finalist_heldout_comparison.md` 的 "Production Economics" 段 |
| 本文 | `job_analysis_evaluation_final_summary.md` |

**Job Analysis 评测到此结束。** 下一步是评测 close-out commit / push（T7），之后转向轻量的 Daily Planning Agent 评测。
