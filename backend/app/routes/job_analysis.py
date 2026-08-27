from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.fit_analysis import FitAnalysisState
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient
from app.services.decision_integration import safe_recompute_job_decisions
from app.services.fit_analysis_service import (
    FitAnalysisError,
    FitAnalysisNormalizationError,
    FitAnalysisNotFoundError,
    FitAnalysisPrerequisiteError,
    FitAnalysisService,
)
from app.services.requirement_matcher import RequirementMatcher

router = APIRouter(prefix="/api/jobs/{job_id}/analysis", tags=["Fit Analysis"])


@lru_cache
def get_requirement_matcher() -> RequirementMatcher:
    return RequirementMatcher(ClaudeStructuredClient(get_settings()))


def service(db: Session) -> FitAnalysisService:
    return FitAnalysisService(db, get_settings())


def fit_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FitAnalysisNotFoundError):
        return HTTPException(status_code=404, detail="岗位不存在。")
    if isinstance(exc, FitAnalysisPrerequisiteError):
        message = (
            "请先在求职档案中上传主简历。"
            if "Master Resume" in str(exc)
            else "该岗位缺少可评分要求，请补充 JD 后重试。"
        )
        return HTTPException(
            status_code=409, detail={"code": "ANALYSIS_NOT_READY", "message": message}
        )
    if isinstance(exc, FitAnalysisNormalizationError):
        return HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_UNRELIABLE",
                "message": "未能生成可靠的匹配分析，请重新尝试。",
            },
        )
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=503, detail="匹配分析暂时无法保存，请稍后重试。")
    if isinstance(exc, FitAnalysisError):
        return HTTPException(status_code=422, detail="匹配分析请求无效。")
    return HTTPException(status_code=500, detail="匹配分析暂时不可用。")


def claude_error(exc: ClaudeServiceError) -> HTTPException:
    if exc.code == "JOB_CONTENT_UNPARSEABLE":
        message = "未能生成可靠的匹配分析，请重新尝试。"
        response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        message = "AI 服务暂时不可用，请稍后重试。"
        response_status = status.HTTP_502_BAD_GATEWAY
    return HTTPException(
        status_code=response_status,
        detail={"code": exc.code, "message": message},
    )


@router.get("", response_model=FitAnalysisState)
def get_fit_analysis(job_id: int, db: Session = Depends(get_db)) -> FitAnalysisState:
    try:
        return service(db).get_state(job_id)
    except (FitAnalysisError, SQLAlchemyError) as exc:
        db.rollback()
        raise fit_error(exc) from exc


@router.post("", response_model=FitAnalysisState)
def run_fit_analysis(
    job_id: int,
    db: Session = Depends(get_db),
    matcher: RequirementMatcher = Depends(get_requirement_matcher),
) -> FitAnalysisState:
    try:
        result = service(db).analyze(job_id, matcher)
        safe_recompute_job_decisions(db, [job_id])
        return result
    except ClaudeServiceError as exc:
        db.rollback()
        raise claude_error(exc) from exc
    except (FitAnalysisError, SQLAlchemyError) as exc:
        db.rollback()
        raise fit_error(exc) from exc
