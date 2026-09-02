# Dataset V1 Importance → Match Score Sensitivity

Deterministic. GT Match Score per job = round_half_up(100 * Σ(weight·statusMult) / Σweight) over matchable requirements. weight {Critical:5, Important:3, Preferred:1}; statusMult {Strong:1.0, Partial:0.5, Missing:0.0}. For each matchable requirement, recompute the job score with only that requirement's importance changed and report the delta. NOT a re-labeling; only to rank human-audit priority. Match Score weights unchanged.

**0 matchable requirements are Critical**, so the scoring-relevant mislabel risk is Important ↔ Preferred.

## Top high-sensitivity matchable requirements (Important↔Preferred single-flip Δ to job GT score)

| job | req (norm) | importance | GT label | #matchable | base score | Δ I↔P | Δ→Critical |
|---|---|---|---|---|---|---|---|
| 微信-语音识别算法工程师 | 流式语音识别模型研发经验（模型训练 / 流式解码 / 延迟优化） | Important | Missing | 3 | 40 | +27.0 | -11.0 |
| AI产品经理 | 开发者工具、研发效能或平台型产品经验 | Preferred | Missing | 2 | 75 | -25.0 | -37.0 |
| AI产品经理（J84006） | 计算机或人工智能相关专业 | Preferred | Strong | 2 | 50 | +25.0 | +33.0 |
| AI产品经理（J84006） | 多模态大模型应用 / AIGC / 社交娱乐类产品经验 | Preferred | Missing | 2 | 50 | -25.0 | -33.0 |
| AI产品经理 | 独立完成需求分析、产品设计、项目推进与数据迭代 | Important | Strong | 2 | 75 | -25.0 | +8.0 |
| AI产品经理（J84492） | 语音交互大模型方向工作或科研经历 | Preferred | Missing | 3 | 80 | -23.0 | -36.0 |
| 腾讯云-经营系统产品经理 | 沟通协调与跨团队沟通能力 | Important | Strong | 3 | 43 | -23.0 | +13.0 |
| 微信-语音识别算法工程师 | 计算机 / 人工智能 / 语音信号处理相关专业 | Preferred | Strong | 3 | 40 | +17.0 | +27.0 |
| 微信-语音识别算法工程师 | 硕士及以上学历 | Preferred | Strong | 3 | 40 | +17.0 | +27.0 |
| 腾讯云-经营系统产品经理 | 熟悉企业经营管理流程 | Important | Missing | 3 | 43 | +17.0 | -10.0 |
| 腾讯会议-AI产品经理-ASR方向 | 熟悉语音交互相关技术（ASR / 语义理解 / TTS） | Important | Missing | 3 | 50 | +14.0 | -9.0 |
| 腾讯会议-AI产品经理-ASR方向 | 用户感知力与问题发现解决能力 | Important | Strong | 3 | 50 | -14.0 | +9.0 |
| 腾讯视频-增长产品经理 | 通过 AB 实验驱动产品迭代 | Important | Missing | 5 | 77 | +14.0 | -10.0 |
| 光子 AI-数据平台产品经理 | B 端 / 数据 / AI / 研发效能平台或企业内部系统产品经验 | Preferred | Partial | 2 | 88 | -13.0 | -19.0 |
| AI产品经理（J84492） | 洞察与规律总结能力 | Important | Strong | 3 | 80 | -13.0 | +6.0 |
| 光子 AI-数据平台产品经理 | 结构化思维：将复杂业务拆解为产品模块 / 数据流程 / 权限 | Important | Strong | 2 | 88 | -13.0 | +4.0 |
| 腾讯会议-评测产品经理 | AI / 策略 / 评测产品相关经验 | Important | Partial | 3 | 70 | +13.0 | -6.0 |
| AI-First Engineering Intern | already uses AI tooling to build/ship faster | Important | Partial | 2 | 75 | +13.0 | -6.0 |
| AI-First Engineering Intern | side projects / self-shipped personal projects | Important | Strong | 2 | 75 | -12.0 | +6.0 |
| AI产品经理（J98328） | 一年以上产品工作经验 | Preferred | Partial | 3 | 90 | -11.0 | -18.0 |

## Top jobs by worst-case single Important↔Preferred flip

| job | #matchable | baseline GT score | worst single-flip Δ |
|---|---|---|---|
| 微信-语音识别算法工程师 | 3 | 40 | 27.0 |
| AI产品经理（J84006） | 2 | 50 | 25.0 |
| AI产品经理 | 2 | 75 | 25.0 |
| AI产品经理（J84492） | 3 | 80 | 23.0 |
| 腾讯云-经营系统产品经理 | 3 | 43 | 23.0 |
| 腾讯会议-AI产品经理-ASR方向 | 3 | 50 | 14.0 |
| 腾讯视频-增长产品经理 | 5 | 77 | 14.0 |
| 光子 AI-数据平台产品经理 | 2 | 88 | 13.0 |
| 腾讯会议-评测产品经理 | 3 | 70 | 13.0 |
| AI-First Engineering Intern | 2 | 75 | 13.0 |
| AI产品经理（J98328） | 3 | 90 | 11.0 |
| 大模型应用平台产品经理（J85776） | 3 | 71 | 11.0 |
