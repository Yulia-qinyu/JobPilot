import logging
from datetime import date
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ActivityEvent, DailyAdviceSnapshot, PlanItem
from app.repositories.profile_repository import DEFAULT_PROFILE_ID
from app.schemas.planning import (
    AddAdviceToPlanRequest,
    DailyAdviceItemOutput,
    DailyAdviceItemRead,
    DailyAdviceOutput,
    DailyAdviceSnapshotRead,
    PlanningGenerateRequest,
    PlanningTodayRead,
)
from app.schemas.workspace import PlanItemCreate, PlanItemRead
from app.services.activity_service import ActivityService
from app.services.application_management_agent import ApplicationManagementAgent
from app.services.claude_client import ClaudeStructuredClient
from app.services.planning_candidate_service import PlanningCandidateService
from app.services.planning_context_service import PlanningContextService
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)
EMPTY_MESSAGE = (
    "目前还没有足够的求职进度可以规划。可以先分析一个岗位、加入 My Jobs，"
    "或者添加今天的计划。"
)


class PlanningError(ValueError):
    pass


class PlanningNotFoundError(PlanningError):
    pass


class PlanningService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.context_service = PlanningContextService(db, settings)
        self.candidate_service = PlanningCandidateService()

    def get_today(self) -> PlanningTodayRead:
        context = self.context_service.build()
        snapshot = self._latest_snapshot(context.as_of)
        current_hash = self.context_service.context_hash(context)
        return PlanningTodayRead(
            snapshot=self._snapshot_read(snapshot) if snapshot else None,
            is_stale=(
                snapshot is not None
                and snapshot.planning_context_hash != current_hash
            ),
            empty_context=self.context_service.is_empty(context),
            empty_message=EMPTY_MESSAGE if self.context_service.is_empty(context) else None,
            timezone=context.timezone,
            as_of=context.as_of,
            signals=context.derived_signals,
        )

    def generate(
        self,
        payload: PlanningGenerateRequest,
        client: ClaudeStructuredClient,
    ) -> PlanningTodayRead:
        context = self.context_service.build()
        context_hash = self.context_service.context_hash(context)
        if self.context_service.is_empty(context):
            return PlanningTodayRead(
                snapshot=None,
                is_stale=False,
                empty_context=True,
                empty_message=EMPTY_MESSAGE,
                timezone=context.timezone,
                as_of=context.as_of,
                signals=context.derived_signals,
            )
        latest = self._latest_snapshot(context.as_of)
        if (
            latest is not None
            and latest.planning_context_hash == context_hash
            and not payload.force_regenerate
        ):
            return PlanningTodayRead(
                snapshot=self._snapshot_read(latest),
                is_stale=False,
                empty_context=False,
                empty_message=None,
                timezone=context.timezone,
                as_of=context.as_of,
                signals=context.derived_signals,
            )

        candidates = self.candidate_service.build(context)
        started = perf_counter()
        result = ApplicationManagementAgent(client).generate(context, candidates)
        elapsed_ms = round((perf_counter() - started) * 1000)
        metrics = client.last_call_metrics
        snapshot = DailyAdviceSnapshot(
            user_profile_id=DEFAULT_PROFILE_ID,
            advice_date=context.as_of,
            planning_context_hash=context_hash,
            strategy=context.job_search_strategy,
            response_json=result.output.model_dump(mode="json"),
            model=str(metrics.get("model") or client.model),
            input_tokens=self._metric_int(metrics.get("input_tokens")),
            output_tokens=self._metric_int(metrics.get("output_tokens")),
            latency_ms=(
                round(float(metrics["elapsed_seconds"]) * 1000)
                if metrics.get("elapsed_seconds") is not None
                else elapsed_ms
            ),
            status="Fallback" if result.fallback_used else "Generated",
        )
        self.db.add(snapshot)
        self.db.flush()
        ActivityService(self.db).record(
            "daily_advice_regenerated" if latest is not None else "daily_advice_generated",
            metadata={
                "snapshot_id": snapshot.id,
                "candidate_action_count": len(candidates),
                "advice_item_count": len(result.output.items),
                "validation_drops": result.validation_drops,
                "fallback_used": result.fallback_used,
            },
        )
        self.db.commit()
        self.db.refresh(snapshot)
        logger.info(
            "Daily planning completed planning_calls=1 model=%s context_size=%s "
            "candidate_action_count=%s advice_item_count=%s validation_drops=%s "
            "fallback_used=%s input_tokens=%s output_tokens=%s latency_ms=%s",
            snapshot.model,
            len(context.model_dump_json()),
            len(candidates),
            len(result.output.items),
            result.validation_drops,
            result.fallback_used,
            snapshot.input_tokens,
            snapshot.output_tokens,
            snapshot.latency_ms,
        )
        return PlanningTodayRead(
            snapshot=self._snapshot_read(snapshot),
            is_stale=False,
            empty_context=False,
            empty_message=None,
            timezone=context.timezone,
            as_of=context.as_of,
            signals=context.derived_signals,
        )

    def add_to_plan(
        self,
        snapshot_id: int,
        item_id: str,
        payload: AddAdviceToPlanRequest,
    ) -> PlanItemRead:
        snapshot = self.db.scalar(
            select(DailyAdviceSnapshot).where(
                DailyAdviceSnapshot.id == snapshot_id,
                DailyAdviceSnapshot.user_profile_id == DEFAULT_PROFILE_ID,
            )
        )
        if snapshot is None:
            raise PlanningNotFoundError("规划建议不存在。")
        output = DailyAdviceOutput.model_validate(snapshot.response_json)
        item = next((value for value in output.items if value.id == item_id), None)
        if item is None:
            raise PlanningNotFoundError("规划建议条目不存在。")
        existing = self._existing_plan_for_advice(snapshot_id, item_id)
        if existing is not None:
            return WorkspaceService(self.db)._plan_read(existing.id)
        plan_type = item.suggested_plan_type or self._plan_type(item)
        title = " ".join((payload.title or item.title).split())
        plan_date = payload.date or item.suggested_date or snapshot.advice_date
        return WorkspaceService(self.db).create_plan(
            PlanItemCreate(
                title=title,
                date=plan_date,
                job_id=item.related_job_id,
                type=plan_type,
                notes=f"来自 {snapshot.advice_date.isoformat()} 的 JobPilot 规划建议。",
            ),
            created_by="agent_suggestion",
            additional_activity=(
                "advice_added_to_plan",
                {"snapshot_id": snapshot.id, "advice_item_id": item.id},
            ),
        )

    def _latest_snapshot(self, advice_date: date) -> DailyAdviceSnapshot | None:
        return self.db.scalar(
            select(DailyAdviceSnapshot)
            .where(
                DailyAdviceSnapshot.user_profile_id == DEFAULT_PROFILE_ID,
                DailyAdviceSnapshot.advice_date == advice_date,
            )
            .order_by(
                DailyAdviceSnapshot.generated_at.desc(),
                DailyAdviceSnapshot.id.desc(),
            )
            .limit(1)
        )

    def _snapshot_read(self, snapshot: DailyAdviceSnapshot) -> DailyAdviceSnapshotRead:
        output = DailyAdviceOutput.model_validate(snapshot.response_json)
        added = self._added_plan_map(snapshot.id)
        return DailyAdviceSnapshotRead(
            id=snapshot.id,
            advice_date=snapshot.advice_date,
            summary=output.summary,
            items=[
                DailyAdviceItemRead(
                    **item.model_dump(), added_plan_item_id=added.get(item.id)
                )
                for item in output.items
            ],
            generated_at=snapshot.generated_at,
            model=snapshot.model,
            input_tokens=snapshot.input_tokens,
            output_tokens=snapshot.output_tokens,
            latency_ms=snapshot.latency_ms,
            status=snapshot.status,
        )

    def _added_plan_map(self, snapshot_id: int) -> dict[str, int]:
        events = self.db.scalars(
            select(ActivityEvent).where(
                ActivityEvent.user_profile_id == DEFAULT_PROFILE_ID,
                ActivityEvent.event_type == "advice_added_to_plan",
                ActivityEvent.plan_item_id.is_not(None),
            )
        ).all()
        plan_ids = set(self.db.scalars(select(PlanItem.id)).all())
        return {
            str(event.metadata_json.get("advice_item_id")): event.plan_item_id
            for event in events
            if event.metadata_json.get("snapshot_id") == snapshot_id
            and event.plan_item_id in plan_ids
            and event.plan_item_id is not None
        }

    def _existing_plan_for_advice(
        self, snapshot_id: int, item_id: str
    ) -> PlanItem | None:
        plan_id = self._added_plan_map(snapshot_id).get(item_id)
        return self.db.get(PlanItem, plan_id) if plan_id is not None else None

    @staticmethod
    def _plan_type(item: DailyAdviceItemOutput) -> str:
        mapping = {
            "apply": "application",
            "resume": "resume",
            "interview_prep": "interview_prep",
            "job_search": "job_search",
            "follow_up": "follow_up",
        }
        return mapping.get(item.action_type, "other")

    @staticmethod
    def _metric_int(value: object) -> int | None:
        return int(value) if isinstance(value, int) else None

