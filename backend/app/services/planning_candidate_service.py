from app.schemas.planning import PlanningCandidate, PlanningContext


class PlanningCandidateService:
    """Builds a bounded, state-grounded action menu before Claude prioritizes it."""

    def build(self, context: PlanningContext) -> list[PlanningCandidate]:
        candidates: list[PlanningCandidate] = []
        as_of = context.as_of
        jobs_by_id = {job.job_id: job for job in context.active_jobs}
        planned_interview_job_ids = {
            item.related_job_id
            for item in context.plan_items
            if item.status == "todo"
            and item.date <= as_of
            and item.type == "interview_prep"
            and item.related_job_id is not None
        }

        for item in context.plan_items:
            if item.status != "todo" or item.date > as_of:
                continue
            overdue = item.date < as_of
            related_job = (
                jobs_by_id.get(item.related_job_id)
                if item.related_job_id is not None
                else None
            )
            interview_fact = (
                [f"已记录面试日期：{related_job.interview_date.isoformat()}。"]
                if item.type == "interview_prep"
                and related_job is not None
                and related_job.interview_date is not None
                else []
            )
            candidates.append(
                PlanningCandidate(
                    id=f"plan:{item.id}",
                    action_type="plan",
                    related_job_id=item.related_job_id,
                    suggested_plan_type=item.type,
                    suggested_date=as_of,
                    title=item.title,
                    signal="overdue_plan" if overdue else "today_plan",
                    urgency=90 if overdue else 82,
                    readiness="ready",
                    rationale_facts=[
                        f"该计划{'已逾期' if overdue else '安排在今天'}。",
                        *(
                            [f"关联岗位：{item.related_job}"]
                            if item.related_job
                            else []
                        ),
                        *interview_fact,
                    ],
                )
            )

        for item in context.plan_items:
            if item.status != "todo" or item.date <= as_of:
                continue
            days = (item.date - as_of).days
            candidates.append(
                PlanningCandidate(
                    id=f"upcoming-plan:{item.id}",
                    action_type="plan",
                    related_job_id=item.related_job_id,
                    suggested_plan_type=item.type,
                    suggested_date=item.date,
                    title=f"提前看一下：{item.title}",
                    signal="upcoming_plan",
                    urgency=max(35, 65 - days * 5),
                    readiness="informational",
                    rationale_facts=[
                        f"该计划安排在 {item.date.isoformat()}。",
                        *(
                            [f"关联岗位：{item.related_job}"]
                            if item.related_job
                            else []
                        ),
                    ],
                )
            )

        for job in context.active_jobs:
            if job.interview_date is not None:
                days = (job.interview_date - as_of).days
                if 0 <= days <= 7 and job.job_id not in planned_interview_job_ids:
                    candidates.append(
                        PlanningCandidate(
                            id=f"interview:{job.job_id}",
                            action_type="interview_prep",
                            related_job_id=job.job_id,
                            suggested_plan_type="interview_prep",
                            suggested_date=as_of,
                            title=f"准备 {job.company} · {job.title} 面试",
                            signal="upcoming_interview",
                            urgency=100 - min(days * 8, 40),
                            readiness="needs_preparation",
                            rationale_facts=[
                                f"面试日期是 {job.interview_date.isoformat()}（{days} 天后）。",
                                f"当前状态：{job.status_label}。",
                            ],
                        )
                    )

            if job.status_category == "to_apply":
                candidates.append(
                    PlanningCandidate(
                        id=f"apply:{job.job_id}",
                        action_type="apply",
                        related_job_id=job.job_id,
                        suggested_plan_type="application",
                        suggested_date=as_of,
                        title=f"推进 {job.company} · {job.title} 投递",
                        signal="ready_to_apply",
                        urgency=72,
                        readiness=(
                            "ready"
                            if job.tailored_resume_status == "Accepted"
                            else "needs_preparation"
                        ),
                        rationale_facts=[
                            "岗位当前处于待投递状态。",
                            *(
                                [f"有效 Match Score：{job.match_score}%。"]
                                if job.match_score is not None
                                else ["当前没有有效 Match Score。"]
                            ),
                            (
                                "岗位简历已确认。"
                                if job.tailored_resume_status == "Accepted"
                                else "岗位简历尚未确认完成。"
                            ),
                        ],
                    )
                )

            if (
                job.status_category in {"interested", "to_apply"}
                and job.tailored_resume_status != "Accepted"
                and job.has_valid_analysis
            ):
                candidates.append(
                    PlanningCandidate(
                        id=f"resume:{job.job_id}",
                        action_type="resume",
                        related_job_id=job.job_id,
                        suggested_plan_type="resume",
                        suggested_date=as_of,
                        title=f"完善 {job.company} · {job.title} 岗位简历",
                        signal="tailored_resume_missing",
                        urgency=68,
                        readiness="needs_preparation",
                        rationale_facts=[
                            "该岗位已有有效匹配分析。",
                            "岗位简历尚未确认完成。",
                            *(
                                [f"Match Score：{job.match_score}%。"]
                                if job.match_score is not None
                                else []
                            ),
                        ],
                    )
                )

            if job.status_category == "applied" and job.days_in_current_status >= 3:
                candidates.append(
                    PlanningCandidate(
                        id=f"follow-up:{job.job_id}",
                        action_type="follow_up",
                        related_job_id=job.job_id,
                        suggested_plan_type="follow_up",
                        suggested_date=as_of,
                        title=f"检查 {job.company} · {job.title} 后续进度",
                        signal="application_follow_up",
                        urgency=55,
                        readiness="informational",
                        rationale_facts=[
                            f"岗位已 {job.days_in_current_status} 天没有状态更新。",
                            "系统未假设招聘方已给出新的截止时间。",
                        ],
                    )
                )

        if (
            context.job_search_strategy == "high_volume"
            and (
                len(context.active_jobs) < 3
                or (context.derived_signals.days_since_last_job_added or 0) >= 3
            )
        ):
            candidates.append(
                PlanningCandidate(
                    id="job-search:pool",
                    action_type="job_search",
                    related_job_id=None,
                    suggested_plan_type="job_search",
                    suggested_date=as_of,
                    title="补充一小批新的候选岗位",
                    signal="low_job_pool_activity",
                    urgency=50,
                    readiness="ready",
                    rationale_facts=[
                        f"当前活跃岗位 {len(context.active_jobs)} 个。",
                        "当前策略是高频投递。",
                    ],
                )
            )

        if not candidates and context.active_jobs:
            job = context.active_jobs[0]
            candidates.append(
                PlanningCandidate(
                    id=f"review:{job.job_id}",
                    action_type="review",
                    related_job_id=job.job_id,
                    suggested_plan_type="other",
                    suggested_date=as_of,
                    title=f"确认 {job.company} · {job.title} 的下一步",
                    signal="active_job_review",
                    urgency=40,
                    readiness="informational",
                    rationale_facts=[
                        f"当前状态：{job.status_label}。",
                        "没有发现更紧急的已知日期。",
                    ],
                )
            )

        strategy_bonus = {
            "high_volume": {"apply": 25, "job_search": 20, "follow_up": 10},
            "focused": {"resume": 25, "review": 15, "interview_prep": 10},
            "balanced": {
                "apply": 10,
                "resume": 10,
                "interview_prep": 15,
                "plan": 10,
            },
            "interview_first": {"interview_prep": 35, "plan": 15},
        }[context.job_search_strategy]
        candidates.sort(
            key=lambda item: (
                -(item.urgency + strategy_bonus.get(item.action_type, 0)),
                item.id,
            )
        )
        return candidates[:15]
