# V2-Real held-out error analysis — qwen3.8-max + Prompt C (job-fit-v3-rubric-refined-v2)

N = 8 jobs · 32 human-reviewed matchable GT rows. **Not a production benchmark; N is small.**

- Macro F1 **0.8697** · ECC **0.8125** · accuracy 0.8125 · coverage 1.0
- per-class F1: Strong 0.7857 · Partial 0.8235 · Missing 1.0 (Missing support = 1)
- grounding 1.0 · unsupported-match 0.0
- Match-Score MAE vs GT representative-core 9.5 · Spearman(model score, HMF) 0.7608 (N=8, descriptive only)
- mean latency 15322.5 ms · first-pass 8/8 · final 8/8 · retries 0

## Confusion (rows = GT, cols = pred)

| | Strong | Partial | Missing |
|---|---|---|---|
| **Strong** | 11 | 4 | 0 |
| **Partial** | 2 | 14 | 0 |
| **Missing** | 0 | 0 | 1 |

## Disagreements (all)

- 校招-AI产品经理（人才专项） — GT **Partial** / pred **Strong** — 参与AI产品从需求探索、方案设计、技术开发到上线迭代的完整流程，推动AI能力在保险场景中落地，而非停留在概念验证
- 校招-AI产品经理（人才专项） — GT **Partial** / pred **Strong** — 结合用户反馈和业务数据，持续优化AI应用效果，对核心指标(用户满意度、转化率、使用率)负责
- AI策略产品经理 — GT **Strong** / pred **Partial** — 负责抖音产品工作，独立跟进子项目的需求分析与规划，产品需求梳理
- AI策略产品经理 — GT **Strong** / pred **Partial** — 对业务有理解、能基于明确的业务场景或需求输出产品Demo或搭建AI应用等工作流，高效推动产品落地
- 平台AI产品经理 — GT **Strong** / pred **Partial** — 输出高质量的产品文档，协调设计、研发、QA资源，确保产品的高质量交付
- 产品经理 — GT **Strong** / pred **Partial** — 定期对行业相关产品进行评估，并提出功能优化、用户体验升级等方面建议

## Job-level Match Score vs GT vs HMF

| job | model score | GT repr-core score | |Δ| | HMF |
|---|---|---|---|---|
| 校招-AI产品经理（人才专项） | 75 | 50 | 25 | 3 |
| AI策略产品经理 | 75 | 100 | 25 | 5 |
| 平台AI产品经理 | 75 | 88 | 13 | 4 |
| 增长产品经理（平台经营） | 75 | 75 | 0 | 4 |
| AI产品经理 | 61 | 61 | 0 | 3 |
| 用户增长-用户运营管培生 | 38 | 38 | 0 | 2 |
| 产品经理 | 75 | 88 | 13 | 4 |
| 游戏AI产品经理（北京） | 75 | 75 | 0 | 4 |
