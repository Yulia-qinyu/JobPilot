# Phase 8B — Daily Planning Human Evaluation

This artifact is for human product review. Advice must be generated from the compact `PlanningContext` and deterministic `PlanningCandidate` list. The review fields below are intentionally blank and must not be completed by Claude.

## Review scale

- Relevant?: Yes / Partial / No
- Actionable?: Yes / Partial / No
- Respects Schedule?: Yes / Partial / No
- Respects Strategy?: Yes / Partial / No
- Grounded?: Yes / Partial / No
- Would Follow?: Yes / Maybe / No

## Scenarios

### 1. High volume · low recent activity

- Strategy: `high_volume`
- Jobs Summary: 5 待投递；0 面试；过去 3 天无投递
- Plan Summary: 今日 1 项；逾期 0 项
- Recent Activity: 3 天内无 `application_status_changed → applied`
- Derived Signals: `pending_application_count=5`, `days_since_last_application=3`, `today_plan_load=1`
- Deterministic Candidates: 推进待投岗位；补充少量候选岗位；完善未完成岗位简历
- Generated Advice: ① 推进两个待投岗位；② 先处理准备度最高的岗位；③ 完成后补充一小批候选岗位。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 2. High volume · busy day

- Strategy: `high_volume`
- Jobs Summary: 4 待投递；0 面试
- Plan Summary: 今日 5 项；逾期 1 项
- Recent Activity: 昨日完成 2 个计划
- Derived Signals: `pending_application_count=4`, `today_plan_load=5`, `overdue_plan_count=1`
- Deterministic Candidates: 逾期计划；今日计划；待投岗位
- Generated Advice: ① 先处理逾期计划；② 完成今天已有的高优先任务；③ 若仍有余量，再推进一个待投岗位。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 3. Focused · high-match job missing tailored resume

- Strategy: `focused`
- Jobs Summary: 1 个 88% 有效匹配岗位；岗位简历未确认
- Plan Summary: 今日 0 项
- Recent Activity: 已完成该岗位分析
- Derived Signals: `jobs_without_tailored_resume_count=1`, `jobs_ready_to_apply_count=1`
- Deterministic Candidates: 完善岗位简历；推进投递
- Generated Advice: ① 完成 88% 匹配岗位的岗位简历；② 检查支持证据后推进该岗位投递。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 4. Focused · small job pool

- Strategy: `focused`
- Jobs Summary: 2 个重点岗位；均有有效分析
- Plan Summary: 今日 1 项
- Recent Activity: 近期无新增岗位
- Derived Signals: `pending_application_count=2`, `days_since_last_job_added=7`
- Deterministic Candidates: 两个岗位的简历/投递准备；不强制补充大量岗位
- Generated Advice: ① 深化 Job A 的岗位简历；② 推进 Job A；③ 复核 Job B 的准备缺口（未建议补充大量岗位）。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 5. Balanced · mixed application state

- Strategy: `balanced`
- Jobs Summary: 2 待投递；2 已投递；1 感兴趣
- Plan Summary: 今日 2 项；未来 7 天 2 项
- Recent Activity: 昨日新增岗位；昨日完成计划
- Derived Signals: `pending_application_count=3`, `today_plan_load=2`, `recent_completed_plan_count=1`
- Deterministic Candidates: 今日计划；推进一个待投岗位；完善一个岗位简历；跟进长期未更新岗位
- Generated Advice: ① 完成今日既有计划；② 推进一个待投岗位；③ 检查长期未更新的已投岗位。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 6. Interview tomorrow

- Strategy: `interview_first`
- Jobs Summary: 1 个岗位明天面试；3 个待投递
- Plan Summary: 今日有 1 项面试准备
- Recent Activity: 已记录 `interview_scheduled`
- Derived Signals: `upcoming_interview_count=1`, `today_plan_load=1`
- Deterministic Candidates: 明日面试准备；已有面试计划；待投岗位
- Generated Advice: ① 完成已关联的明日面试准备计划；② 有余量时推进一个待投岗位。已有计划与面试信号合并为一个动作。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 7. Interview today

- Strategy: `balanced`
- Jobs Summary: 1 个岗位今天面试；1 个待投递
- Plan Summary: 今日有面试复习与交通确认
- Recent Activity: 面试时间已记录
- Derived Signals: `upcoming_interview_count=1`, `today_plan_load=2`
- Deterministic Candidates: 今日面试准备；今日已安排计划；待投岗位降为次要
- Generated Advice: ① 完成今天的面试复习；② 确认已记录的面试安排；③ 其他投递动作降低优先级。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 8. Overdue plans

- Strategy: `balanced`
- Jobs Summary: 2 个活跃岗位
- Plan Summary: 2 项逾期；今日 1 项
- Recent Activity: 最近 7 天完成 0 项
- Derived Signals: `overdue_plan_count=2`, `today_plan_load=1`
- Deterministic Candidates: 两项逾期计划；今日计划；相关岗位动作
- Generated Advice: ① 处理最紧急的逾期计划；② 处理第二项逾期计划；③ 完成今日已有计划。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 9. No jobs and no meaningful context

- Strategy: `balanced`
- Jobs Summary: 0
- Plan Summary: 0
- Recent Activity: 无有效求职 activity
- Derived Signals: all counts 0
- Deterministic Result: 不调用 Claude；提示先分析岗位、加入 My Jobs 或添加计划
- Generated Advice: `目前还没有足够的求职进度可以规划。可以先分析一个岗位、加入 My Jobs，或者添加今天的计划。`
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 10. No plans but active jobs

- Strategy: `balanced`
- Jobs Summary: 1 待投递；1 已投递超过 3 天
- Plan Summary: 0
- Recent Activity: 有岗位加入和状态变化
- Derived Signals: `today_plan_load=0`, `jobs_ready_to_apply_count=1`
- Deterministic Candidates: 推进待投岗位；检查已投岗位后续；完善岗位简历
- Generated Advice: ① 推进待投岗位；② 检查已投岗位后续；③ 完善尚未确认的岗位简历。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 11. Custom status · first interview

- Strategy: `balanced`
- Jobs Summary: 自定义状态“一面”1 个；待投递 1 个
- Plan Summary: 今日 1 项准备计划
- Recent Activity: `application_status_changed` 到“一面”
- Derived Signals: custom status normalized to `interview`; `upcoming_interview_count` depends only on a recorded date
- Deterministic Candidates: 有日期时生成面试准备；无日期时不编造面试时间
- Generated Advice: ① 有已记录日期时准备“一面”；② 完成已关联的准备计划；未记录日期时不虚构日期。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

### 12. Stale advice and explicit replan

- Strategy: `balanced`
- Jobs Summary: 1 待投递；1 明日面试
- Plan Summary before: 1 面试准备 todo
- State change: 用户完成该计划
- Derived Signals after: `today_plan_load` decreases; `recent_completed_plan_count` increases
- Freshness: existing snapshot hash differs from current context hash; GET marks stale and makes 0 Claude calls
- Generated Advice before: ① 准备明日字节跳动面试；② 推进待投岗位。初次 smoke 中发现已有计划与面试候选重复，已在 deterministic candidate 层修复。
- Generated Advice after explicit replan: ① 完成已存在的字节跳动面试准备计划；② 推进抖音待投岗位。相同面试只保留一个动作；状态变化本身未触发 Claude，用户点击重新规划后才生成。
- Relevant?:
- Actionable?:
- Respects Schedule?:
- Respects Strategy?:
- Grounded?:
- Would Follow?:

## Aggregate human results

- Relevant: /12
- Actionable: /12
- Respects Schedule: /12
- Respects Strategy: /12
- Grounded: /12
- Would Follow: /12
- Harmful / fabricated advice count:
- Invalid job reference count:
- Automatic state mutation count:
- Reviewer notes:

## Live browser smoke measurement

- Strategy: `balanced`
- Jobs: 1 待投递；1 已投递；1 自定义“一面”，面试日期为 2026-08-28
- Plans before generation: 1 interview-prep todo；1 completed
- Calls before click: 0
- First explicit generation: 1 call, 3 validated items, interview preparation first
- Advice → Plan: explicit click; `created_by=agent_suggestion`; Job status unchanged; 0 calls
- Plan completion: snapshot became stale; 0 calls
- Explicit replan: 1 call; changed state reflected
- Regression discovered and fixed: existing interview-prep plan and interview signal no longer create duplicate actions
- Final fixed output: 2 grounded items (existing interview plan first, then one pending application)
- Model: `claude-sonnet-4-5-20250929`
- Measured snapshots during smoke: `3825/392 tokens, 9104 ms`; `3935/434 tokens, 7289 ms`; fix-verification `3819/283 tokens, 5210 ms`
- Note: the third call was a one-time engineering verification after fixing the duplicate-candidate regression, not normal product behavior.
