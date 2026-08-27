from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import JobImportSession
from app.repositories.profile_repository import DEFAULT_PROFILE_ID


class JobImportRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, session: JobImportSession) -> JobImportSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get(self, session_id: int) -> JobImportSession | None:
        return self.db.scalar(
            select(JobImportSession).where(
                JobImportSession.id == session_id,
                JobImportSession.user_profile_id == DEFAULT_PROFILE_ID,
            )
        )

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, session: JobImportSession) -> None:
        self.db.refresh(session)
