from collections.abc import Sequence

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.db.models import Job, JobAnalysis, JobDecision
from app.repositories.profile_repository import DEFAULT_PROFILE_ID


class JobDecisionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, job_id: int) -> JobDecision | None:
        return self.db.scalar(
            select(JobDecision)
            .join(Job)
            .where(JobDecision.job_id == job_id, Job.user_profile_id == DEFAULT_PROFILE_ID)
        )

    def add(self, decision: JobDecision) -> JobDecision:
        self.db.add(decision)
        self.db.flush()
        return decision

    def jobs_for_recompute(self, job_ids: Sequence[int] | None = None) -> list[Job]:
        # Phase 3 may have inserted/replaced the one-to-one analysis after this
        # session previously observed an empty relationship.
        self.db.expire_all()
        statement = (
            select(Job)
            .where(Job.user_profile_id == DEFAULT_PROFILE_ID)
            .options(selectinload(Job.analysis), selectinload(Job.decision))
            .order_by(Job.id)
        )
        if job_ids is not None:
            statement = statement.where(Job.id.in_(job_ids))
        return list(self.db.scalars(statement).all())

    def mark_all_stale(self) -> None:
        self.db.execute(update(JobDecision).values(is_stale=True))

    def mark_stale(self, job_id: int) -> None:
        self.db.execute(
            update(JobDecision).where(JobDecision.job_id == job_id).values(is_stale=True)
        )

    def page(
        self,
        *,
        page: int,
        page_size: int,
        eligibility: str | None,
        role_family: str | None,
        role_fit: str | None,
        match_status: str | None,
        decision_value: str | None,
        company: str | None,
        source: str | None,
        application_status: str | None,
        job_ids: Sequence[int] | None,
        sort: str,
    ) -> tuple[list[tuple[Job, JobDecision | None, JobAnalysis | None]], int]:
        filters = [Job.user_profile_id == DEFAULT_PROFILE_ID]
        if eligibility:
            filters.append(JobDecision.effective_eligibility_status == eligibility)
        if role_family:
            filters.append(JobDecision.effective_role_family == role_family)
        if role_fit:
            filters.append(
                JobDecision.target_role_fit.in_(["Primary", "Secondary"])
                if role_fit == "Target"
                else JobDecision.target_role_fit == role_fit
            )
        if decision_value:
            filters.append(
                or_(
                    JobDecision.final_decision == decision_value,
                    JobDecision.pre_match_decision == decision_value,
                )
            )
        if company:
            filters.append(func.lower(Job.company).contains(company.casefold()))
        if source == "manual":
            filters.append(Job.source.is_(None))
        elif source:
            filters.append(Job.source == source)
        if application_status:
            if application_status.isdigit():
                filters.append(Job.application_status_id == int(application_status))
            else:
                filters.append(Job.status == application_status)
        if job_ids is not None:
            filters.append(Job.id.in_(job_ids))
        if match_status == "analyzed":
            filters.extend([JobAnalysis.id.is_not(None), JobDecision.analysis_hash.is_not(None)])
        elif match_status == "pending":
            filters.append(JobAnalysis.id.is_(None))
        elif match_status == "stale":
            filters.extend([JobAnalysis.id.is_not(None), JobDecision.analysis_hash.is_(None)])

        base = (
            select(Job, JobDecision, JobAnalysis)
            .options(selectinload(Job.application_status))
            .outerjoin(JobDecision, JobDecision.job_id == Job.id)
            .outerjoin(JobAnalysis, JobAnalysis.job_id == Job.id)
            .where(*filters)
        )
        count_statement = (
            select(func.count(Job.id))
            .outerjoin(JobDecision, JobDecision.job_id == Job.id)
            .outerjoin(JobAnalysis, JobAnalysis.job_id == Job.id)
            .where(*filters)
        )
        if sort == "company":
            base = base.order_by(func.lower(Job.company), func.lower(Job.role))
        elif sort == "match_score":
            base = base.order_by(
                case((Job.match_score.is_(None), 1), else_=0), Job.match_score.desc(), Job.id.desc()
            )
        elif sort == "role_fit":
            base = base.order_by(
                case(
                    (JobDecision.target_role_fit == "Primary", 0),
                    (JobDecision.target_role_fit == "Secondary", 1),
                    (JobDecision.target_role_fit == "Exploratory", 2),
                    (JobDecision.target_role_fit == "Low", 3),
                    (JobDecision.target_role_fit == "Unknown", 4),
                    else_=5,
                ),
                Job.id.desc(),
            )
        elif sort == "decision":
            base = base.order_by(
                case(
                    (JobDecision.final_decision == "Priority", 0),
                    (JobDecision.final_decision == "Apply", 1),
                    (JobDecision.pre_match_decision == "WorthAnalyzing", 2),
                    (JobDecision.final_decision == "Consider", 3),
                    (JobDecision.pre_match_decision == "LowPriority", 4),
                    else_=5,
                ),
                Job.match_score.desc().nullslast(),
                Job.id.desc(),
            )
        else:
            base = base.order_by(Job.created_at.desc(), Job.id.desc())
        rows = list(self.db.execute(base.offset((page - 1) * page_size).limit(page_size)).all())
        total = int(self.db.scalar(count_statement) or 0)
        return rows, total

    def summary(self) -> dict[str, int]:
        current = JobDecision.is_stale.is_(False)
        row = self.db.execute(
            select(
                func.count(Job.id),
                func.count(JobDecision.id).filter(
                    current, JobDecision.effective_eligibility_status == "Eligible"
                ),
                func.count(JobDecision.id).filter(
                    current, JobDecision.target_role_fit.in_(["Primary", "Secondary"])
                ),
                func.count(JobDecision.id).filter(current, JobDecision.analysis_hash.is_not(None)),
                func.count(JobDecision.id).filter(
                    current, JobDecision.final_decision == "Priority"
                ),
            )
            .select_from(Job)
            .outerjoin(JobDecision, JobDecision.job_id == Job.id)
            .where(Job.user_profile_id == DEFAULT_PROFILE_ID)
        ).one()
        return {
            "total": int(row[0]),
            "no_explicit_blocker": int(row[1]),
            "target_fit": int(row[2]),
            "analyzed": int(row[3]),
            "priority": int(row[4]),
        }

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, decision: JobDecision) -> None:
        self.db.refresh(decision)
