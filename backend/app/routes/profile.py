from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.profile import (
    CandidateIdentityUpdate,
    FactCreate,
    FactUpdate,
    LocationUpdate,
    NameCreate,
    ProfileRead,
    TargetRoleCreate,
    TargetRoleUpdate,
)
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient
from app.services.file_extractor import FileExtractionError, extract_resume_text
from app.services.profile_service import (
    ProfileConflictError,
    ProfileError,
    ProfileLimitError,
    ProfileNotFoundError,
    ProfileService,
)
from app.services.resume_parser import ResumeParser

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@lru_cache
def get_resume_parser() -> ResumeParser:
    return ResumeParser(ClaudeStructuredClient(get_settings()))


def service(db: Session) -> ProfileService:
    return ProfileService(db)


def profile_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProfileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (ProfileConflictError, ProfileLimitError)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ProfileError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=503, detail="Profile database operation failed.")
    return HTTPException(status_code=500, detail="Unexpected profile error.")


@router.get("", response_model=ProfileRead)
def get_profile(db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).get_profile()
    except SQLAlchemyError as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.put("/location", response_model=ProfileRead)
def update_location(payload: LocationUpdate, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).update_location(payload.preferred_location)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.put("/identity", response_model=ProfileRead)
def update_candidate_identity(
    payload: CandidateIdentityUpdate, db: Session = Depends(get_db)
) -> ProfileRead:
    try:
        return service(db).update_candidate_identity(
            payload.candidate_type, payload.graduation_year
        )
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.post("/resume", response_model=ProfileRead)
def upload_master_resume(
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
    parser: ResumeParser = Depends(get_resume_parser),
) -> ProfileRead:
    settings = get_settings()
    filename = resume.filename or ""
    if Path(filename).suffix.lower() not in {".pdf", ".docx"}:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX resumes are supported.")
    content = resume.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Resume must be 10 MB or smaller.")
    try:
        extracted_text = extract_resume_text(filename, content)
        parsed = parser.parse(extracted_text)
        return service(db).replace_resume(filename, extracted_text, parsed)
    except FileExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.post("/companies", response_model=ProfileRead)
def add_company(payload: NameCreate, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).add_company(payload.name)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.put("/companies/{company_id}", response_model=ProfileRead)
def update_company(
    company_id: int, payload: NameCreate, db: Session = Depends(get_db)
) -> ProfileRead:
    try:
        return service(db).update_company(company_id, payload.name)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.delete("/companies/{company_id}", response_model=ProfileRead)
def delete_company(company_id: int, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).delete_company(company_id)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.post("/roles", response_model=ProfileRead)
def add_role(payload: TargetRoleCreate, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).add_role(payload.name, payload.priority)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.put("/roles/{role_id}", response_model=ProfileRead)
def update_role(
    role_id: int, payload: TargetRoleUpdate, db: Session = Depends(get_db)
) -> ProfileRead:
    try:
        return service(db).update_role(role_id, payload)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.delete("/roles/{role_id}", response_model=ProfileRead)
def delete_role(role_id: int, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).delete_role(role_id)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.post("/experiences/{experience_id}/facts", response_model=ProfileRead)
def add_fact(experience_id: int, payload: FactCreate, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).add_fact(experience_id, payload.text, payload.confirmed)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.put("/facts/{fact_id}", response_model=ProfileRead)
def update_fact(fact_id: int, payload: FactUpdate, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).update_fact(fact_id, payload.text, payload.confirmed)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc


@router.delete("/facts/{fact_id}", response_model=ProfileRead)
def delete_fact(fact_id: int, db: Session = Depends(get_db)) -> ProfileRead:
    try:
        return service(db).delete_fact(fact_id)
    except (ProfileError, SQLAlchemyError) as exc:
        db.rollback()
        raise profile_error(exc) from exc
