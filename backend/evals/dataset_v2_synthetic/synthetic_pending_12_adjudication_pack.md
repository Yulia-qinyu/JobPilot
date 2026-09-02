# Synthetic — 12 Pending Representative Probe Adjudication Pack

The 12 probe rows selected in T4. Human enters Strong / Partial / Missing only. The 9 already-confirmed decisions are NOT re-opened. No new synthetic cases.

Category coverage: {'technology_adjacency': 3, 'project_vs_formal_work': 2, 'strong_partial_boundary': 2, 'or_alternative': 2, 'role_core_mismatch': 3}

### A01 · technology_adjacency — 多模态大模型产品经理

- requirement: 具备图文 / 视频 / 语音多模态大模型产品经验  ·  type matchable  ·  importance Critical
- draft expected label: **Missing** — 仅 LLM/RAG，无多模态(图文/视频/语音)大模型产品证据
- requested capability: 图文/视频/语音多模态大模型产品经验
- evidenced / adjacent: LLM application development (ai_experience:0), RAG (ai_experience:4), GoFin conversational LLM (ev 28)
- absent: multimodal (image/video/speech) large-model product experience
- human_match_label = ___ ; human_match_notes = ___

### A08 · technology_adjacency — 强化学习训练产品经理

- requirement: 有 RLHF / 强化学习 / 偏好对齐训练经验  ·  type matchable  ·  importance Critical
- draft expected label: **Missing** — 仅一般模型训练辅助与性能评估；大模型精度调优/基模/强化学习训练技术相邻不足以判 Partial (ev 22,ai_experience:11)
- requested capability: RLHF / 强化学习 / 偏好对齐训练经验
- evidenced / adjacent: data cleaning + feature engineering + data support for model training (ev 22); 模型性能评估 (ai_experience:11)
- absent: RLHF / RL / preference-alignment training ownership
- human_match_label = ___ ; human_match_notes = ___

### A08 · technology_adjacency — 强化学习训练产品经理

- requirement: 有模型效果评估经验  ·  type matchable  ·  importance Important
- draft expected label: **Partial** — 有 KPI/训练数据/模型评估，但未独立设计 AI 产品评测集 (ev 19,22,ai_experience:11)
- requested capability: 模型效果评估经验
- evidenced / adjacent: KPI / training data / 模型性能评估 (ev 19, 22, ai_experience:11); NLP project 模型训练评估 (ev 29)
- absent: independently designed AI-product evaluation set
- human_match_label = ___ ; human_match_notes = ___

### B01 · project_vs_formal_work — 资深 AI 产品经理

- requirement: 3 年以上正式 AI 产品经理工作经验  ·  type eligibility  ·  importance Critical
- draft expected label: **PotentialGap** — 已验证为早期职业/应届+实习+单段 Product Owner，与‘3年以上正式工作经验’门槛存在明确冲突
- requested capability: 3 年以上正式 AI 产品经理工作经验 (eligibility gate)
- evidenced / adjacent: verified job-seeker identity: 应届 / 校招, 2027届 (manual_confirmed); internships + one Product-Owner project
- absent: 3+ years of formal AI-PM employment tenure — explicit conflict with verified new-grad status
- human_match_label = ___ ; human_match_notes = ___

### B03 · project_vs_formal_work — AI 应用交付产品经理

- requirement: 有 AI 功能的完整动手交付经验（强调实操而非正式任职年限）  ·  type matchable  ·  importance Critical
- draft expected label: **Strong** — GoFin 完整落地：需求→设计→跨职能→迭代→上线 (ev 28,product_experience:9)
- requested capability: 有 AI 功能的完整动手交付经验（强调实操而非正式任职年限）
- evidenced / adjacent: GoFin full landing: 需求→设计→跨职能→迭代→上线 (ev 28, product_experience:9); LLM/RAG delivery
- absent: none material for the hands-on framing (repeated delivery not required by this requirement)
- human_match_label = ___ ; human_match_notes = ___

### C03 · strong_partial_boundary — 数据产品经理

- requirement: 曾以数据产品经理身份独立负责完整数据产品  ·  type matchable  ·  importance Critical
- draft expected label: **Partial** — 有数据体系/运营/产品策划，但未以数据产品经理身份负责完整产品 (ev 16,18,28)
- requested capability: 曾以数据产品经理身份独立负责完整数据产品
- evidenced / adjacent: data systems / 潜客数据架构 / ETL (ev 18); growth-ops (ev 16); product planning (GoFin, ev 28)
- absent: ownership of a complete product as a Data Product Manager
- human_match_label = ___ ; human_match_notes = ___

### C06 · strong_partial_boundary — 大模型应用产品经理

- requirement: 具备 Prompt / 上下文工程的完整实践经验  ·  type matchable  ·  importance Critical
- draft expected label: **Partial** — LLM/RAG/Agent 交付明确，但无单独可验证的 Prompt/上下文工程完整实践 (ev 28,ai_experience:0,4)
- requested capability: 具备 Prompt / 上下文工程的完整实践经验
- evidenced / adjacent: LLM/RAG/Agent delivery in GoFin (ev 28, ai_experience:0, ai_experience:4)
- absent: a separately verifiable, complete Prompt / context-engineering practice
- human_match_label = ___ ; human_match_notes = ___

### E01 · or_alternative — 行业 AI 产品经理

- requirement: 有 金融 或 保险 或 支付 行业经验（满足其一即可）  ·  type matchable  ·  importance Critical
- draft expected label: **Strong** — 支付/银行/金融产品/合规 (ev 16,24,26,domain_experience:0)
- requested capability: 有 金融 或 保险 或 支付 行业经验（满足其一即可）
- evidenced / adjacent: 支付 / 银行 / 金融产品 / 合规 (ev 16, 24, 26, domain_experience:0)
- absent: insurance branch specifically (not required — one branch suffices)
- human_match_label = ___ ; human_match_notes = ___

### E03 · or_alternative — 数据方向产品经理

- requirement: 熟练使用 SQL 或 Python 进行数据分析（满足其一即可）  ·  type matchable  ·  importance Critical
- draft expected label: **Strong** — SQL 技能目录 + SQL 触发器/归因项目 (ev 18,skills:4)
- requested capability: 熟练使用 SQL 或 Python 进行数据分析（满足其一即可）
- evidenced / adjacent: SQL skill + SQL triggers / attribution project (ev 18, skills:4); Python 百万级数据 EDA (ev 30, skills:0)
- absent: none material
- human_match_label = ___ ; human_match_notes = ___

### G01 · role_core_mismatch — 私域用户运营专员

- requirement: 有私域社群 / SCRM 运营经验  ·  type matchable  ·  importance Critical
- draft expected label: **Missing** — 无私域社群/SCRM 运营经验
- requested capability: 有私域社群 / SCRM 运营经验
- evidenced / adjacent: growth-ops (ev domain_experience:3); data analysis (ev 19)
- absent: private-domain community / SCRM operations experience
- human_match_label = ___ ; human_match_notes = ___

### G01 · role_core_mismatch — 私域用户运营专员

- requirement: 有用户增长 / 转化优化经验  ·  type matchable  ·  importance Important
- draft expected label: **Strong** — KPay 增长策略/增长运营/转化优化 (ev 16,19,domain_experience:3)
- requested capability: 有用户增长 / 转化优化经验
- evidenced / adjacent: KPay 增长策略 / 增长运营 / 转化优化 (ev 16, 19, domain_experience:3)
- absent: none material
- human_match_label = ___ ; human_match_notes = ___

### G03 · role_core_mismatch — 智能硬件产品经理

- requirement: 有智能硬件 / 终端产品从设计到量产的经验  ·  type matchable  ·  importance Critical
- draft expected label: **Missing** — 无智能硬件/终端产品从设计到量产经验
- requested capability: 有智能硬件 / 终端产品从设计到量产的经验
- evidenced / adjacent: none — software/AI-product and data roles only
- absent: smart-hardware / terminal product design-to-mass-production experience
- human_match_label = ___ ; human_match_notes = ___

