from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.fit_analysis import FitAnalysisPreview
from app.schemas.job import (
    JobAnalysisPreviewRequest,
    JobCreate,
    JobJdPreviewRequest,
    JobListItem,
    JobPreview,
    JobRead,
    JobUpdate,
    JobUrlPreviewRequest,
)
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient
from app.services.fit_analysis_service import (
    FitAnalysisError,
    FitAnalysisNormalizationError,
    FitAnalysisPrerequisiteError,
    FitAnalysisService,
)
from app.services.jd_parser import JDParser
from app.services.job_ingestion import JobIngestionError, JobPageFetcher
from app.services.job_service import JobNotFoundError, JobService, JobServiceError
from app.services.matcher_client import build_matcher_client
from app.services.requirement_matcher import RequirementMatcher

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

CLAUDE_ERROR_MESSAGES = {
    "AI_SERVICE_UNAVAILABLE": "AI 服务暂时不可用，请稍后重试。",
    "JOB_CONTENT_UNPARSEABLE": "未能识别该职位信息，请检查 JD 内容或稍后重试。",
    "AI_REQUEST_INVALID": "AI 请求暂时无法完成，请稍后重试。",
}


@lru_cache
def get_job_parser() -> JDParser:
    return JDParser(ClaudeStructuredClient(get_settings()))


@lru_cache
def get_job_fetcher() -> JobPageFetcher:
    return JobPageFetcher(get_settings())


@lru_cache
def get_preview_matcher() -> RequirementMatcher:
    return RequirementMatcher(build_matcher_client(get_settings()))


def service(db: Session) -> JobService:
    return JobService(db, get_settings())


def job_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, JobIngestionError):
        return HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": "无法自动读取该岗位，请手动粘贴职位描述。"},
        )
    if isinstance(exc, JobServiceError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=503, detail="Job database operation failed.")
    return HTTPException(status_code=500, detail="Unexpected job error.")


def claude_error(exc: ClaudeServiceError) -> HTTPException:
    status_code = 422 if exc.code == "JOB_CONTENT_UNPARSEABLE" else 502
    return HTTPException(
        status_code=status_code,
        detail={
            "code": exc.code,
            "message": CLAUDE_ERROR_MESSAGES.get(exc.code, "AI 服务暂时不可用，请稍后重试。"),
        },
    )


@router.post("/preview/url", response_model=JobPreview)
def preview_job_url(
    payload: JobUrlPreviewRequest,
    db: Session = Depends(get_db),
    parser: JDParser = Depends(get_job_parser),
    fetcher: JobPageFetcher = Depends(get_job_fetcher),
) -> JobPreview:
    try:
        return service(db).preview_url(payload.url, parser, fetcher)
    except ClaudeServiceError as exc:
        raise claude_error(exc) from exc
    except JobIngestionError as exc:
        raise job_error(exc) from exc


@router.post("/preview/jd", response_model=JobPreview)
def preview_job_jd(
    payload: JobJdPreviewRequest,
    db: Session = Depends(get_db),
    parser: JDParser = Depends(get_job_parser),
) -> JobPreview:
    try:
        return service(db).preview_jd(payload.job_description, parser)
    except ClaudeServiceError as exc:
        raise claude_error(exc) from exc


@router.post("/preview/analysis", response_model=FitAnalysisPreview)
def preview_job_analysis(
    payload: JobAnalysisPreviewRequest,
    db: Session = Depends(get_db),
    matcher: RequirementMatcher = Depends(get_preview_matcher),
) -> FitAnalysisPreview:
    try:
        return FitAnalysisService(db, get_settings()).analyze_preview(
            payload.structured_jd, matcher
        )
    except ClaudeServiceError as exc:
        raise claude_error(exc) from exc
    except FitAnalysisPrerequisiteError as exc:
        message = (
            "请先在求职档案中上传主简历。"
            if "Master Resume" in str(exc)
            else "该岗位缺少可评分要求，请补充 JD 后重试。"
        )
        raise HTTPException(
            status_code=409,
            detail={"code": "ANALYSIS_NOT_READY", "message": message},
        ) from exc
    except FitAnalysisNormalizationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "ANALYSIS_UNRELIABLE", "message": "未能生成可靠的匹配分析，请重试。"},
        ) from exc
    except (FitAnalysisError, SQLAlchemyError) as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="匹配分析暂时不可用。") from exc


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> JobRead:
    try:
        return service(db).create(payload)
    except (JobServiceError, SQLAlchemyError) as exc:
        db.rollback()
        raise job_error(exc) from exc


@router.get("", response_model=list[JobListItem])
def list_jobs(
    status_filter: str = Query(default="all", alias="status"),
    sort: str = Query(default="recent"),
    db: Session = Depends(get_db),
) -> list[JobListItem]:
    try:
        return service(db).list(status_filter, sort)
    except JobServiceError as exc:
        raise job_error(exc) from exc


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobRead:
    try:
        return service(db).get(job_id)
    except JobServiceError as exc:
        raise job_error(exc) from exc


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)) -> JobRead:
    try:
        return service(db).update(job_id, payload)
    except (JobServiceError, SQLAlchemyError) as exc:
        db.rollback()
        raise job_error(exc) from exc


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)) -> None:
    try:
        service(db).delete(job_id)
    except (JobServiceError, SQLAlchemyError) as exc:
        db.rollback()
        raise job_error(exc) from exc
