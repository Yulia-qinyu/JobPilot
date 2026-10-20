from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import ApplicationStatusDefinition, Job
from app.services.activity_service import ActivityService


@dataclass(frozen=True)
class StatusTransitionResult:
    changed: bool
    previous_label: str
    new_label: str


class ApplicationStatusTransitionService:
    """Single transaction boundary for user-maintained application status changes."""

    def __init__(self, db: Session):
        self.db = db

    def apply(
        self,
        job: Job,
        target: ApplicationStatusDefinition,
        *,
        source: str,
        detected_at: datetime | None = None,
    ) -> StatusTransitionResult:
        previous = (
            self.db.get(ApplicationStatusDefinition, job.application_status_id)
            if job.application_status_id is not None
            else None
        )
        previous_label = previous.label if previous else job.status
        if job.application_status_id == target.id:
            return StatusTransitionResult(False, previous_label, target.label)

        changed_at = detected_at or datetime.now(UTC)
        job.application_status_id = target.id
        job.application_status = target
        if target.legacy_status:
            job.status = target.legacy_status
        job.application_status_changed_at = changed_at
        ActivityService(self.db).record(
            "application_status_changed",
            job_id=job.id,
            metadata={
                "source": source,
                "from_status_id": previous.id if previous else None,
                "from_status_key": previous.key if previous else None,
                "from_status_label": previous_label,
                "to_status_id": target.id,
                "to_status_key": target.key,
                "to_status_label": target.label,
                "detected_at": changed_at.isoformat(),
            },
        )
        return StatusTransitionResult(True, previous_label, target.label)
