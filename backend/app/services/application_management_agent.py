import json
import re
from dataclasses import dataclass

from app.schemas.planning import (
    DailyAdviceItemOutput,
    DailyAdviceOutput,
    PlanningCandidate,
    PlanningContext,
)
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient

UNSAFE_ADVICE = re.compile(
    r"自动(?:投递|申请|删除|修改状态)|替你(?:投递|申请)|删除岗位|"
    r"修改(?:求职策略|Master Resume|主简历)|直接标记为已投递",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PlanningAgentResult:
    output: DailyAdviceOutput
    fallback_used: bool
    validation_drops: int


class ApplicationManagementAgent:
    """One bounded planning call over backend-grounded action candidates."""

    PROMPT_VERSION = "daily-planning-v1"
    SCHEMA_VERSION = "daily-advice-wire-v1"

    def __init__(self, client: ClaudeStructuredClient):
        self.client = client

    def generate(
        self, context: PlanningContext, candidates: list[PlanningCandidate]
    ) -> PlanningAgentResult:
        try:
            raw = self.client.generate(
                prompt=self._prompt(context, candidates),
                output_model=DailyAdviceOutput,
                tool_name="generate_daily_advice",
            )
        except ClaudeServiceError:
            return PlanningAgentResult(
                output=self._fallback(candidates),
                fallback_used=True,
                validation_drops=0,
            )
        normalized, drops = self._normalize(raw, context, candidates)
        if normalized is None:
            return PlanningAgentResult(
                output=self._fallback(candidates),
                fallback_used=True,
                validation_drops=drops,
            )
        return PlanningAgentResult(
            output=normalized,
            fallback_used=False,
            validation_drops=drops,
        )

    def _prompt(
        self, context: PlanningContext, candidates: list[PlanningCandidate]
    ) -> str:
        compact_context = context.model_dump(mode="json")
        return f"""
You are JobPilot's bounded Application Management Agent.
Help the user decide what to do today. The user owns every action and all state.

Rules:
- Select, order, and explain only actions from CANDIDATE_ACTIONS.
- Return 3–5 items when enough candidates exist; otherwise return the useful available items.
- Respect strategy, existing plans, today's workload, and known interview dates.
- Never invent a job, interview, deadline, score, completed action, or candidate fact.
- Never propose automatic application, status mutation, job deletion, strategy mutation, or Master Resume mutation.
- Match Score is a planning signal, never a reason to tell the user not to apply.
- Keep titles concise and reasons grounded in the supplied rationale facts.
- Every output id, action_type, related_job_id, and suggested_plan_type must exactly match its selected candidate.
- Do not output prose outside the structured response.

PLANNING_CONTEXT:
{json.dumps(compact_context, ensure_ascii=False, separators=(',', ':'))}

CANDIDATE_ACTIONS:
{json.dumps([item.model_dump(mode='json') for item in candidates], ensure_ascii=False, separators=(',', ':'))}
""".strip()

    def _normalize(
        self,
        output: DailyAdviceOutput,
        context: PlanningContext,
        candidates: list[PlanningCandidate],
    ) -> tuple[DailyAdviceOutput | None, int]:
        allowed = {item.id: item for item in candidates}
        valid_job_ids = {item.job_id for item in context.active_jobs}
        seen: set[str] = set()
        normalized: list[DailyAdviceItemOutput] = []
        drops = 0
        for item in output.items:
            candidate = allowed.get(item.id)
            if candidate is None or item.id in seen:
                drops += 1
                continue
            seen.add(item.id)
            title = " ".join(item.title.split())[:255]
            reason = " ".join(item.reason.split())[:800]
            if (
                item.action_type != candidate.action_type
                or item.related_job_id != candidate.related_job_id
                or item.suggested_plan_type != candidate.suggested_plan_type
                or (
                    item.related_job_id is not None
                    and item.related_job_id not in valid_job_ids
                )
                or not title
                or not reason
                or UNSAFE_ADVICE.search(f"{title} {reason}")
            ):
                drops += 1
                continue
            normalized.append(
                item.model_copy(
                    update={
                        "title": title,
                        "reason": reason,
                        "suggested_date": candidate.suggested_date,
                    }
                )
            )
            if len(normalized) == 5:
                break
        summary = " ".join(output.summary.split())[:500]
        if not normalized:
            return None, drops
        return (
            DailyAdviceOutput(
                summary=summary
                or "已根据当前岗位、计划和近期进度整理今日优先事项。",
                items=normalized,
            ),
            drops,
        )

    @staticmethod
    def _fallback(candidates: list[PlanningCandidate]) -> DailyAdviceOutput:
        items = [
            DailyAdviceItemOutput(
                id=item.id,
                priority="high" if item.urgency >= 80 else "medium",
                action_type=item.action_type,
                title=item.title,
                reason=" ".join(item.rationale_facts),
                related_job_id=item.related_job_id,
                suggested_plan_type=item.suggested_plan_type,
                suggested_date=item.suggested_date,
            )
            for item in candidates[:3]
        ]
        if not items:
            items = [
                DailyAdviceItemOutput(
                    id="review:workspace",
                    priority="low",
                    action_type="review",
                    title="查看未完成计划和活跃岗位",
                    reason="这次个性化规划暂时不可用，可以先从已有计划和岗位中确认下一步。",
                    related_job_id=None,
                    suggested_plan_type="other",
                    suggested_date=None,
                )
            ]
        return DailyAdviceOutput(
            summary="这次规划没有完整生成，先提供基于当前状态的安全建议。",
            items=items,
        )
