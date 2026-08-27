from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.job_import_repository import JobImportRepository
from app.schemas.job_decision import (
    DecisionJobPage,
    DecisionRecomputeRequest,
    DecisionRecomputeResult,
    DecisionSummary,
    EligibilityStatus,
    FinalDecision,
    JobDecisionOverride,
    JobDecisionRead,
    PreMatchDecision,
    TargetRoleFit,
)
from app.schemas.profile import RoleFamily
from app.services.job_decision_service import (
    JobDecisionError,
    JobDecisionNotFoundError,
    JobDecisionService,
)

router = APIRouter(prefix="/api/job-decisions", tags=["Job Decisions"])
job_router = APIRouter(prefix="/api/jobs/{job_id}/decision", tags=["Job Decisions"])

MatchStatus = Literal["pending", "analyzed", "stale"]
RoleFitFilter = TargetRoleFit | Literal["Target"]
DecisionFilter = PreMatchDecision | FinalDecision
DecisionSort = Literal["recent", "company", "match_score", "role_fit", "decision"]


def decision_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobDecisionNotFoundError):
        return HTTPException(status_code=404, detail="岗位判断不存在。")
    if isinstance(exc, JobDecisionError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=503, detail="岗位判断暂时无法读取，请稍后重试。")
    return HTTPException(status_code=500, detail="岗位判断暂时不可用。")


@router.get("", response_model=DecisionJobPage)
def list_job_decisions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50),
    eligibility: EligibilityStatus | None = None,
    role_family: RoleFamily | None = None,
    role_fit: RoleFitFilter | None = None,
    match_status: MatchStatus | None = None,
    decision: DecisionFilter | None = None,
    company: str | None = Query(default=None, max_length=200),
    source: str | None = Query(default=None, max_length=40),
    application_status: str | None = Query(default=None, max_length=64),
    import_session_id: int | None = Query(default=None, ge=1),
    sort: DecisionSort = "recent",
    db: Session = Depends(get_db),
) -> DecisionJobPage:
    if page_size not in {25, 50, 100}:
        raise HTTPException(status_code=422, detail="page_size must be 25, 50, or 100.")
    job_ids = None
    if import_session_id is not None:
        import_session = JobImportRepository(db).get(import_session_id)
        if import_session is None:
            raise HTTPException(status_code=404, detail="导入记录不存在。")
        job_ids = import_session.result_job_ids
    try:
        return JobDecisionService(db).page(
            page=page,
            page_size=page_size,
            eligibility=eligibility,
            role_family=role_family,
            role_fit=role_fit,
            match_status=match_status,
            decision_value=decision,
            company=company,
            source=source,
            application_status=application_status,
            job_ids=job_ids,
            sort=sort,
        )
    except (JobDecisionError, SQLAlchemyError) as exc:
        db.rollback()
        raise decision_error(exc) from exc


@router.get("/summary", response_model=DecisionSummary)
def get_decision_summary(db: Session = Depends(get_db)) -> DecisionSummary:
    try:
        return JobDecisionService(db).summary()
    except SQLAlchemyError as exc:
        db.rollback()
        raise decision_error(exc) from exc


@router.post("/recompute", response_model=DecisionRecomputeResult)
def recompute_decisions(
    payload: DecisionRecomputeRequest, db: Session = Depends(get_db)
) -> DecisionRecomputeResult:
    try:
        return JobDecisionService(db).recompute(payload.job_ids)
    except (JobDecisionError, SQLAlchemyError) as exc:
        db.rollback()
        raise decision_error(exc) from exc


@job_router.get("", response_model=JobDecisionRead)
def get_job_decision(job_id: int, db: Session = Depends(get_db)) -> JobDecisionRead:
    try:
        return JobDecisionService(db).get(job_id)
    except (JobDecisionError, SQLAlchemyError) as exc:
        db.rollback()
        raise decision_error(exc) from exc


@job_router.patch("", response_model=JobDecisionRead)
def update_job_decision(
    job_id: int,
    payload: JobDecisionOverride,
    db: Session = Depends(get_db),
) -> JobDecisionRead:
    try:
        return JobDecisionService(db).update_overrides(job_id, payload)
    except (JobDecisionError, SQLAlchemyError) as exc:
        db.rollback()
        raise decision_error(exc) from exc
