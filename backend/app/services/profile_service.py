from sqlalchemy.orm import Session

from app.db.models import Experience, ExperienceFact, Resume, TargetCompany, TargetRole
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.analysis import ResumeProfile
from app.schemas.profile import ProfileRead, RolePriority, TargetRoleUpdate
from app.services.activity_service import ActivityService
from app.services.role_classifier import RoleClassifier

MAX_TARGETS = 5


class ProfileError(ValueError):
    pass


class ProfileNotFoundError(ProfileError):
    pass


class ProfileConflictError(ProfileError):
    pass


class ProfileLimitError(ProfileError):
    pass


class ProfileService:
    def __init__(self, db: Session):
        self.repo = ProfileRepository(db)
        self.role_classifier = RoleClassifier()

    def get_profile(self) -> ProfileRead:
        profile = self.repo.get_full_profile()
        self.repo.commit()
        return ProfileRead.model_validate(profile)

    def update_location(self, location: str | None) -> ProfileRead:
        profile = self.repo.ensure_default_profile()
        profile.preferred_location = self._clean_optional(location)
        self.repo.mark_job_decisions_stale()
        self.repo.commit()
        return self.get_profile()

    def update_candidate_identity(
        self, candidate_type: str | None, graduation_year: int | None
    ) -> ProfileRead:
        if candidate_type not in {None, "graduate", "experienced", "both"}:
            raise ProfileError("Invalid candidate type.")
        if graduation_year is not None and not 1900 <= graduation_year <= 2200:
            raise ProfileError("Invalid graduation year.")
        if candidate_type in {None, "experienced"}:
            graduation_year = None
        profile = self.repo.ensure_default_profile()
        previous = {
            "candidate_type": profile.candidate_type,
            "graduation_year": profile.graduation_year,
        }
        profile.candidate_type = candidate_type
        profile.graduation_year = graduation_year
        self.repo.mark_job_decisions_stale(analysis_stale=True)
        ActivityService(self.repo.db).record(
            "candidate_identity_changed",
            metadata={
                "from": previous,
                "to": {
                    "candidate_type": candidate_type,
                    "graduation_year": graduation_year,
                },
            },
        )
        self.repo.commit()
        return self.get_profile()

    def add_company(self, name: str) -> ProfileRead:
        clean_name = self._clean_name(name)
        profile = self.repo.get_full_profile()
        if len(profile.target_companies) >= MAX_TARGETS:
            raise ProfileLimitError("You can save up to 5 target companies.")
        if self.repo.find_company_by_name(clean_name):
            raise ProfileConflictError("That target company is already saved.")
        self.repo.db.add(TargetCompany(user_profile_id=DEFAULT_PROFILE_ID, name=clean_name))
        self.repo.commit()
        return self.get_profile()

    def update_company(self, company_id: int, name: str) -> ProfileRead:
        company = self.repo.find_company(company_id)
        if company is None:
            raise ProfileNotFoundError("Target company not found.")
        clean_name = self._clean_name(name)
        if self.repo.find_company_by_name(clean_name, exclude_id=company_id):
            raise ProfileConflictError("That target company is already saved.")
        company.name = clean_name
        self.repo.commit()
        return self.get_profile()

    def delete_company(self, company_id: int) -> ProfileRead:
        company = self.repo.find_company(company_id)
        if company is None:
            raise ProfileNotFoundError("Target company not found.")
        self.repo.delete(company)
        self.repo.commit()
        return self.get_profile()

    def add_role(self, name: str, priority: RolePriority = "primary") -> ProfileRead:
        clean_name = self._clean_name(name)
        profile = self.repo.get_full_profile()
        if len(profile.target_roles) >= MAX_TARGETS:
            raise ProfileLimitError("You can save up to 5 target roles.")
        if self.repo.find_role_by_name(clean_name):
            raise ProfileConflictError("That target role is already saved.")
        auto_family = self.role_classifier.classify_text(clean_name).role_family
        self.repo.db.add(
            TargetRole(
                user_profile_id=DEFAULT_PROFILE_ID,
                name=clean_name,
                priority=priority,
                auto_role_family=auto_family,
                role_family_override=None,
                role_family=auto_family,
            )
        )
        self.repo.mark_job_decisions_stale()
        self.repo.commit()
        return self.get_profile()

    def update_role(self, role_id: int, payload: TargetRoleUpdate) -> ProfileRead:
        role = self.repo.find_role(role_id)
        if role is None:
            raise ProfileNotFoundError("Target role not found.")
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes:
            clean_name = self._clean_name(changes["name"])
            if self.repo.find_role_by_name(clean_name, exclude_id=role_id):
                raise ProfileConflictError("That target role is already saved.")
            role.name = clean_name
            role.auto_role_family = self.role_classifier.classify_text(clean_name).role_family
        if "priority" in changes:
            role.priority = changes["priority"]
        if "role_family_override" in payload.model_fields_set:
            role.role_family_override = payload.role_family_override
        role.role_family = role.role_family_override or role.auto_role_family
        self.repo.mark_job_decisions_stale()
        self.repo.commit()
        return self.get_profile()

    def delete_role(self, role_id: int) -> ProfileRead:
        role = self.repo.find_role(role_id)
        if role is None:
            raise ProfileNotFoundError("Target role not found.")
        self.repo.delete(role)
        self.repo.mark_job_decisions_stale()
        self.repo.commit()
        return self.get_profile()

    def recompute_target_role_families(self) -> ProfileRead:
        profile = self.repo.get_full_profile()
        for role in profile.target_roles:
            role.auto_role_family = self.role_classifier.classify_text(role.name).role_family
            role.role_family = role.role_family_override or role.auto_role_family
        self.repo.mark_job_decisions_stale()
        self.repo.commit()
        return self.get_profile()

    def replace_resume(
        self, filename: str, extracted_text: str, structured_profile: ResumeProfile
    ) -> ProfileRead:
        profile = self.repo.get_full_profile()
        resume = profile.resume
        if resume is None:
            resume = Resume(
                user_profile_id=DEFAULT_PROFILE_ID,
                original_filename=filename,
                extracted_text=extracted_text,
                structured_profile=structured_profile.model_dump(mode="json"),
            )
            self.repo.db.add(resume)
            self.repo.db.flush()
        else:
            self._remove_old_resume_facts(resume.id)
            resume.original_filename = filename
            resume.extracted_text = extracted_text
            resume.structured_profile = structured_profile.model_dump(mode="json")
        self.repo.db.flush()
        self._create_resume_experiences(resume, structured_profile)
        self.repo.mark_job_decisions_stale(analysis_stale=True)
        self.repo.commit()
        return self.get_profile()

    def add_fact(self, experience_id: int, text: str, confirmed: bool) -> ProfileRead:
        experience = self.repo.find_experience(experience_id)
        if experience is None:
            raise ProfileNotFoundError("Experience not found.")
        experience.facts.append(
            ExperienceFact(text=self._clean_fact(text), source_type="manual", confirmed=confirmed)
        )
        self.repo.mark_job_decisions_stale(analysis_stale=True)
        self.repo.commit()
        return self.get_profile()

    def update_fact(
        self, fact_id: int, text: str | None = None, confirmed: bool | None = None
    ) -> ProfileRead:
        fact = self.repo.find_fact(fact_id)
        if fact is None:
            raise ProfileNotFoundError("Experience fact not found.")
        if text is not None:
            fact.text = self._clean_fact(text)
            fact.source_type = "manual"
        if confirmed is not None:
            fact.confirmed = confirmed
        self.repo.mark_job_decisions_stale(analysis_stale=True)
        self.repo.commit()
        return self.get_profile()

    def delete_fact(self, fact_id: int) -> ProfileRead:
        fact = self.repo.find_fact(fact_id)
        if fact is None:
            raise ProfileNotFoundError("Experience fact not found.")
        self.repo.delete(fact)
        self.repo.mark_job_decisions_stale(analysis_stale=True)
        self.repo.commit()
        return self.get_profile()

    def _remove_old_resume_facts(self, resume_id: int) -> None:
        for experience in self.repo.resume_experiences(resume_id):
            resume_facts = [fact for fact in experience.facts if fact.source_type == "resume"]
            has_manual = any(fact.source_type == "manual" for fact in experience.facts)
            for fact in resume_facts:
                self.repo.delete(fact)
            if has_manual:
                experience.source_resume_id = None
            else:
                self.repo.delete(experience)
        self.repo.db.flush()

    def _create_resume_experiences(self, resume: Resume, parsed: ResumeProfile) -> None:
        order = 0
        for item in parsed.work_experience:
            experience = Experience(
                user_profile_id=DEFAULT_PROFILE_ID,
                source_resume_id=resume.id,
                organization=item.company,
                title=item.title,
                experience_type="work",
                date_range=item.period,
                sort_order=order,
            )
            experience.facts = [
                ExperienceFact(text=text.strip(), source_type="resume", confirmed=False)
                for text in item.highlights
                if text.strip()
            ]
            self.repo.db.add(experience)
            order += 1
        for item in parsed.projects:
            experience = Experience(
                user_profile_id=DEFAULT_PROFILE_ID,
                source_resume_id=resume.id,
                organization=item.name,
                title="Project",
                experience_type="project",
                date_range=None,
                sort_order=order,
            )
            if item.description.strip():
                experience.facts = [
                    ExperienceFact(
                        text=item.description.strip(), source_type="resume", confirmed=False
                    )
                ]
            self.repo.db.add(experience)
            order += 1

    @staticmethod
    def _clean_name(value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ProfileError("Name cannot be empty.")
        return cleaned

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @staticmethod
    def _clean_fact(value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ProfileError("Experience fact is too short.")
        return cleaned
