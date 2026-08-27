from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResumeTailoring


class ResumeTailoringRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_job(self, job_id: int) -> ResumeTailoring | None:
        return self.db.scalar(select(ResumeTailoring).where(ResumeTailoring.job_id == job_id))

    def add(self, value: ResumeTailoring) -> ResumeTailoring:
        self.db.add(value)
        self.db.flush()
        return value

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, value: ResumeTailoring) -> None:
        self.db.refresh(value)
