from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Experience,
    ExperienceFact,
    JobDecision,
    TargetCompany,
    TargetRole,
    UserProfile,
)

DEFAULT_PROFILE_ID = 1


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_default_profile(self) -> UserProfile:
        profile = self.db.get(UserProfile, DEFAULT_PROFILE_ID)
        if profile is None:
            profile = UserProfile(id=DEFAULT_PROFILE_ID)
            self.db.add(profile)
            self.db.flush()
        return profile

    def get_full_profile(self) -> UserProfile:
        self.ensure_default_profile()
        statement = (
            select(UserProfile)
            .where(UserProfile.id == DEFAULT_PROFILE_ID)
            .execution_options(populate_existing=True)
            .options(
                selectinload(UserProfile.resume),
                selectinload(UserProfile.target_companies),
                selectinload(UserProfile.target_roles),
                selectinload(UserProfile.experiences).selectinload(Experience.facts),
            )
        )
        return self.db.scalars(statement).one()

    def find_full_profile(self) -> UserProfile | None:
        """Read the current profile without creating one as a side effect."""
        statement = (
            select(UserProfile)
            .where(UserProfile.id == DEFAULT_PROFILE_ID)
            .execution_options(populate_existing=True)
            .options(
                selectinload(UserProfile.resume),
                selectinload(UserProfile.target_companies),
                selectinload(UserProfile.target_roles),
                selectinload(UserProfile.experiences).selectinload(Experience.facts),
            )
        )
        return self.db.scalar(statement)

    def find_company(self, company_id: int) -> TargetCompany | None:
        return self.db.scalar(
            select(TargetCompany).where(
                TargetCompany.id == company_id,
                TargetCompany.user_profile_id == DEFAULT_PROFILE_ID,
            )
        )

    def find_company_by_name(
        self, name: str, exclude_id: int | None = None
    ) -> TargetCompany | None:
        query = select(TargetCompany).where(
            TargetCompany.user_profile_id == DEFAULT_PROFILE_ID,
            func.lower(TargetCompany.name) == name.lower(),
        )
        if exclude_id is not None:
            query = query.where(TargetCompany.id != exclude_id)
        return self.db.scalar(query)

    def find_role(self, role_id: int) -> TargetRole | None:
        return self.db.scalar(
            select(TargetRole).where(
                TargetRole.id == role_id,
                TargetRole.user_profile_id == DEFAULT_PROFILE_ID,
            )
        )

    def find_role_by_name(self, name: str, exclude_id: int | None = None) -> TargetRole | None:
        query = select(TargetRole).where(
            TargetRole.user_profile_id == DEFAULT_PROFILE_ID,
            func.lower(TargetRole.name) == name.lower(),
        )
        if exclude_id is not None:
            query = query.where(TargetRole.id != exclude_id)
        return self.db.scalar(query)

    def find_experience(self, experience_id: int) -> Experience | None:
        return self.db.scalar(
            select(Experience)
            .where(
                Experience.id == experience_id,
                Experience.user_profile_id == DEFAULT_PROFILE_ID,
            )
            .options(selectinload(Experience.facts))
        )

    def find_fact(self, fact_id: int) -> ExperienceFact | None:
        return self.db.scalar(
            select(ExperienceFact)
            .join(Experience)
            .where(
                ExperienceFact.id == fact_id,
                Experience.user_profile_id == DEFAULT_PROFILE_ID,
            )
        )

    def resume_experiences(self, resume_id: int) -> list[Experience]:
        return list(
            self.db.scalars(
                select(Experience)
                .where(Experience.source_resume_id == resume_id)
                .options(selectinload(Experience.facts))
            ).all()
        )

    def commit(self) -> None:
        self.db.commit()

    def mark_job_decisions_stale(self, *, analysis_stale: bool = False) -> None:
        values: dict[str, object] = {"is_stale": True}
        if analysis_stale:
            values["analysis_hash"] = None
        self.db.execute(update(JobDecision).values(**values))

    def delete(self, instance: object) -> None:
        self.db.delete(instance)
