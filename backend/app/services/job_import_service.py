import hashlib
import logging
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import JobImportSession
from app.repositories.job_import_repository import JobImportRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.schemas.job import JobListItem
from app.schemas.job_import import JobImportJobsRead, JobImportSessionRead
from app.services.decision_integration import safe_recompute_job_decisions
from app.services.job_sources.bytedance import JobSourceError, SourceRecordError
from app.services.job_sources.registry import JobSourceRegistry
from app.services.source_acquisition import SourceAcquisitionService
from app.services.workspace_job_upsert import WorkspaceJobUpsertService

logger = logging.getLogger(__name__)


class JobImportNotFoundError(ValueError):
    pass


class JobImportService:
    COMMIT_INTERVAL = 25

    def __init__(self, db: Session, settings: Settings, registry: JobSourceRegistry):
        self.db = db
        self.settings = settings
        self.registry = registry
        self.import_repo = JobImportRepository(db)
        self.job_repo = JobRepository(db)
        self.acquisition = SourceAcquisitionService()
        self.workspace = WorkspaceJobUpsertService(db)

    def create_session(self, search_url: str) -> JobImportSessionRead:
        ProfileRepository(self.db).ensure_default_profile()
        adapter = self.registry.for_url(search_url)
        query = adapter.parse_search_url(search_url)
        session = JobImportSession(
            user_profile_id=DEFAULT_PROFILE_ID,
            source=adapter.source,
            search_url=query.normalized_url,
            search_url_hash=hashlib.sha256(query.normalized_url.encode("utf-8")).hexdigest(),
            status="Queued",
            stage="Discovering",
            discovered_count=0,
            processed_count=0,
            imported_count=0,
            updated_count=0,
            duplicate_count=0,
            failed_count=0,
            result_job_ids=[],
            failure_details=[],
        )
        self.import_repo.add(session)
        self.import_repo.commit()
        self.import_repo.refresh(session)
        return JobImportSessionRead.model_validate(session)

    def get_session(self, session_id: int) -> JobImportSessionRead:
        return JobImportSessionRead.model_validate(self._session(session_id))

    def get_session_jobs(self, session_id: int) -> JobImportJobsRead:
        session = self._session(session_id)
        return JobImportJobsRead(
            session_id=session.id,
            jobs=[
                JobListItem.model_validate(job)
                for job in self.job_repo.list_by_ids(session.result_job_ids)
            ],
        )

    def run(self, session_id: int) -> None:
        started = perf_counter()
        session = self._session(session_id)
        session.status = "Running"
        session.stage = "Discovering"
        session.started_at = datetime.now(UTC)
        self.import_repo.commit()
        logger.info(
            "job_discovery_started session_id=%s source=%s status=running",
            session.id,
            session.source,
        )
        try:
            adapter = self.registry.for_url(session.search_url)
            query = adapter.parse_search_url(session.search_url)

            def page_progress(offset: int, returned: int, total: int) -> None:
                session.discovered_count += returned
                self.import_repo.commit()
                logger.info(
                    "job_discovery_page_completed session_id=%s source=%s offset=%s "
                    "returned_count=%s discovered_count=%s total_count=%s status=success",
                    session.id,
                    session.source,
                    offset,
                    returned,
                    session.discovered_count,
                    total,
                )

            discovered, upstream_duplicates = self.acquisition.discover(
                adapter, query, on_page=page_progress
            )
            session.duplicate_count += upstream_duplicates
            session.processed_count += upstream_duplicates

            session.stage = "Importing"
            self.import_repo.commit()
            for record in discovered:
                try:
                    with self.db.begin_nested():
                        draft = adapter.normalize(record)
                        result = self.workspace.upsert(draft)
                    legacy_outcome = {
                        "created": "imported",
                        "existing": "duplicate",
                        "updated": "updated",
                    }[result.outcome]
                    self._record_success(session, legacy_outcome, result.job.id)
                except (SourceRecordError, SQLAlchemyError, ValueError) as exc:
                    self._record_failure(session, record.external_job_id or None, exc)
                if session.processed_count % self.COMMIT_INTERVAL == 0:
                    self.import_repo.commit()
            session.stage = "Completed"
            session.status = "Partial" if session.failed_count else "Completed"
            session.completed_at = datetime.now(UTC)
            self.import_repo.commit()
            logger.info(
                "job_import_completed session_id=%s source=%s duration_seconds=%.3f "
                "discovered_count=%s imported_count=%s updated_count=%s duplicate_count=%s "
                "failed_count=%s claude_api_calls=0 status=%s",
                session.id,
                session.source,
                perf_counter() - started,
                session.discovered_count,
                session.imported_count,
                session.updated_count,
                session.duplicate_count,
                session.failed_count,
                session.status.lower(),
            )
            safe_recompute_job_decisions(self.db, session.result_job_ids)
        except JobSourceError as exc:
            self.db.rollback()
            session = self._session(session_id)
            session.status = "Failed"
            session.stage = "Completed"
            session.error_code = exc.code
            session.completed_at = datetime.now(UTC)
            self.import_repo.commit()
            logger.warning(
                "job_import_failed session_id=%s source=%s duration_seconds=%.3f "
                "error_code=%s exception_type=%s status=failed",
                session.id,
                session.source,
                perf_counter() - started,
                exc.code,
                type(exc).__name__,
            )
        except Exception as exc:  # noqa: BLE001 - keep the background session terminal
            self.db.rollback()
            session = self._session(session_id)
            session.status = "Failed"
            session.stage = "Completed"
            session.error_code = "JOB_IMPORT_FAILED"
            session.completed_at = datetime.now(UTC)
            self.import_repo.commit()
            logger.warning(
                "job_import_failed session_id=%s source=%s duration_seconds=%.3f "
                "error_code=JOB_IMPORT_FAILED exception_type=%s status=failed",
                session.id,
                session.source,
                perf_counter() - started,
                type(exc).__name__,
            )

    @staticmethod
    def _record_success(session: JobImportSession, outcome: str, job_id: int) -> None:
        session.processed_count += 1
        if outcome == "imported":
            session.imported_count += 1
        elif outcome == "updated":
            session.updated_count += 1
        else:
            session.duplicate_count += 1
        if job_id not in session.result_job_ids:
            session.result_job_ids = [*session.result_job_ids, job_id]

    @staticmethod
    def _record_failure(
        session: JobImportSession, external_job_id: str | None, exc: Exception
    ) -> None:
        session.processed_count += 1
        session.failed_count += 1
        code = getattr(exc, "code", "INVALID_SOURCE_JOB")
        if len(session.failure_details) < 50:
            session.failure_details = [
                *session.failure_details,
                {
                    "external_job_id": external_job_id,
                    "stage": "normalize",
                    "error_code": code,
                },
            ]

    def _session(self, session_id: int) -> JobImportSession:
        session = self.import_repo.get(session_id)
        if session is None:
            raise JobImportNotFoundError("Job import session not found.")
        return session
