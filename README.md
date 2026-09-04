# JobPilot

> **Evidence-grounded AI Job Decision Assistant**

JobPilot 是一个基于候选人真实经历的岗位决策辅助工具。用户粘贴岗位链接或完整 JD 后，可以快速看懂岗位要求、逐项核对履历证据、获得可复算的 Match Score，并生成有安全边界的岗位专属简历。

它不是自动投递工具，也不替用户决定职业选择：**系统解释和建议，用户拥有事实并采取行动。**

## 问题

候选人在求职时往往需要反复完成同一组高认知负担任务：拆解冗长 JD、判断资格与能力匹配、寻找简历证据、针对岗位改写简历，再把岗位和投递状态维护在不同工具里。

普通 Job Tracker 只能记录状态；通用 LLM 又容易给出无法追溯的判断或虚构经历。JobPilot 将岗位理解、证据匹配、简历优化和申请管理连接成一个可审计工作流。

## 产品概览

当前一级导航只有：

- **岗位分析**：输入岗位 URL 或 JD，先预览完整分析；
- **我的岗位**：管理明确加入的岗位、状态、日期和后续动作；
- **求职档案**：维护 Master Resume、Experience Bank、求职身份与目标。

主流程保持明确的人机边界：分析预览不会自动创建岗位，Smart Nudge 不会自动改变状态，简历改写也不会覆盖 Master Resume。

## 核心工作流

```text
Candidate Profile + Job JD
            │
            ▼
      Structured Understanding
            │
            ├── Eligibility ──→ Supported / PotentialGap / Unknown
            ├── Knowledge   ──→ Preparation Topics（不评分）
            └── Matchable   ──→ Strong / Partial / Missing
                                      │
                                      ▼
                           Deterministic Match Score
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
               Resume Optimization         My Jobs / Tracking
                                                   │
                                                   ▼
                                          Deterministic Nudges
                                                   │
                                                   ▼
                                             User Action
```

## 核心能力

### 1. 岗位分析

- 支持粘贴完整 JD，或尝试读取公开岗位 URL；不支持的链接会明确提示用户粘贴 JD。
- 将岗位转换为概览、职责、资格、可匹配要求、知识准备主题与主观期待。
- Preview Analysis 默认不持久化；只有用户点击“加入我的岗位”才创建 Job。
- 满足一致性条件时，Preview Artifact 会直接提升为持久化分析，避免重复 matcher 调用和分数漂移。

### 2. Requirement Taxonomy V2

JobPilot 不再把所有 JD 句子都塞进同一套匹配逻辑：

| Requirement type | 含义 | 处理方式 | 进入 Match Score |
| --- | --- | --- | ---: |
| `eligibility` | 学历、毕业届别、明确年限、资格证、工作许可等门槛 | 确定性核验 | 否 |
| `matchable` | 可由履历验证的经验或能力 | Requirement Matcher | 是 |
| `knowledge` | 原理、机制、架构、能力边界等知识要求 | 准备主题 | 否 |

专业背景和学历层级独立判断。例如“人工智能 / 信息技术 / 软件工程”可以支持“计算机相关专业”，但不会据此推断未经验证的学历层级。

### 3. Evidence-grounded 匹配

- 对每条 `matchable` requirement 展示 **已匹配 / 部分匹配 / 暂无匹配证据**。
- Strong 与 Partial 必须引用允许的 evidence ID；后端会校验引用是否真实存在。
- 可用于高风险判断的候选人证据仅包括：
  - `resume_extracted`：从当前 Master Resume 提取；
  - `manual_confirmed`：由用户明确确认。
- `manual_unconfirmed`、未知来源和推测事实不能支持强匹配或简历 claim。

> “暂无匹配证据”只表示当前没有足够的已验证证据，不表示候选人一定不具备该能力。

### 4. 确定性 Match Score

LLM 只负责 requirement 与 evidence 的语义匹配，不直接给最终分数。后端按固定规则计算：

```text
Importance: Critical = 5 · Important = 3 · Preferred = 1
Match:      Strong = 1.0 · Partial = 0.5 · Missing = 0

Match Score = round_half_up(
  100 × Σ(importance weight × match multiplier) / Σ(importance weight)
)
```

分子和分母都只包含 `matchable` requirements；Eligibility 和 Knowledge 不会以“0 分要求”的形式稀释结果。若岗位没有可评分要求，系统显示 score unavailable，而不是错误地显示 0 分。

### 5. 岗位专属简历优化

```text
Validated Match Analysis
→ Deterministic Evidence Selection
→ 简历优化方案
→ User Confirmation
→ Batch Rewrite
→ Deterministic Guardrails
→ Batch Semantic Validation
→ Validated Draft / Original Fallback
```

- 每个 Job 保存独立的岗位简历 artifact；Master Resume 永不被覆盖。
- 改写只能使用 allowlisted evidence，不允许新增技能、数字、实体、ownership 或工作成果。
- Knowledge 与 Eligibility 不会被包装成履历 claim。
- 验证失败的 bullet 回退原文，不通过额外 critic loop 冒险放行。

### 6. My Jobs 与申请跟踪

- 支持手动添加任意渠道的岗位，或从分析预览显式加入。
- 支持默认及自定义申请状态、状态排序和安全迁移。
- 保存投递日期、面试日期、下一阶段与备注。
- 展示 Match Score、分析 freshness 和岗位简历状态。
- 重复加入保持幂等，不会创建重复岗位。

### 7. Smart Nudges

Smart Nudges 是当前产品中的行动建议层，但它**不是 LLM Agent**：

- 根据 `high_volume / focused / balanced / interview_first` 求职策略读取当前岗位状态；
- 关注临近面试、待确认资格、高匹配岗位停滞、待投递积压等可解释信号；
- 完全确定性、零 LLM、只读、最多返回 3 条；
- 不持久化建议，不自动投递，不修改岗位状态，也不创建用户任务；
- CTA 只把用户带到相应岗位或分析页面，最终行动始终由用户完成。

## AI 与确定性架构

JobPilot 使用**任务级模型服务 + 确定性领域服务**，不是 Multi-Agent 系统。

```text
Raw JD
  └─ Claude structured parsing
        ↓
Structured Requirement Taxonomy
  ├─ EligibilityService             deterministic
  ├─ Knowledge preparation          deterministic projection
  └─ RequirementMatcher             qwen3.8-max + Prompt C
        ↓
Evidence validation + normalization deterministic
        ↓
Match Score                         deterministic
        ↓
Resume tailoring                    task-specific generation + validation
        ↓
Smart Nudges                        deterministic, zero LLM
```

冻结的生产 Requirement Matcher：

| Setting | Production value |
| --- | --- |
| Provider | Alibaba DashScope |
| Model | `qwen3.8-max` |
| Prompt | `job-fit-v3-rubric-refined-v2`（Prompt C） |
| Temperature | `0` |
| Thinking trace | disabled |
| Output | structured requirement-level matches |

未单独评测迁移的语义任务继续使用现有 Claude structured-output 服务，例如 JD parsing 与简历生成/验证。模型不会绕过 evidence allowlist、后端归一化或确定性评分。

## 评估方法与关键结果

Job Analysis Evaluation 已完成并关闭。评估把开发集、真实 held-out 和合成压力测试严格分开：

- **Dataset V1（开发集）**：30 个真实岗位、158 条 canonical requirements，其中 100 条 `matchable` requirements 有人工 Ground Truth；用于 baseline、模型选择和 Prompt A→B→C 迭代。
- **V2-Real（held-out）**：8 个代表性真实岗位、32 条 core matchable requirements；用于小样本泛化检查。
- **V2-Synthetic（压力测试）**：50 个合成岗位、65 条 probe requirements；其中 Strong/Partial/Missing 的人工复核 subset 为 20 条，用于测试已知决策边界。

核心指标包括 Macro F1、Effective Correct Coverage（ECC）、Grounding、Unsupported Match、Match Score MAE、HMF Spearman、延迟和首次调用成功率。

| Evaluation | Qwen3.8-Max + Prompt C | Comparator / context |
| --- | ---: | --- |
| V1 development Macro F1 | **0.786** | Claude baseline 0.692 |
| V1 development ECC | **0.780** | Claude baseline 0.620 |
| V2-Real Macro F1 | **0.8697** | Kimi K3 + Control 0.8920 |
| V2-Real ECC / Accuracy | **0.8125** | Kimi 0.8438 |
| V2-Real Grounding / Unsupported | **1.00 / 0.00** | Kimi 1.00 / 0.00 |
| V2-Real mean / p95 latency | **15.3 s / 17.8 s** | Kimi 34.1 s / 58.8 s |
| V2-Real first-pass success | **8 / 8** | Kimi 7 / 8，retry 后恢复 |
| Human-reviewed synthetic probe Macro F1 | **0.903** | Kimi 0.836 |
| Technology-adjacency accuracy | **1.00** | Kimi 0.33 |

这些数字必须结合样本量理解：在当前 8 个岗位 / 32 条 requirement 的样本规模下，结果不足以支持两模型存在明确真实差异，因此本轮将其解释为实质接近，而非证明两模型客观等价。Prompt C 的主要证据是对 technology adjacency failure mode 的鲁棒性，而非普遍的真实世界准确率跃升。

完整方法、误差分析与限制见 [Job Analysis Evaluation Case Study](backend/evals/job_analysis_evaluation_final_summary.md)。

## 生产模型决策

最终选择 `qwen3.8-max + Prompt C`，依据是组合产品权衡：

1. 在小规模真实 held-out 上与 finalist 基本持平；
2. 在人工复核的 adjacency 压力测试上更稳健；
3. V2-Real 平均延迟约低 **2.2×**；
4. 首次调用可靠性更好，且结构化输出最终全部成功；
5. Prompt C 只保留经 error slice 验证有价值的规则，没有继续堆叠脆弱指令。

仓库没有可核验的最新官方单价，因此不编造美元成本。冻结分析只报告实际 token/cache 使用和参数化成本框架。

## 技术栈

| Layer | Technology |
| --- | --- |
| Frontend | React · TypeScript · Vite · React Router |
| Backend | FastAPI · Python · Pydantic |
| Database | PostgreSQL · SQLAlchemy · Alembic |
| Requirement Matcher | DashScope · `qwen3.8-max` |
| Other semantic services | Claude structured output |
| Verification | pytest · Vitest · Ruff · ESLint · TypeScript |

## 截图与 Demo

<!-- TODO(portfolio): add privacy-safe screenshots for 岗位分析、匹配分析、简历优化、我的岗位、求职档案. -->

仓库当前没有可公开引用的脱敏截图，因此这里不使用虚假文件名或本地路径。运行项目后可访问：

- `/` 或 `/analyze`：岗位分析
- `/my-jobs`：我的岗位与 Smart Nudges
- `/profile`：求职档案
- `/jobs/:id`：岗位要求、匹配分析与简历优化

## 本地运行

Prerequisites：Python 3.11+、Node.js 20+、Docker Desktop（或可用的 PostgreSQL）。

```bash
git clone https://github.com/Yulia-qinyu/JobPilot.git
cd JobPilot
cp .env.example .env
docker compose up -d postgres
```

若要复现冻结的生产模型配置，在 `.env` 中设置：

```dotenv
MATCHER_PROVIDER=qwen
MATCHER_MODEL=qwen3.8-max
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# JD parsing、简历生成与验证等现有 Claude 服务
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

启动后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

启动前端：

```bash
cd frontend
npm install
npm run dev
```

- 产品地址：`http://localhost:5173`
- OpenAPI：`http://localhost:8000/docs`

不要提交真实 API key；`.env` 已被 `.gitignore` 排除。

## 验证

```bash
# backend
cd backend
source .venv/bin/activate
pytest
ruff check app tests

# frontend
cd ../frontend
npm test -- --run
npm run lint
npm run typecheck
npm run build
```

Feature-freeze close-out 的最近一次验证结果：backend **278 passed**；frontend **57 passed**；相关 Ruff、ESLint、TypeScript、production build 与 `git diff --check` 均通过。

## 项目状态

**Feature frozen.** Job Analysis Evaluation 已完成并关闭，生产 matcher 已固定为 Qwen3.8-Max + Prompt C。

- Standalone Planning / Daily Planning Agent 已退出 active product flow；`/plan` 只保留安全跳转兼容。
- Discovery 基础设施与 `/discover` compatibility route 仍保留，但不是一级入口，也不是产品核心定位。
- 后续不计划扩展新功能；只有 blocker bug fix 才应重新打开产品代码。

## 限制与范围

- 当前是单用户、本地 portfolio architecture，没有 authentication 或多用户 ownership。
- 评估规模有限，尤其 V2-Real 只有 8 个岗位；结果不能解释为生产级 benchmark。
- Source Catalog 有意保持有限；JobPilot 不承诺全网岗位覆盖。
- 不执行自动投递、招聘网站登录、CAPTCHA 绕过或通用 browser agent。
- 每个 Job 当前只维护一个 current tailored resume artifact，没有完整版本历史 UI。
- 没有 production durable queue、SaaS tenancy、通知或日历集成。
- Smart Nudges 是确定性启发式建议，不是对用户现实行为的自动化控制。

---

**JobPilot 的核心承诺：AI 可以加速理解和准备，但事实、判断与行动始终属于用户。**
