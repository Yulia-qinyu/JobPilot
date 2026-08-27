from dataclasses import asdict, dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Experience,
    ExperienceFact,
    Job,
    JobAnalysis,
    JobDecision,
    JobImportSession,
    Resume,
    ResumeTailoring,
    TargetCompany,
    TargetRole,
    UserProfile,
)


@dataclass(frozen=True)
class JobWorkspaceCounts:
    jobs: int
    job_decisions: int
    job_analyses: int
    resume_tailorings: int
    job_import_sessions: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateKnowledgeCounts:
    user_profiles: int
    resumes: int
    experiences: int
    experience_facts: int
    target_roles: int
    target_companies: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class JobWorkspaceResetService:
    """Delete the local Job workspace without touching candidate-owned data.

    The caller owns the transaction. Production code must never invoke this service.
    """

    def __init__(self, db: Session):
        self.db = db

    def workspace_counts(self) -> JobWorkspaceCounts:
        return JobWorkspaceCounts(
            jobs=self._count(Job),
            job_decisions=self._count(JobDecision),
            job_analyses=self._count(JobAnalysis),
            resume_tailorings=self._count(ResumeTailoring),
            job_import_sessions=self._count(JobImportSession),
        )

    def candidate_counts(self) -> CandidateKnowledgeCounts:
        return CandidateKnowledgeCounts(
            user_profiles=self._count(UserProfile),
            resumes=self._count(Resume),
            experiences=self._count(Experience),
            experience_facts=self._count(ExperienceFact),
            target_roles=self._count(TargetRole),
            target_companies=self._count(TargetCompany),
        )

    def reset(self) -> JobWorkspaceCounts:
        before = self.workspace_counts()
        # Explicit child-first deletes keep behavior consistent even when a local
        # SQLite test connection does not enable foreign-key cascades.
        self.db.execute(delete(ResumeTailoring))
        self.db.execute(delete(JobDecision))
        self.db.execute(delete(JobAnalysis))
        self.db.execute(delete(Job))
        self.db.execute(delete(JobImportSession))
        return before

    def _count(self, model: type) -> int:
        return int(self.db.scalar(select(func.count()).select_from(model)) or 0)
