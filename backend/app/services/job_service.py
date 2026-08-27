import hashlib

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ApplicationStatusDefinition, Job
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.analysis import JDRequirements
from app.schemas.job import (
    DashboardCounts,
    DashboardProfile,
    DashboardRead,
    JobCreate,
    JobListItem,
    JobPreview,
    JobRead,
    JobUpdate,
)
from app.schemas.profile import TargetCompanyRead, TargetRoleRead
from app.services.activity_service import ActivityService
from app.services.decision_integration import safe_recompute_job_decisions
from app.services.fit_analysis_service import FitAnalysisService
from app.services.jd_parser import JDParser
from app.services.job_ingestion import JobPageFetcher
from app.services.workspace_service import WorkspaceService


class JobServiceError(ValueError):
    pass


class JobNotFoundError(JobServiceError):
    pass


FILTER_STATUSES: dict[str, list[str] | None] = {
    "all": None,
    "Interested": ["Interested"],
    "Preparing": ["Preparing"],
    "Applied": ["Applied"],
    "OA": ["OA"],
    "Interview": ["Interview", "Final Interview"],
    "Offer": ["Offer"],
}


class JobService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.repo = JobRepository(db)

    def preview_jd(
        self,
        jd_text: str,
        parser: JDParser,
        *,
        source_url: str | None = None,
    ) -> JobPreview:
        original_jd = jd_text.strip()
        parsed = parser.parse(None, original_jd)
        return JobPreview(
            company=parsed.company,
            role=parsed.role,
            location=parsed.location,
            recruitment_type=parsed.recruitment_type,
            published_date=parsed.published_date,
            source_url=source_url,
            original_jd=original_jd,
            structured_jd=parsed,
            parser_model=parser.client.model,
            parser_prompt_version=parser.PROMPT_VERSION,
            parser_schema_version=parser.SCHEMA_VERSION,
            source_content_hash=self.content_hash(original_jd),
        )

    def preview_url(
        self,
        url: str,
        parser: JDParser,
        fetcher: JobPageFetcher,
    ) -> JobPreview:
        final_url, text = fetcher.fetch(url)
        return self.preview_jd(text, parser, source_url=final_url)

    def create(self, payload: JobCreate) -> JobRead:
        ProfileRepository(self.db).ensure_default_profile()
        company = self._required(payload.company, "Company")
        role = self._required(payload.role, "Role")
        original_jd = payload.original_jd.strip()
        structured = self._confirmed_structure(payload, company, role)
        content_hash = self.content_hash(original_jd)
        duplicate = (
            self.repo.get_manual_duplicate(
                source_url=self._optional(payload.source_url),
                content_hash=content_hash,
                company=company,
                role=role,
            )
            if payload.source_content_hash == content_hash
            else None
        )
        if duplicate is not None:
            return JobRead.model_validate(duplicate)
        statuses = WorkspaceService(self.db).ensure_default_statuses()
        default_status = next((item for item in statuses if item.legacy_status == payload.status), None)
        job = Job(
            user_profile_id=DEFAULT_PROFILE_ID,
            company=company,
            role=role,
            location=self._optional(payload.location),
            recruitment_type=self._optional(payload.recruitment_type),
            source_url=self._optional(payload.source_url),
            original_jd=original_jd,
            structured_jd=structured.model_dump(mode="json"),
            published_date=payload.published_date,
            status=payload.status,
            application_status_id=default_status.id if default_status else None,
            match_score=None,
            recommendation=None,
            parser_model=payload.parser_model or self.settings.claude_model,
            parser_prompt_version=payload.parser_prompt_version or JDParser.PROMPT_VERSION,
            parser_schema_version=payload.parser_schema_version or JDParser.SCHEMA_VERSION,
            source_content_hash=content_hash,
        )
        self.repo.add(job)
        promoted = False
        if payload.preview_artifact_token:
            promoted = FitAnalysisService(self.db, self.settings).promote_preview(
                job, payload.preview_artifact_token
            ) is not None
        ActivityService(self.db).record("job_added", job_id=job.id, metadata={"source": "analysis"})
        if promoted:
            ActivityService(self.db).record("job_analyzed", job_id=job.id, metadata={"source": "preview_promotion"})
        self.repo.commit()
        self.repo.refresh(job)
        safe_recompute_job_decisions(self.db, [job.id])
        return JobRead.model_validate(job).model_copy(update={"analysis_promoted": promoted})

    def delete(self, job_id: int) -> None:
        job = self.repo.get(job_id)
        if job is None:
            raise JobNotFoundError("Job not found.")
        ActivityService(self.db).record("job_deleted", job_id=job.id, metadata={"company": job.company, "role": job.role})
        self.repo.delete(job)
        self.repo.commit()

    def get(self, job_id: int) -> JobRead:
        job = self.repo.get(job_id)
        if job is None:
            raise JobNotFoundError("Job not found.")
        return JobRead.model_validate(job)

    def list(self, status_filter: str = "all", sort: str = "recent") -> list[JobListItem]:
        if status_filter not in FILTER_STATUSES:
            raise JobServiceError("Unsupported job status filter.")
        if sort not in {"recent", "company", "match_score"}:
            raise JobServiceError("Unsupported job sort.")
        return [
            JobListItem.model_validate(job)
            for job in self.repo.list(FILTER_STATUSES[status_filter], sort)
        ]

    def update(self, job_id: int, payload: JobUpdate) -> JobRead:
        job = self.repo.get(job_id)
        if job is None:
            raise JobNotFoundError("Job not found.")
        changes = payload.model_dump(exclude_unset=True)
        old_status = job.status
        if "company" in changes:
            job.company = self._required(changes["company"], "Company")
        if "role" in changes:
            job.role = self._required(changes["role"], "Role")
        for field in (
            "location",
            "recruitment_type",
            "next_stage",
            "notes",
        ):
            if field in changes:
                setattr(job, field, self._optional(changes[field]))
        for field in ("published_date", "status", "application_date", "interview_date"):
            if field in changes:
                setattr(job, field, changes[field])
        if "application_status_id" in changes:
            definition = self.db.get(ApplicationStatusDefinition, changes["application_status_id"])
            if definition is None or definition.user_profile_id != DEFAULT_PROFILE_ID or not definition.is_active:
                raise JobServiceError("Application status not found.")
            job.application_status_id = definition.id
            if definition.legacy_status:
                job.status = definition.legacy_status
        if "structured_jd" in changes and payload.structured_jd is not None:
            job.structured_jd = payload.structured_jd.model_dump(mode="json")

        structured = JDRequirements.model_validate(job.structured_jd)
        structured = structured.model_copy(
            update={
                "company": job.company,
                "role": job.role,
                "location": job.location,
                "recruitment_type": job.recruitment_type,
                "published_date": job.published_date,
            }
        )
        job.structured_jd = structured.model_dump(mode="json")
        if job.status != old_status or "application_status_id" in changes:
            ActivityService(self.db).record(
                "application_status_changed", job_id=job.id,
                metadata={"from_status": old_status, "to_status": job.status,
                          "application_status_id": job.application_status_id},
            )
        if "interview_date" in changes:
            ActivityService(self.db).record("interview_scheduled", job_id=job.id, metadata={"date": str(job.interview_date) if job.interview_date else None})
        self.repo.commit()
        self.repo.refresh(job)
        safe_recompute_job_decisions(self.db, [job.id])
        return JobRead.model_validate(job)

    def dashboard(self) -> DashboardRead:
        profile = ProfileRepository(self.db).get_full_profile()
        return DashboardRead(
            counts=DashboardCounts(**self.repo.counts()),
            profile=DashboardProfile(
                preferred_location=profile.preferred_location,
                target_companies=[
                    TargetCompanyRead.model_validate(item) for item in profile.target_companies
                ],
                target_roles=[TargetRoleRead.model_validate(item) for item in profile.target_roles],
            ),
            jobs=[JobListItem.model_validate(job) for job in self.repo.list(limit=8)],
        )

    @staticmethod
    def content_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _required(value: str | None, label: str) -> str:
        cleaned = " ".join((value or "").split())
        if not cleaned:
            raise JobServiceError(f"{label} is required.")
        return cleaned

    @staticmethod
    def _optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @staticmethod
    def _confirmed_structure(payload: JobCreate, company: str, role: str) -> JDRequirements:
        return payload.structured_jd.model_copy(
            update={
                "company": company,
                "role": role,
                "location": JobService._optional(payload.location),
                "recruitment_type": JobService._optional(payload.recruitment_type),
                "published_date": payload.published_date,
            }
        )
