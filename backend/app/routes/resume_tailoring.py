from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.resume_tailoring import (
    ResumeTailoringState,
    TailoredDraftPatch,
    TailoringPlanPatch,
)
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient
from app.services.resume_bullet_rewriter import ResumeBulletRewriter
from app.services.resume_claim_validator import ResumeClaimValidator
from app.services.resume_tailoring_service import (
    AnalysisRequiredError,
    AnalysisStaleError,
    InvalidEvidenceReferenceError,
    InvalidRequirementReferenceError,
    NoMatchableRequirementsError,
    PlanNotConfirmedError,
    ResumeTailoringError,
    ResumeTailoringService,
    TailoringNotFoundError,
    TailoringStaleError,
    UnsupportedClaimError,
)

router = APIRouter(prefix="/api/jobs/{job_id}/resume-tailoring", tags=["Resume Tailoring"])


@lru_cache
def get_rewriter() -> ResumeBulletRewriter:
    return ResumeBulletRewriter(ClaudeStructuredClient(get_settings()))


@lru_cache
def get_semantic_validator() -> ResumeClaimValidator:
    return ResumeClaimValidator(ClaudeStructuredClient(get_settings()))


def service(db: Session) -> ResumeTailoringService:
    return ResumeTailoringService(db, get_settings())


def tailoring_error(exc: Exception) -> HTTPException:
    if isinstance(exc, TailoringNotFoundError):
        return HTTPException(
            status_code=404, detail={"code": exc.code, "message": "岗位或简历优化不存在。"}
        )
    if isinstance(
        exc,
        (
            AnalysisRequiredError,
            AnalysisStaleError,
            TailoringStaleError,
            NoMatchableRequirementsError,
        ),
    ):
        messages = {
            "ANALYSIS_REQUIRED": "请先完成岗位匹配分析，再生成针对性简历。",
            "ANALYSIS_STALE": "当前岗位匹配分析已过期，请先重新分析。",
            "TAILORING_STALE": "主简历、经历事实或岗位分析已变化，请刷新优化方案。",
            "NO_MATCHABLE_REQUIREMENTS": "该岗位暂无可基于履历优化的要求。",
        }
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": messages[exc.code]},
        )
    if isinstance(exc, PlanNotConfirmedError):
        return HTTPException(
            status_code=422, detail={"code": exc.code, "message": "请先确认简历优化方案。"}
        )
    if isinstance(
        exc,
        (InvalidEvidenceReferenceError, InvalidRequirementReferenceError, UnsupportedClaimError),
    ):
        messages = {
            "INVALID_EVIDENCE_REFERENCE": "简历改写引用了无效或未授权的经历证据。",
            "INVALID_REQUIREMENT_REFERENCE": "简历改写引用了无效的岗位要求。",
            "UNSUPPORTED_CLAIM": "改写内容包含无法由当前证据支持的信息。",
        }
        return HTTPException(
            status_code=422, detail={"code": exc.code, "message": messages[exc.code]}
        )
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(
            status_code=503,
            detail={"code": "TAILORING_STORAGE_FAILED", "message": "简历优化结果暂时无法保存。"},
        )
    return HTTPException(
        status_code=422, detail={"code": "TAILORING_INVALID", "message": "简历优化请求无效。"}
    )


def ai_error(exc: ClaudeServiceError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={"code": exc.code, "message": "AI 服务暂时不可用，请稍后重试。"},
    )


@router.get("", response_model=ResumeTailoringState)
def get_tailoring(job_id: int, db: Session = Depends(get_db)) -> ResumeTailoringState:
    try:
        return service(db).get_state(job_id)
    except (ResumeTailoringError, SQLAlchemyError) as exc:
        db.rollback()
        raise tailoring_error(exc) from exc


@router.post("/plan", response_model=ResumeTailoringState)
def create_plan(job_id: int, db: Session = Depends(get_db)) -> ResumeTailoringState:
    try:
        return service(db).create_plan(job_id)
    except (ResumeTailoringError, SQLAlchemyError) as exc:
        db.rollback()
        raise tailoring_error(exc) from exc


@router.patch("/plan", response_model=ResumeTailoringState)
def patch_plan(
    job_id: int, payload: TailoringPlanPatch, db: Session = Depends(get_db)
) -> ResumeTailoringState:
    try:
        return service(db).patch_plan(job_id, payload)
    except (ResumeTailoringError, SQLAlchemyError) as exc:
        db.rollback()
        raise tailoring_error(exc) from exc


@router.post("/draft", response_model=ResumeTailoringState)
def generate_draft(
    job_id: int,
    db: Session = Depends(get_db),
    rewriter: ResumeBulletRewriter = Depends(get_rewriter),
    validator: ResumeClaimValidator = Depends(get_semantic_validator),
) -> ResumeTailoringState:
    try:
        return service(db).generate_draft(job_id, rewriter, validator)
    except ClaudeServiceError as exc:
        db.rollback()
        raise ai_error(exc) from exc
    except (ResumeTailoringError, SQLAlchemyError) as exc:
        db.rollback()
        raise tailoring_error(exc) from exc


@router.patch("/draft", response_model=ResumeTailoringState)
def edit_draft(
    job_id: int, payload: TailoredDraftPatch, db: Session = Depends(get_db)
) -> ResumeTailoringState:
    try:
        return service(db).edit_draft(job_id, payload)
    except (ResumeTailoringError, SQLAlchemyError) as exc:
        db.rollback()
        raise tailoring_error(exc) from exc


@router.post("/validate", response_model=ResumeTailoringState)
def validate_draft(
    job_id: int,
    db: Session = Depends(get_db),
    validator: ResumeClaimValidator = Depends(get_semantic_validator),
) -> ResumeTailoringState:
    try:
        return service(db).validate_edits(job_id, validator)
    except ClaudeServiceError as exc:
        db.rollback()
        raise ai_error(exc) from exc
    except (ResumeTailoringError, SQLAlchemyError) as exc:
        db.rollback()
        raise tailoring_error(exc) from exc


@router.post("/accept", response_model=ResumeTailoringState)
def accept_draft(job_id: int, db: Session = Depends(get_db)) -> ResumeTailoringState:
    try:
        return service(db).accept(job_id)
    except (ResumeTailoringError, SQLAlchemyError) as exc:
        db.rollback()
        raise tailoring_error(exc) from exc
