from sqlalchemy.orm import Session

from app.db.models import Job, JobNote
from app.repositories.job_note_repository import JobNoteRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import DEFAULT_PROFILE_ID
from app.schemas.job_note import JobNoteRead
from app.services.activity_service import ActivityService


class JobNoteError(ValueError):
    pass


class JobNoteNotFound(JobNoteError):
    pass


class JobNoteService:
    """Canonical write path for Phase B notes.

    Methods deliberately do not commit so callers control the transaction
    boundary for note and activity-event persistence.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobNoteRepository(db)
        self.jobs = JobRepository(db)

    def list_notes(self, job_id: int) -> list[JobNoteRead]:
        self._job(job_id)
        return [JobNoteRead.model_validate(note) for note in self.repo.list_for_job(job_id)]

    def create_human_note(self, job_id: int, content: str) -> JobNote:
        job = self._job(job_id)
        note = self._create(job, content)
        ActivityService(self.db).record(
            "job_note_added", job_id=job_id, metadata={"author_type": "human"}
        )
        return note

    def update_human_note(self, job_id: int, note_id: int, content: str) -> JobNote:
        job = self._job(job_id)
        note = self._note(job_id, note_id)
        if note.author_type != "human":
            raise JobNoteError("Agent notes are read-only.")
        note.content = self._content(content)
        self._touch(job)
        ActivityService(self.db).record(
            "job_note_updated", job_id=job_id, metadata={"author_type": "human"}
        )
        self.db.flush()
        return note

    def delete_human_note(self, job_id: int, note_id: int) -> None:
        job = self._job(job_id)
        note = self._note(job_id, note_id)
        if note.author_type != "human":
            raise JobNoteError("Agent notes are read-only.")
        self.db.delete(note)
        self._touch(job)
        ActivityService(self.db).record(
            "job_note_deleted", job_id=job_id, metadata={"author_type": "human"}
        )
        self.db.flush()

    def latest_for_jobs(self, job_ids: list[int]) -> dict[int, JobNoteRead]:
        return {
            job_id: JobNoteRead.model_validate(note)
            for job_id, note in self.repo.latest_for_jobs(job_ids).items()
        }

    def _create(self, job: Job, content: str) -> JobNote:
        note = JobNote(
            user_profile_id=DEFAULT_PROFILE_ID,
            job_id=job.id,
            content=self._content(content),
            author_type="human",
            metadata_json={},
            dedupe_key=None,
        )
        self.db.add(note)
        self._touch(job)
        self.db.flush()
        return note

    def _job(self, job_id: int) -> Job:
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNoteNotFound("Job not found.")
        return job

    def _note(self, job_id: int, note_id: int) -> JobNote:
        note = self.repo.get(job_id, note_id)
        if note is None:
            raise JobNoteNotFound("Job note not found.")
        return note

    @staticmethod
    def _content(value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise JobNoteError("Note content is required.")
        return cleaned

    @staticmethod
    def _touch(job: Job) -> None:
        from app.db.models import utc_now

        job.updated_at = utc_now()
