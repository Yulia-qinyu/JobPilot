from collections.abc import Sequence

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Job
from app.repositories.profile_repository import DEFAULT_PROFILE_ID


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, job: Job) -> Job:
        self.db.add(job)
        self.db.flush()
        return job

    def get(self, job_id: int) -> Job | None:
        return self.db.scalar(
            select(Job).where(
                Job.id == job_id,
                Job.user_profile_id == DEFAULT_PROFILE_ID,
            )
        )

    def get_by_source_identity(self, source: str, external_job_id: str) -> Job | None:
        return self.db.scalar(
            select(Job).where(
                Job.user_profile_id == DEFAULT_PROFILE_ID,
                Job.source == source,
                Job.external_job_id == external_job_id,
            )
        )

    def get_manual_duplicate(
        self,
        *,
        source_url: str | None,
        content_hash: str,
        company: str,
        role: str,
    ) -> Job | None:
        identity = [Job.source_content_hash == content_hash]
        if source_url:
            identity.append(Job.source_url == source_url)
        return self.db.scalar(
            select(Job).where(
                Job.user_profile_id == DEFAULT_PROFILE_ID,
                Job.source.is_(None),
                func.lower(Job.company) == company.casefold(),
                func.lower(Job.role) == role.casefold(),
                or_(*identity),
            ).order_by(Job.created_at.desc())
        )

    def by_source_identities(self, source: str, external_job_ids: list[str]) -> dict[str, Job]:
        if not external_job_ids:
            return {}
        jobs = self.db.scalars(
            select(Job).where(
                Job.user_profile_id == DEFAULT_PROFILE_ID,
                Job.source == source,
                Job.external_job_id.in_(external_job_ids),
            )
        ).all()
        return {job.external_job_id: job for job in jobs if job.external_job_id}

    def list_by_ids(self, job_ids: list[int]) -> list[Job]:
        if not job_ids:
            return []
        jobs = list(
            self.db.scalars(
                select(Job).where(
                    Job.user_profile_id == DEFAULT_PROFILE_ID,
                    Job.id.in_(job_ids),
                )
            ).all()
        )
        order = {job_id: index for index, job_id in enumerate(job_ids)}
        return sorted(jobs, key=lambda job: order.get(job.id, len(order)))

    def list(
        self,
        statuses: Sequence[str] | None = None,
        sort: str = "recent",
        limit: int | None = None,
    ) -> list[Job]:
        statement = select(Job).where(Job.user_profile_id == DEFAULT_PROFILE_ID)
        if statuses:
            statement = statement.where(Job.status.in_(statuses))
        if sort == "company":
            statement = statement.order_by(func.lower(Job.company), Job.created_at.desc())
        elif sort == "match_score":
            statement = statement.order_by(
                case((Job.match_score.is_(None), 1), else_=0),
                Job.match_score.desc(),
                Job.created_at.desc(),
            )
        else:
            statement = statement.order_by(Job.created_at.desc())
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.scalars(statement).all())

    def counts(self) -> dict[str, int]:
        row = self.db.execute(
            select(
                func.count(Job.id),
                func.count(Job.id).filter(
                    Job.status.in_(
                        ["Applied", "OA", "Interview", "Final Interview", "Offer", "Rejected"]
                    )
                ),
                func.count(Job.id).filter(Job.status.in_(["Interview", "Final Interview"])),
                func.count(Job.id).filter(Job.status == "Offer"),
            ).where(Job.user_profile_id == DEFAULT_PROFILE_ID)
        ).one()
        return {
            "total": int(row[0]),
            "applied": int(row[1]),
            "interviews": int(row[2]),
            "offers": int(row[3]),
        }

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, job: Job) -> None:
        self.db.refresh(job)

    def delete(self, job: Job) -> None:
        self.db.delete(job)
