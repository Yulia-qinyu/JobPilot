# Lightweight Importance Calibration — Reference Set (8 cases)

A small human-calibrated Importance reference set. **Not** exhaustive adjudication; all other Dataset V1 Importance labels remain `importance_not_explicitly_human_verified`. Do not extrapolate these 8 labels to other requirements. Baseline: `dataset_v1_corrected_evaluation_view.json`.

- Cases reviewed: **8**
- Distribution: **Critical 5 / Important 0 / Preferred 3**
- **accepted 3** (draft == human) · **edited 5** (draft != human; all Important → Critical)

| # | requirement_id | job | requirement_text | draft → human | status | uncertain |
|---|---|---|---|---|---|---|
| 1 | `reqv2_db1d8efa4071bf5f` | 微信-语音识别算法工程师 | 流式语音识别模型研发经验（模型训练 / 流式解码 / 延迟优化） | Important → **Critical** | edited | false |
| 2 | `reqv2_7c4b6a0fd084f77d` | AI产品经理 | 开发者工具、研发效能或平台型产品经验 | Preferred (unchanged) | accepted | false |
| 3 | `reqv2_7c8882c717660066` | AI产品经理 | 独立完成需求分析、产品设计、项目推进与数据迭代 | Important → **Critical** | edited | false |
| 4 | `reqv2_c5c5a841f5fb83b6` | AI产品经理（J84006） | 多模态大模型应用 / AIGC / 社交娱乐类产品经验 | Preferred (unchanged) | accepted | false |
| 5 | `reqv2_5685d10f28aca7c2` | 腾讯会议-AI产品经理-ASR方向 | 熟悉语音交互相关技术（ASR / 语义理解 / TTS） | Important → **Critical** | edited | false |
| 6 | `reqv2_cd8c089c6f3c4688` | 腾讯视频-增长产品经理 | 通过 AB 实验驱动产品迭代 | Important → **Critical** | edited | false |
| 7 | `reqv2_f2105cecb6db9371` | 光子 AI-数据平台产品经理 | B 端 / 数据 / AI / 研发效能平台或企业内部系统产品经验 | Preferred (unchanged) | accepted | false |
| 8 | `reqv2_91500289fe78e7b4` | 大数据产品经理（深圳/北京） | 数据开发 / 分析 / SQL / 指标体系 / 元数据 / 数据血缘 / 数据质量 | Important → **Critical** | edited | false |

## Lightweight impact (apply ONLY these 8 decisions on the corrected view)

Match Score formula unchanged. **Not** a fully human-verified GT Match Score.

| job | cases | importance edits | GT score before | GT score after | Δ |
|---|---|---|---|---|---|
| 微信-语音识别算法工程师 | 1 | 1 | 25 | 17 | -8 |
| AI产品经理 | 2,3 | 1 | 75 | 83 | +8 |
| AI产品经理（J84006） | 4 | 0 | 50 | 50 | +0 |
| 腾讯会议-AI产品经理-ASR方向 | 5 | 1 | 25 | 19 | -6 |
| 腾讯视频-增长产品经理 | 6 | 1 | 77 | 67 | -10 |
| 光子 AI-数据平台产品经理 | 7 | 0 | 88 | 88 | +0 |
| 大数据产品经理（深圳/北京） | 8 | 1 | 83 | 77 | -6 |

Distinct jobs touched: 7; jobs with a score delta: 5 (the 3 accepted-as-Preferred cases change no score).
