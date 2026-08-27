import re
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ApplicationStatusDefinition, Job, PlanItem
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.workspace import (
    ApplicationStatusCreate,
    ApplicationStatusDeleteResult,
    ApplicationStatusRead,
    ApplicationStatusUpdate,
    PlanItemCreate,
    PlanItemRead,
    PlanItemUpdate,
    StrategyRead,
)
from app.services.activity_service import ActivityService

DEFAULT_STATUSES = [
    ("interested", "感兴趣", 10, "Interested"),
    ("to_apply", "待投递", 20, "Preparing"),
    ("applied", "已投递", 30, "Applied"),
    ("oa", "笔试", 40, "OA"),
    ("interview", "面试中", 50, "Interview"),
    ("final_interview", "终面", 60, "Final Interview"),
    ("offer", "Offer", 70, "Offer"),
    ("rejected", "未通过", 80, "Rejected"),
    ("withdrawn", "已撤回", 90, "Withdrawn"),
]


class WorkspaceError(ValueError):
    pass


class WorkspaceNotFoundError(WorkspaceError):
    pass


class WorkspaceConflictError(WorkspaceError):
    pass


class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db
        self.activity = ActivityService(db)

    def ensure_default_statuses(self) -> list[ApplicationStatusDefinition]:
        ProfileRepository(self.db).ensure_default_profile()
        current = self.db.scalars(
            select(ApplicationStatusDefinition).where(
                ApplicationStatusDefinition.user_profile_id == DEFAULT_PROFILE_ID
            )
        ).all()
        by_key = {item.key: item for item in current}
        for key, label, order, legacy in DEFAULT_STATUSES:
            if key not in by_key:
                self.db.add(ApplicationStatusDefinition(
                    user_profile_id=DEFAULT_PROFILE_ID, key=key, label=label,
                    sort_order=order, is_system_default=True, is_active=True,
                    legacy_status=legacy,
                ))
        self.db.flush()
        return list(self.db.scalars(
            select(ApplicationStatusDefinition)
            .where(ApplicationStatusDefinition.user_profile_id == DEFAULT_PROFILE_ID)
            .order_by(ApplicationStatusDefinition.sort_order, ApplicationStatusDefinition.id)
        ).all())

    def get_strategy(self) -> StrategyRead:
        profile = ProfileRepository(self.db).ensure_default_profile()
        return StrategyRead(job_search_strategy=profile.job_search_strategy)

    def update_strategy(self, strategy: str) -> StrategyRead:
        profile = ProfileRepository(self.db).ensure_default_profile()
        old = profile.job_search_strategy
        profile.job_search_strategy = strategy
        if old != strategy:
            self.activity.record("job_search_strategy_changed", metadata={"from": old, "to": strategy})
        self.db.commit()
        return StrategyRead(job_search_strategy=strategy)

    def list_statuses(self) -> list[ApplicationStatusRead]:
        statuses = self.ensure_default_statuses()
        self._backfill_jobs(statuses)
        self.db.commit()
        return [ApplicationStatusRead.model_validate(item) for item in statuses if item.is_active]

    def create_status(self, payload: ApplicationStatusCreate) -> ApplicationStatusRead:
        statuses = self.ensure_default_statuses()
        label = " ".join(payload.label.split())
        if any(item.label.casefold() == label.casefold() for item in statuses):
            raise WorkspaceConflictError("该状态名称已存在。")
        key_base = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-") or "custom"
        key = f"custom-{key_base}-{int(datetime.now(UTC).timestamp() * 1000)}"
        order = max((item.sort_order for item in statuses), default=0) + 10
        item = ApplicationStatusDefinition(
            user_profile_id=DEFAULT_PROFILE_ID, key=key, label=label,
            sort_order=order, is_system_default=False, is_active=True,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return ApplicationStatusRead.model_validate(item)

    def update_status(self, status_id: int, payload: ApplicationStatusUpdate) -> ApplicationStatusRead:
        item = self._status(status_id)
        changes = payload.model_dump(exclude_unset=True)
        if "label" in changes:
            label = " ".join(changes["label"].split())
            duplicate = self.db.scalar(select(ApplicationStatusDefinition).where(
                ApplicationStatusDefinition.user_profile_id == DEFAULT_PROFILE_ID,
                func.lower(ApplicationStatusDefinition.label) == label.casefold(),
                ApplicationStatusDefinition.id != status_id,
            ))
            if duplicate:
                raise WorkspaceConflictError("该状态名称已存在。")
            item.label = label
        if "sort_order" in changes:
            item.sort_order = changes["sort_order"]
        self.db.commit()
        self.db.refresh(item)
        return ApplicationStatusRead.model_validate(item)

    def delete_status(self, status_id: int, migrate_to_status_id: int | None) -> ApplicationStatusDeleteResult:
        item = self._status(status_id)
        if item.is_system_default:
            raise WorkspaceConflictError("系统默认状态不能删除。")
        jobs = list(self.db.scalars(select(Job).where(Job.application_status_id == status_id)).all())
        if jobs and migrate_to_status_id is None:
            raise WorkspaceConflictError(f"该状态下还有 {len(jobs)} 个岗位，请先选择迁移状态。")
        target = self._status(migrate_to_status_id) if migrate_to_status_id is not None else None
        if target is not None and target.id == item.id:
            raise WorkspaceConflictError("迁移目标不能是当前状态。")
        for job in jobs:
            job.application_status = target
            job.application_status_id = target.id if target else None
            if target and target.legacy_status:
                job.status = target.legacy_status
        self.db.delete(item)
        self.db.commit()
        return ApplicationStatusDeleteResult(deleted_id=status_id, migrated_jobs=len(jobs))

    def list_plans(self) -> list[PlanItemRead]:
        items = self.db.scalars(
            select(PlanItem).where(PlanItem.user_profile_id == DEFAULT_PROFILE_ID)
            .options(selectinload(PlanItem.job))
            .order_by(PlanItem.status, PlanItem.date, PlanItem.time_optional, PlanItem.id)
        ).all()
        return [PlanItemRead.model_validate(item) for item in items]

    def create_plan(self, payload: PlanItemCreate) -> PlanItemRead:
        self._validate_job(payload.job_id)
        item = PlanItem(
            user_profile_id=DEFAULT_PROFILE_ID, title=" ".join(payload.title.split()),
            date=payload.date, time_optional=payload.time_optional, job_id=payload.job_id,
            type=payload.type, status="todo", notes=self._optional(payload.notes), created_by="user",
        )
        self.db.add(item)
        self.db.flush()
        self.activity.record("plan_added", job_id=item.job_id, plan_item_id=item.id, metadata={"plan_type": item.type})
        self.db.commit()
        return self._plan_read(item.id)

    def update_plan(self, plan_id: int, payload: PlanItemUpdate) -> PlanItemRead:
        item = self._plan(plan_id)
        changes = payload.model_dump(exclude_unset=True)
        if "job_id" in changes:
            self._validate_job(changes["job_id"])
        old_status = item.status
        for field, value in changes.items():
            if field in {"title", "notes"}:
                value = self._optional(value)
                if field == "title" and not value:
                    raise WorkspaceError("计划标题不能为空。")
            setattr(item, field, value)
        if "status" in changes and changes["status"] != old_status:
            item.completed_at = datetime.now(UTC) if item.status == "done" else None
            if item.status == "done":
                self.db.flush()
                self.activity.record("plan_completed", job_id=item.job_id, plan_item_id=item.id, metadata={"plan_type": item.type})
        self.db.commit()
        return self._plan_read(item.id)

    def delete_plan(self, plan_id: int) -> None:
        item = self._plan(plan_id)
        self.activity.record("plan_deleted", job_id=item.job_id, plan_item_id=item.id, metadata={"plan_type": item.type})
        self.db.delete(item)
        self.db.commit()

    def _backfill_jobs(self, statuses: list[ApplicationStatusDefinition]) -> None:
        by_legacy = {item.legacy_status: item.id for item in statuses if item.legacy_status}
        for job in self.db.scalars(select(Job).where(Job.user_profile_id == DEFAULT_PROFILE_ID, Job.application_status_id.is_(None))).all():
            job.application_status_id = by_legacy.get(job.status)

    def _status(self, status_id: int | None) -> ApplicationStatusDefinition:
        item = self.db.scalar(select(ApplicationStatusDefinition).where(
            ApplicationStatusDefinition.id == status_id,
            ApplicationStatusDefinition.user_profile_id == DEFAULT_PROFILE_ID,
            ApplicationStatusDefinition.is_active.is_(True),
        ))
        if item is None:
            raise WorkspaceNotFoundError("岗位状态不存在。")
        return item

    def _plan(self, plan_id: int) -> PlanItem:
        item = self.db.scalar(select(PlanItem).where(PlanItem.id == plan_id, PlanItem.user_profile_id == DEFAULT_PROFILE_ID))
        if item is None:
            raise WorkspaceNotFoundError("计划不存在。")
        return item

    def _plan_read(self, plan_id: int) -> PlanItemRead:
        item = self.db.scalar(select(PlanItem).where(PlanItem.id == plan_id).options(selectinload(PlanItem.job)))
        assert item is not None
        return PlanItemRead.model_validate(item)

    def _validate_job(self, job_id: int | None) -> None:
        if job_id is None:
            return
        job = self.db.scalar(select(Job).where(Job.id == job_id, Job.user_profile_id == DEFAULT_PROFILE_ID))
        if job is None:
            raise WorkspaceError("关联岗位不存在。")

    @staticmethod
    def _optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None
