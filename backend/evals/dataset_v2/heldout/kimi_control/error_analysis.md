# V2-Real held-out error analysis — kimi-k3 + Control / Prompt A (job-fit-v3-matchable-only)

N = 8 jobs · 32 human-reviewed matchable GT rows. **Not a production benchmark; N is small.**

- Macro F1 **0.892** · ECC **0.8438** · accuracy 0.8438 · coverage 1.0
- per-class F1: Strong 0.8485 · Partial 0.8276 · Missing 1.0 (Missing support = 1)
- grounding 1.0 · unsupported-match 0.0
- Match-Score MAE vs GT representative-core 7.625 · Spearman(model score, HMF) 0.7506 (N=8, descriptive only)
- mean latency 34134.3 ms · first-pass 7/8 · final 8/8 · retries 3

## Confusion (rows = GT, cols = pred)

| | Strong | Partial | Missing |
|---|---|---|---|
| **Strong** | 14 | 1 | 0 |
| **Partial** | 4 | 12 | 0 |
| **Missing** | 0 | 0 | 1 |

## Disagreements (all)

- 校招-AI产品经理（人才专项） — GT **Partial** / pred **Strong** — 探索大模型、Agent、RAG等AI技术在智能咨询、核保辅助、保险教育等真实业务场景中的应用，打造用户真正需要的智能化产品
- 校招-AI产品经理（人才专项） — GT **Partial** / pred **Strong** — 结合用户反馈和业务数据，持续优化AI应用效果，对核心指标(用户满意度、转化率、使用率)负责
- AI策略产品经理 — GT **Strong** / pred **Partial** — 负责抖音产品工作，独立跟进子项目的需求分析与规划，产品需求梳理
- 平台AI产品经理 — GT **Partial** / pred **Strong** — 参与内部协同办公、AI创新、研发效能、财务&HR相关产品领域革新，通过云、大数据、机器学习等基础设施，追求极致化效率与体验，并带来管理数字化变革
- 产品经理 — GT **Partial** / pred **Strong** — 负责用户需求的调研、分析、评估和原型设计

## Job-level Match Score vs GT vs HMF

| job | model score | GT repr-core score | |Δ| | HMF |
|---|---|---|---|---|
| 校招-AI产品经理（人才专项） | 75 | 50 | 25 | 3 |
| AI策略产品经理 | 88 | 100 | 12 | 5 |
| 平台AI产品经理 | 100 | 88 | 12 | 4 |
| 增长产品经理（平台经营） | 75 | 75 | 0 | 4 |
| AI产品经理 | 61 | 61 | 0 | 3 |
| 用户增长-用户运营管培生 | 38 | 38 | 0 | 2 |
| 产品经理 | 100 | 88 | 12 | 4 |
| 游戏AI产品经理（北京） | 75 | 75 | 0 | 4 |
