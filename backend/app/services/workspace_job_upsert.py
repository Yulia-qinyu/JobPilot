from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import Job
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.services.activity_service import ActivityService
from app.services.decision_integration import safe_recompute_job_decisions
from app.services.job_sources.base import ImportedJobDraft
from app.services.workspace_service import WorkspaceService


@dataclass(frozen=True)
class WorkspaceUpsertResult:
    outcome: str
    job: Job


class WorkspaceJobUpsertService:
    """Materialize a trusted normalized source job into the user-owned workspace."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def upsert(self, draft: ImportedJobDraft) -> WorkspaceUpsertResult:
        self._validate_identity(draft)
        now = datetime.now(UTC)
        job = self.repo.get_by_source_identity(draft.source, draft.external_job_id)
        if job is None:
            ProfileRepository(self.db).ensure_default_profile()
            statuses = WorkspaceService(self.db).ensure_default_statuses()
            interested = next(item for item in statuses if item.legacy_status == "Interested")
            job = Job(
                user_profile_id=DEFAULT_PROFILE_ID,
                company=draft.company,
                role=draft.role,
                location=draft.location,
                recruitment_type=draft.recruitment_type,
                source_url=draft.source_url,
                original_jd=draft.original_jd,
                structured_jd=draft.structured_jd.model_dump(mode="json"),
                published_date=draft.published_date,
                status="Interested",
                application_status_id=interested.id,
                match_score=None,
                recommendation=None,
                parser_model=None,
                parser_prompt_version=None,
                parser_schema_version=None,
                source_content_hash=draft.source_content_hash,
                source=draft.source,
                external_job_id=draft.external_job_id,
                external_job_code=draft.external_job_code,
                source_metadata=draft.source_metadata,
                last_seen_at=now,
            )
            self.repo.add(job)
            ActivityService(self.db).record("job_added", job_id=job.id, metadata={"source": draft.source})
            return WorkspaceUpsertResult("created", job)

        job.last_seen_at = now
        job.external_job_code = draft.external_job_code
        if job.source_content_hash == draft.source_content_hash:
            return WorkspaceUpsertResult("existing", job)
        for field in (
            "company",
            "role",
            "location",
            "recruitment_type",
            "source_url",
            "original_jd",
            "published_date",
            "source_metadata",
            "source_content_hash",
        ):
            setattr(job, field, getattr(draft, field))
        job.structured_jd = draft.structured_jd.model_dump(mode="json")
        job.parser_model = None
        job.parser_prompt_version = None
        job.parser_schema_version = None
        job.match_score = None
        job.recommendation = None
        return WorkspaceUpsertResult("updated", job)

    def commit_and_recompute(self, result: WorkspaceUpsertResult) -> None:
        self.db.commit()
        self.repo.refresh(result.job)
        if result.outcome in {"created", "updated"}:
            safe_recompute_job_decisions(self.db, [result.job.id])

    @staticmethod
    def _validate_identity(draft: ImportedJobDraft) -> None:
        if not draft.source.strip() or not draft.external_job_id.strip():
            raise ValueError("A source job requires source and external_job_id.")
