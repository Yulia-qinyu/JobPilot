from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import JobAnalysis


class JobAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_job(self, job_id: int) -> JobAnalysis | None:
        return self.db.scalar(select(JobAnalysis).where(JobAnalysis.job_id == job_id))

    def add(self, analysis: JobAnalysis) -> JobAnalysis:
        self.db.add(analysis)
        self.db.flush()
        return analysis

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, analysis: JobAnalysis) -> None:
        self.db.refresh(analysis)
