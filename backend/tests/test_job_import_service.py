import logging
from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import JobAnalysis, JobDecision
from app.schemas.analysis import JDRequirements, KeyRequirement
from app.schemas.job import JobCreate, JobUpdate
from app.services.fit_analysis_service import FitAnalysisService
from app.services.job_import_service import JobImportService
from app.services.job_service import JobService
from app.services.job_sources.base import (
    ImportedJobDraft,
    SourceJobPage,
    SourceJobRecord,
    SourceSearchQuery,
)
from app.services.job_sources.bytedance import JobSourceError, SourceRecordError
from app.services.job_sources.registry import JobSourceRegistry
from app.services.requirement_catalog import RequirementCatalogBuilder


def engine():
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


def record(external_id: str, text: str = "Requirement") -> SourceJobRecord:
    return SourceJobRecord(
        source="test",
        external_job_id=external_id,
        external_job_code=f"C-{external_id}",
        title=f"Role {external_id}",
        locations=("Beijing",),
        recruitment_type="Campus",
        detail_url=f"https://jobs.example/{external_id}",
        description=f"Description {text}",
        requirements=text,
        published_date=date(2026, 8, 23),
    )


def draft(item: SourceJobRecord) -> ImportedJobDraft:
    original = f"职位描述\n{item.description}\n\n职位要求\n{item.requirements}"
    return ImportedJobDraft(
        source="test",
        external_job_id=item.external_job_id,
        external_job_code=item.external_job_code,
        company="Test Company",
        role=item.title,
        location="Beijing",
        recruitment_type="Campus",
        source_url=item.detail_url,
        original_jd=original,
        structured_jd=JDRequirements(
            role=item.title,
            company="Test Company",
            responsibilities=[item.description],
            required_skills=[item.requirements],
            key_requirements=[
                KeyRequirement(title=item.requirements, explanation=item.requirements)
            ],
        ),
        published_date=item.published_date,
        source_metadata={"normalizer_version": "test-v1"},
        source_content_hash=JobService.content_hash(original),
    )


class FakeAdapter:
    source = "test"

    def __init__(self, records: list[SourceJobRecord], fail_discovery: bool = False):
        self.records = records
        self.fail_discovery = fail_discovery

    def supports(self, _url: str) -> bool:
        return True

    def parse_search_url(self, _url: str) -> SourceSearchQuery:
        return SourceSearchQuery(
            source="test", normalized_url="https://jobs.example/search", channel="test"
        )

    def discover(self, _query):
        if self.fail_discovery:
            raise JobSourceError("page failed")
        midpoint = min(100, len(self.records))
        yield SourceJobPage(tuple(self.records[:midpoint]), len(self.records), 0)
        if len(self.records) > midpoint:
            yield SourceJobPage(tuple(self.records[midpoint:]), len(self.records), midpoint)

    def normalize(self, item):
        if not item.external_job_id:
            raise SourceRecordError("missing", "MISSING_EXTERNAL_ID")
        return draft(item)


def make_service(db: Session, adapter: FakeAdapter) -> JobImportService:
    return JobImportService(db, Settings(), JobSourceRegistry([adapter]))


def test_import_deduplicates_upstream_and_persists_120_jobs() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    records = [record(str(index)) for index in range(120)] + [record("1")]
    with Session(db_engine, expire_on_commit=False) as db:
        service = make_service(db, FakeAdapter(records))
        session_id = service.create_session("https://jobs.example/search").id
        service.run(session_id)
        result = service.get_session(session_id)
        assert result.status == "Completed"
        assert result.discovered_count == 121
        assert result.processed_count == 121
        assert result.imported_count == 120
        assert result.duplicate_count == 1
        assert result.failed_count == 0
        assert len(service.get_session_jobs(session_id).jobs) == 120
        assert db.scalar(select(func.count(JobDecision.id))) == 120

    with Session(db_engine) as reloaded:
        assert (
            len(make_service(reloaded, FakeAdapter(records)).get_session_jobs(session_id).jobs)
            == 120
        )


def test_rerun_duplicate_then_changed_source_preserves_tracker_fields() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    adapter = FakeAdapter([record("1", "Original requirement")])
    with Session(db_engine, expire_on_commit=False) as db:
        service = make_service(db, adapter)
        first = service.create_session("https://jobs.example/search").id
        service.run(first)
        job = service.get_session_jobs(first).jobs[0]
        JobService(db, Settings()).update(
            job.id,
            JobUpdate(status="Preparing", notes="Keep me", next_stage="OA"),
        )
        original_job = JobService(db, Settings()).get(job.id)
        original_jd_hash = (
            RequirementCatalogBuilder().build(original_job.structured_jd).structured_jd_hash
        )
        db.add(
            JobAnalysis(
                job_id=job.id,
                resume_hash="resume-v1",
                experience_bank_hash="experience-v1",
                structured_jd_hash=original_jd_hash,
                matcher_model="test-model",
                matcher_prompt_version="test-prompt",
                matcher_schema_version="test-schema",
                match_score=72,
                recommendation="Apply",
                summary="Existing persisted analysis",
                requirement_matches=[],
                strengths=[],
                gaps=[],
                suggested_preparation=[],
            )
        )
        db.commit()

        duplicate = service.create_session("https://jobs.example/search").id
        service.run(duplicate)
        duplicate_result = service.get_session(duplicate)
        assert duplicate_result.duplicate_count == 1
        assert duplicate_result.imported_count == 0

        adapter.records = [record("1", "Changed requirement")]
        updated = service.create_session("https://jobs.example/search").id
        service.run(updated)
        updated_result = service.get_session(updated)
        updated_job = JobService(db, Settings()).get(job.id)
        assert updated_result.updated_count == 1
        assert updated_job.status == "Preparing"
        assert updated_job.notes == "Keep me"
        assert updated_job.next_stage == "OA"
        assert updated_job.match_score is None
        assert "Changed requirement" in updated_job.original_jd
        state = FitAnalysisService(db, Settings()).get_state(job.id)
        assert state.analysis is not None
        assert state.is_stale is True
        assert "job_description" in state.stale_reasons


def test_partial_record_failure_and_page_failure_have_safe_terminal_states(caplog) -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    with Session(db_engine, expire_on_commit=False) as db:
        partial_service = make_service(
            db, FakeAdapter([record("1", "SENSITIVE_JD_MARKER"), record("")])
        )
        partial_id = partial_service.create_session("https://jobs.example/search").id
        with caplog.at_level(logging.INFO):
            partial_service.run(partial_id)
        partial = partial_service.get_session(partial_id)
        assert partial.status == "Partial"
        assert partial.imported_count == 1
        assert partial.failed_count == 1
        assert partial.failure_details[0].error_code == "MISSING_EXTERNAL_ID"
        assert "SENSITIVE_JD_MARKER" not in caplog.text

        failed_service = make_service(db, FakeAdapter([], fail_discovery=True))
        failed_id = failed_service.create_session("https://jobs.example/search").id
        failed_service.run(failed_id)
        failed = failed_service.get_session(failed_id)
        assert failed.status == "Failed"
        assert failed.error_code == "JOB_SOURCE_UNAVAILABLE"


def test_manual_null_source_jobs_are_not_subject_to_source_identity_uniqueness() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    payload = JobCreate(
        company="Manual",
        role="PM",
        original_jd="A sufficiently long manual description and requirement for testing.",
        structured_jd=JDRequirements(role="PM", company="Manual"),
    )
    with Session(db_engine) as db:
        service = JobService(db, Settings())
        first = service.create(payload)
        second = service.create(payload)
        assert first.id != second.id
        assert first.source is None and second.source is None
