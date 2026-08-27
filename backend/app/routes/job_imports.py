from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.job_import import JobImportCreate, JobImportJobsRead, JobImportSessionRead
from app.services.job_import_runner import InProcessJobImportRunner, build_source_registry
from app.services.job_import_service import JobImportNotFoundError, JobImportService
from app.services.job_sources.bytedance import JobSourceError

router = APIRouter(prefix="/api/job-imports", tags=["Job Imports"])


@lru_cache
def get_import_runner() -> InProcessJobImportRunner:
    return InProcessJobImportRunner(get_settings())


def service(db: Session) -> JobImportService:
    settings = get_settings()
    return JobImportService(db, settings, build_source_registry(settings))


def import_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobImportNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, JobSourceError):
        messages = {
            "UNSUPPORTED_JOB_SOURCE_URL": "目前仅支持 ByteDance 社招或校招搜索结果 URL。",
            "JOB_SOURCE_RESULT_TOO_LARGE": "搜索结果过多，请先在招聘官网进一步缩小筛选范围。",
        }
        return HTTPException(
            status_code=422,
            detail={
                "code": exc.code,
                "message": messages.get(exc.code, "无法读取该招聘搜索结果。"),
            },
        )
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=503, detail="Job import database operation failed.")
    return HTTPException(status_code=500, detail="Unexpected job import error.")


@router.post("", response_model=JobImportSessionRead, status_code=status.HTTP_202_ACCEPTED)
def create_import(
    payload: JobImportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    runner: InProcessJobImportRunner = Depends(get_import_runner),
) -> JobImportSessionRead:
    try:
        result = service(db).create_session(payload.search_url)
        runner.enqueue(background_tasks, result.id)
        return result
    except (JobSourceError, SQLAlchemyError) as exc:
        db.rollback()
        raise import_error(exc) from exc


@router.get("/{session_id}", response_model=JobImportSessionRead)
def get_import(session_id: int, db: Session = Depends(get_db)) -> JobImportSessionRead:
    try:
        return service(db).get_session(session_id)
    except JobImportNotFoundError as exc:
        raise import_error(exc) from exc


@router.get("/{session_id}/jobs", response_model=JobImportJobsRead)
def get_import_jobs(session_id: int, db: Session = Depends(get_db)) -> JobImportJobsRead:
    try:
        return service(db).get_session_jobs(session_id)
    except JobImportNotFoundError as exc:
        raise import_error(exc) from exc
