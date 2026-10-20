from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import JobNote
from app.repositories.profile_repository import DEFAULT_PROFILE_ID


class JobNoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, job_id: int, note_id: int) -> JobNote | None:
        return self.db.scalar(
            select(JobNote).where(
                JobNote.id == note_id,
                JobNote.job_id == job_id,
                JobNote.user_profile_id == DEFAULT_PROFILE_ID,
            )
        )

    def list_for_job(self, job_id: int) -> list[JobNote]:
        return list(
            self.db.scalars(
                select(JobNote)
                .where(
                    JobNote.job_id == job_id,
                    JobNote.user_profile_id == DEFAULT_PROFILE_ID,
                )
                .order_by(JobNote.created_at.desc(), JobNote.id.desc())
            ).all()
        )

    def latest_for_jobs(self, job_ids: Sequence[int]) -> dict[int, JobNote]:
        if not job_ids:
            return {}
        ranked = (
            select(
                JobNote.id.label("note_id"),
                JobNote.job_id,
                func.row_number()
                .over(
                    partition_by=JobNote.job_id,
                    order_by=(JobNote.created_at.desc(), JobNote.id.desc()),
                )
                .label("rank"),
            )
            .where(
                JobNote.user_profile_id == DEFAULT_PROFILE_ID,
                JobNote.job_id.in_(job_ids),
            )
            .subquery()
        )
        notes = self.db.scalars(
            select(JobNote).join(ranked, ranked.c.note_id == JobNote.id).where(ranked.c.rank == 1)
        ).all()
        return {note.job_id: note for note in notes}

    def by_dedupe_key(self, job_id: int, dedupe_key: str) -> JobNote | None:
        return self.db.scalar(
            select(JobNote).where(
                JobNote.job_id == job_id,
                JobNote.user_profile_id == DEFAULT_PROFILE_ID,
                JobNote.dedupe_key == dedupe_key,
            )
        )
