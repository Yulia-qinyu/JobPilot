# JobPilot — Job Analysis & Application Workspace

JobPilot 是一个基于候选人真实经历的 AI 求职匹配与简历优化工作台。用户粘贴岗位链接或完整 JD 后，可以看懂岗位要求、逐项查看匹配证据、获得确定性 Match Score，并继续生成可追溯、可验证的针对性简历草稿。

核心链路：`Job URL / JD → Job Understanding → Requirement-level Match → Resume Optimization → My Jobs → Application Tracking`。JobPilot 帮助用户理解和准备，不替用户决定是否投递。

Phase 7 将岗位体验明确拆成 **Discover** 与 **My Jobs**：Discover 是 60 分钟 TTL 的临时招聘市场探索空间；只有用户明确点击 `Add to My Jobs` 后，岗位才会进入 PostgreSQL，并继续使用现有 Match、Decision、Tailoring 与 Application Tracker。Discover 使用 generalized ephemeral Search Intent，独立表达 location、company、job function、role family、industry、domain、recruitment type 与未知 freeform concepts；它不再受 Candidate Target Role taxonomy 限制。简单 query 为 0 Claude calls，语义覆盖不足时最多使用 1 次 bounded structured planner call。SourcePlan 由 CompanySourceResolver 和 Source Catalog 确定性生成；当前默认仅启用 ByteDance 国内岗位源，Greenhouse adapter 与测试保留但不参与默认路由。获取、排名、解释、个性化和 Add 均不调用 Claude，也不会自动运行 Phase 3。

Phase 4 的正式定位是 **Job Discovery & Batch Import**：让用户低成本、可靠地把受支持招聘网站的候选岗位带入 JobPilot。ByteDance 是第一个 `JobSourceAdapter`，不是产品本身；本阶段只负责 `Discover → Normalize → Persist`，不做筛选、排名或申请建议。

Phase 5 的正式定位是 **Job Decision**：通过确定性的岗位方向分类、保守资格判断和 Target Role Fit，将大岗位池缩小为“值得分析 / 低优先级 / 排除”。只有用户主动运行 Phase 3 Deep Match 后，系统才会基于有效分析确定性地产生“优先投递 / 建议投递 / 可以考虑 / 跳过”。Phase 5 自动预筛选不调用 Claude。

Target Role 遵循明确的责任边界：`Career priority = explicit user intent`，`Role family = system classification with human override`。用户只需填写岗位名称并选择 Primary / Secondary / Exploratory；系统复用确定性 RoleClassifier 生成标准岗位方向，用户可按需修正或清除修正。

Phase 6 的正式定位是 **Evidence-Grounded Resume Tailoring**。有效且未过期的 Phase 3 requirement/evidence mapping 是强制前置条件。系统先以确定性逻辑生成 Tailoring Plan，用户确认后才进行一次批量生成和一次批量语义验证。所有改写必须引用 allowlisted evidence；数字、技能、实体与 ownership 升级还会经过确定性 guardrails。任何验证失败的改写默认回退原文，Master Resume 永远不会被覆盖。

Phase 6.1 是 Tailoring Quality 与 Validator Precision 的小范围修正，不改变 Phase 6 的安全架构或正常调用数。长证据会形成只读的 derived claim segments，经历 title / organization / project / dates 作为受限 context metadata 单独传递；metadata 可以原样或等义复述，但不能推导新的责任、领导力、范围或结果。生成器可以明确选择 `Keep`，格式或标点层面的伪改写会被后端确定性降级为 Keep。语义验证只检查候选 bullet 中实际出现的 claim 是否得到证据支持，允许为聚焦 JD 而省略未使用的证据信息。

## 当前能力

- 持久化单个本地用户的主简历、结构化 Resume Profile、经历事实库、目标公司、目标岗位和目标城市。
- 岗位分析是默认首页；一级导航为“岗位分析 / 我的岗位 / 求职档案”。Dashboard backend statistics 与 Phase 7 Discover architecture 保留，但都不再作为一级入口。
- 首页支持岗位 URL 或完整 JD 的非持久化分析；只有用户明确点击“加入我的岗位”才创建 persistent Job。
- 独立 Discover 页面：自然语言或 ByteDance search URL → ephemeral session → temporary results。
- Generalized Search Intent 保留 typed explicit concepts；已知概念确定性标准化，未知概念以 session-local freeform evidence 保留。
- Required clarification 只解决最高影响的缺失维度；optional refinement 可由 catalog 或同一次 semantic planner call 动态产生，最多两层且不阻塞搜索。
- Source Catalog 当前默认启用 ByteDance；Greenhouse sources 标记为 disabled，adapter、fixtures 与显式启用测试路径仍保留。
- 无 company constraint 时搜索所有 eligible enabled domestic sources；显式 company constraint 产生 full / partial / unsupported coverage，不静默忽略未支持公司。
- Discover 结果支持城市、公司、岗位方向、相关度和 My Jobs 状态筛选；Why this job 完全由当前搜索条件确定性生成。
- 个性化默认关闭；开启后仅用 verified Candidate Evidence 在当前搜索相关度边界内重排和解释，不改变 Search Intent 或 source routing。
- 独立 My Jobs 语义：只包含用户明确加入的 persistent Job workspace。
- 保留原有单岗位 URL / 粘贴 JD → Claude structured parsing → 用户确认流程。
- 从 ByteDance 社招或校招搜索结果 URL 批量发现岗位。
- 通过官方前端 JSON search endpoint 分页读取，无 Playwright、无逐岗位 detail 请求。
- 将 source 数据确定性标准化为 source-neutral DTO 和 JobPilot Job；导入默认 Claude 调用数为 0。
- 按 `(user_profile_id, source, external_job_id)` 幂等新增、识别重复、更新来源字段。
- 持久化 Import Session 进度，允许单岗位失败而保留其他成功岗位。
- 用户明确触发时，使用 Phase 3 的一次 Claude requirement matching，并由后端确定性计算分数和推荐。
- 基于 Phase 3 已验证 evidence 生成确定性 Tailoring Plan，Plan 与页面读取均不调用 Claude。
- 用户确认 Plan 后以 1 次 structured generation + 1 次 batch semantic validation 生成草稿。
- Phase 6.1 区分 Meaningful Rewrite、Model Keep、Formatting-only Keep 与 Fallback，不用文字变化幅度冒充 tailoring 价值。
- 长 Experience Fact 仅在 tailoring runtime 形成稳定、可追溯的 derived segments；不会写回 Experience Bank 或改变 Phase 3。
- 支持 Before/After、查看依据、编辑、保留原文、主动验证与显式接受；未验证或过期草稿不可接受。

## Architecture

Phase 7 Workspace boundary：

```text
Natural query / supported careers URL
→ deterministic extraction + semantic coverage check
→ optional max 1 bounded Claude semantic planner
→ generalized Search Intent + dynamic bounded refinement
→ CompanySourceResolver + deterministic SourcePlan
→ SourceRouter + verified Source Catalog
→ ByteDanceJobSource / GreenhouseJobSource
→ deterministic normalization
→ InMemoryDiscoverySessionStore (TTL 60 min, max 500 results)
→ temporary filters / Why this job
→ explicit Add to My Jobs
→ WorkspaceJobUpsertService
→ PostgreSQL Job + deterministic Phase 5 recompute
```

`Search alone != Job persistence`。Legacy `/api/job-imports` 继续保留“明确全量导入”的 Phase 4 contract，但内部与 Discover 共享 acquisition 和 workspace upsert；Discovery 不调用 legacy import service。Greenhouse identity 仍使用 namespaced source（例如 `greenhouse:scaleai`）加 external job ID，供 adapter regression 和未来显式重新启用时使用。

Phase 5 Decision Funnel：

```text
Persisted Job
→ Deterministic RoleClassifier
→ Conservative EligibilityService
→ TargetRoleFitService
→ Pre-Match Decision
→ user-triggered Phase 3 Match (optional)
→ Deterministic Final Decision
→ persisted JobDecision
```

`JobDecision` 分开保存 auto、manual override 和 effective 值；重新计算不会覆盖用户修正。候选人档案、目标岗位、岗位输入和 Phase 3 分析分别使用 canonical hash 跟踪 freshness。Job Pool 使用服务端 pagination/filter/sort，漏斗数字由 PostgreSQL aggregate 计算。

Phase 5 不新增 Candidate Relevance Score、Priority Score 或第二套 Match Score；也不自动或批量触发 Phase 3。

Phase 6 Tailoring 链路：

```text
Valid Phase 3 Analysis
→ deterministic evidence selection
→ deterministic segmentation + Tailoring Plan (0 Claude calls)
→ user confirmation
→ one batch Claude generation (Rewrite or Keep)
→ reference + deterministic claim validation
→ one batch one-way claim-entailment validation
→ deterministic draft assembly with original fallback
→ user review/edit/accept
```

生成模型只负责措辞、重点与精炼表达。证据选择、引用授权、数字/技能/实体/ownership 安全检查、fallback、最终组装与接受资格均由后端控制。

语义验证的方向是 `candidate claims → allowed evidence/context support`。省略证据中的次要信息不构成 safety failure；validator 返回的 unsupported span 必须是 candidate bullet 中实际存在的原文片段，否则按 protocol violation 安全回退。生成与验证仍各为一次 batch call，不存在 per-bullet call、第三次 critic 或自动 retry loop。

```text
ByteDance Search URL
  → POST /api/job-imports (202)
  → in-process background runner
  → JobImportService
  → JobSourceRegistry
  → ByteDanceJobSource
  → official public JSON search API
  → source-neutral SourceJobRecord
  → deterministic normalization
  → idempotent Job upsert
  → PostgreSQL Job Pool
```

来源获取与 JobPilot 领域逻辑分离。未来新增官方招聘源时，实现新的 adapter 并注册即可，不需要把 source-specific 代码放进 `JobImportService`。

`original_jd` 是忠实组合的 source evidence：

```text
职位描述
{source description}

职位要求
{source requirement}
```

`structured_jd` 是 derived normalized representation。Phase 4 仅做列表切分、明确加分项识别和 source metadata 映射，不推断 `Critical / Important / Preferred`；Phase 3 Requirement Catalog 继续拥有 requirement-level interpretation responsibility。

当前使用 in-process 单 worker runner，因为产品是 single-user portfolio application。导入领域逻辑与执行设施已经隔离；未来可用 durable queue 替换 runner，而无需修改 source adapters 或 upsert 规则。后台任务总是创建自己的数据库 Session，不复用 request-scoped Session。

## Database

现有表：

- `user_profiles`, `resumes`, `experiences`, `experience_facts`
- `target_companies`, `target_roles`
- `jobs`, `job_analyses`
- `resume_tailorings`（每个 Job 一个 active tailoring derived artifact）

Phase 4 扩展 `jobs`：

- `source`, `external_job_id`, `external_job_code`
- `source_metadata`, `last_seen_at`
- unique constraint: `(user_profile_id, source, external_job_id)`

手工岗位继续使用 `source = NULL`, `external_job_id = NULL`，不受唯一约束影响。

新增 `job_import_sessions`，保存 search URL/hash、source、status/stage、discovered/processed/imported/updated/duplicate/failed counts、批次岗位 ID、受限的失败代码以及时间戳。没有引入逐岗位 ImportItem 表。

Phase 6 新增 `resume_tailorings`，保存 source Resume、deterministic Plan、generated/user-edited draft、validation results、canonical freshness hashes、模型/schema/guardrail 版本和安全 token/latency metadata。它不会修改 `Resume.extracted_text`、`Resume.structured_profile` 或 Experience Bank。

Phase 6.1 不新增数据库表或 migration。Plan、generator、validator 与 guardrail 使用 v2 version marker；旧 active tailoring 会显示为 engine-outdated/stale，用户可查看但必须主动刷新 Plan/Draft，系统不会后台重新生成。

重新发现来源岗位时：相同 hash 仅更新 `last_seen_at`；不同 hash 更新 source-owned fields 并清空 Job 上的 cached match summary。Application Tracker 字段不会被覆盖，旧 `JobAnalysis` 不删除，并由 Phase 3 的 JD hash 机制显示为 stale。

## Project structure

```text
JobPilot/
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── alembic/versions/
│   ├── app/
│   │   ├── db/
│   │   ├── repositories/
│   │   ├── routes/
│   │   ├── schemas/
│   │   └── services/
│   │       └── job_sources/
│   │           ├── base.py       # source-neutral contracts
│   │           ├── registry.py
│   │           └── bytedance.py  # first adapter
│   └── tests/
└── frontend/src/
    ├── AddJobPage.tsx
    ├── JobImportPanel.tsx
    ├── JobsPage.tsx
    └── ...
```

## Local setup

Prerequisites: Python 3.11+, Node.js 20+, Docker Desktop 或 PostgreSQL 15+。单岗位 Resume/JD parsing 与 Phase 3 分析需要 Anthropic API key；Phase 4 批量导入不需要 Claude。

```bash
cp .env.example .env
docker compose up -d postgres

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m scripts.recompute_target_roles
python -m scripts.recompute_job_decisions
uvicorn app.main:app --reload --port 8000
```

新终端：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173` 会直接进入“分析一个岗位”。兼容的 `/discover` route 仍然保留。

仅在本地开发环境重置 My Jobs（保留 Profile、Resume、Experience Bank、Target Roles）：

```bash
cd /Users/yulia/Documents/JobPilot/backend
JOBPILOT_ENVIRONMENT=development .venv/bin/python -m scripts.reset_job_workspace
JOBPILOT_ENVIRONMENT=development .venv/bin/python -m scripts.reset_job_workspace --confirm
```

第一条命令只预览计数；第二条必须显式 `--confirm` 才会在单事务中删除 Job、Decision、Analysis、Tailoring 与 legacy Import Session。脚本拒绝 production environment 和非本机数据库。

Xiaomi / Feishu Recruitment HTTP-only contract diagnostic：

```bash
cd /Users/yulia/Documents/JobPilot/backend
.venv/bin/python -m scripts.spike_xiaomi_feishu_recruitment
```

该脚本不是 source adapter，不会注册进 Discover；不登录、不执行浏览器自动化、不访问申请接口，也不绕过前端 `_signature` 风控。

## Environment variables

| Variable | Default/example | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://jobpilot:jobpilot@localhost:5433/jobpilot` | PostgreSQL |
| `ANTHROPIC_API_KEY` | — | 单岗位解析及主动匹配分析 |
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Claude structured-output model |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | CORS |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend API URL |
| `JOB_IMPORT_PAGE_SIZE` | `100` | Search API page size |
| `JOB_IMPORT_MAX_JOBS` | `2000` | Per-session result cap |
| `JOB_IMPORT_MAX_PAGES` | `50` | Pagination safety cap |
| `JOB_IMPORT_TIMEOUT_SECONDS` | `20` | Upstream request timeout |
| `JOB_IMPORT_MAX_RESPONSE_BYTES` | `5242880` | Per-page response cap |
| `JOB_IMPORT_PAGE_DELAY_SECONDS` | `0.35` | Polite delay between pages |
| `JOB_IMPORT_MAX_RETRIES` | `3` | 429/5xx/network retry cap |

`.env` 与 frontend local environment files 已被 `.gitignore` 保护。不要提交真实 API key。

## API

Batch import：

- `POST /api/job-imports` → `202 Accepted` + persisted queued session
- `GET /api/job-imports/{session_id}` → progress / terminal result
- `GET /api/job-imports/{session_id}/jobs` → 本批新增、更新或已存在岗位

现有 `GET/POST/PATCH /api/jobs...`、Profile、Dashboard、Phase 3 Job Analysis，以及 legacy `POST /api/analyze` 均保留。

Resume Tailoring：

- `GET /api/jobs/{job_id}/resume-tailoring`
- `POST /api/jobs/{job_id}/resume-tailoring/plan`
- `PATCH /api/jobs/{job_id}/resume-tailoring/plan`
- `POST /api/jobs/{job_id}/resume-tailoring/draft`
- `PATCH /api/jobs/{job_id}/resume-tailoring/draft`
- `POST /api/jobs/{job_id}/resume-tailoring/validate`
- `POST /api/jobs/{job_id}/resume-tailoring/accept`

Discovery：

- `POST /api/discovery/sessions`
- `PATCH /api/discovery/sessions/{session_id}/context`
- `POST /api/discovery/sessions/{session_id}/search`
- `GET /api/discovery/sessions/{session_id}`
- `GET /api/discovery/sessions/{session_id}/results`
- `POST /api/discovery/sessions/{session_id}/results/{result_id}/my-job`

Discovery sessions 只存在于单个 backend process 内存。未知 session 返回 404，已过期/被容量淘汰的 session 返回 `410 DISCOVERY_SESSION_EXPIRED`。

未运行或已过期的 Phase 3 分析分别返回安全的 `409 ANALYSIS_REQUIRED` / `409 ANALYSIS_STALE`；过期 tailoring 不可 Accept。服务不会在这些操作中自动运行 Phase 3。

## Safety and upstream behavior

- ByteDance 只接受 exact HTTPS host `jobs.bytedance.com` 的 `/experienced/position` 或 `/campus/position`。
- Greenhouse 只接受 verified catalog tenant 的 `job-boards.greenhouse.io` / `boards.greenhouse.io` URL；API 获取固定使用 public `boards-api.greenhouse.io` endpoint。
- 使用 `httpx` connection reuse、20 秒 timeout、5 MB page cap、100/page、低请求频率。
- 只重试 429、有限的 5xx 和 network errors；确定性 4xx 快速失败。
- 不使用 cookies，不绕过登录/CAPTCHA/访问控制，不记录响应正文或完整 JD。
- 结果超过 2,000 或 pagination safety cap 时明确失败，并要求用户先在官网缩小筛选范围，不静默截断。
- CI 使用 sanitized fixtures 与 `httpx.MockTransport`，不访问 live website。

显式 live smoke（会把结果写入当前 `DATABASE_URL`，默认不在 CI 运行）：

```bash
cd backend
source .venv/bin/activate
python -m scripts.smoke_bytedance_import \
  'https://jobs.bytedance.com/experienced/position?keywords=AI%20Product%20Manager&location=CT_11'
```

## Verification

```bash
cd backend
source .venv/bin/activate
pytest
ruff check app tests alembic scripts

cd ../frontend
npm test -- --run
npm run lint
npm run typecheck
npm run build
```

## Known limitations

- 单用户、本地 portfolio 部署，无 authentication。
- in-process background task 不是 durable queue；进程重启会中断 Running/Queued session，需要用户重新提交。
- 当前 Source Catalog 是明确 allowlist，不代表全网搜索；未支持招聘站会提示改用单岗位链接或 JD。
- Import Session 保留最多 50 条脱敏失败明细，没有 per-item retry UI、cancel 或 scheduled monitoring。
- Phase 4 不生成 AI JD Quick Overview；导入岗位的 overview 只使用可安全确定的 source-derived 内容。
- Phase 5 的 Role Classification 和 Eligibility 是保守的 deterministic rules；模糊信息保留为 `general_product` / `unknown` / `PossiblyEligible`，不会借助 LLM 猜测。
- Migration 后旧 Target Role 的 priority 原样保留；role family 由确定性分类器回填。无法可靠识别的岗位保留为 `unknown` 并在「求职档案」提示用户确认，系统不会替用户决定求职优先级。
- Phase 5 当前不支持 bulk Match。Deep Match 仍由用户逐岗位主动触发。
- 本地 single-user 部署可用 `python -m scripts.recompute_job_decisions` 回填或刷新最多 2,000 个岗位；生产级任务队列仍属未来扩展。
- Phase 6 是内容级 structured draft，不包含 DOCX/PDF export、视觉模板编辑器或完整版本历史。
- Derived evidence segmentation 是确定性的 punctuation/sentence-boundary view，不是新的 Candidate Fact；复杂或没有明确断句的长事实仍可能保持较粗粒度。
- 确定性 entity/ownership guardrails 有意保守；边界表达可能回退原文并等待人工编辑，而不会冒险放行。
- Phase 6.1 的 Human Preference 与 validator false-positive rate 必须由人工填写 `backend/evals/phase6_1_human_evaluation.md` 后评定；自动 safety 指标不能代替产品验收。
- Phase 7A/7B Discovery session 在进程重启后丢失，不支持多 worker、Redis 或 durable recovery；已加入 My Jobs 的岗位不受影响。
- 个性化关闭时 Candidate context provider 调用数为 0；开启时只使用 `resume_extracted` / `manual_confirmed` evidence，并且不能提升 public-search Low result。
- Greenhouse adapter 已完成多来源架构验证，但所有 Greenhouse tenant 当前默认禁用，不参与国内产品的自然语言 source routing。
- 自然语言 company resolution 可识别已登记但尚未支持的公司并诚实报告 coverage；实际 source routing 仍只覆盖当前 Source Catalog，不使用 browser agent。
- Discovery relevance 是当前 SearchContext 的 High/Medium/Low 可解释 band，不是 Candidate Match Score，也不会声称岗位“适合你本人”。
- 没有自动 Phase 3 matching、Cover Letter、Interview Copilot、unbounded browser Agent、RAG、MCP 或自动申请。
- 外部招聘站的 robots/Terms 与公开接口可用性可能变化；adapter 不会绕过访问限制。
