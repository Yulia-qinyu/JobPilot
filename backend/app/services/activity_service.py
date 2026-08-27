from sqlalchemy.orm import Session

from app.db.models import ActivityEvent
from app.repositories.profile_repository import DEFAULT_PROFILE_ID


class ActivityService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        event_type: str,
        *,
        job_id: int | None = None,
        plan_item_id: int | None = None,
        metadata: dict | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            user_profile_id=DEFAULT_PROFILE_ID,
            event_type=event_type,
            job_id=job_id,
            plan_item_id=plan_item_id,
            metadata_json=metadata or {},
        )
        self.db.add(event)
        return event

