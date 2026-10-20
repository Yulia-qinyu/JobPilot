from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job_note import JobNoteCreate, JobNoteRead, JobNoteUpdate
from app.services.job_note_service import JobNoteError, JobNoteNotFound, JobNoteService

router = APIRouter(prefix="/api/jobs/{job_id}/notes", tags=["Job Notes"])


def note_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobNoteNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, JobNoteError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=503, detail="岗位备注暂时不可用。")
    return HTTPException(status_code=500, detail="岗位备注暂时不可用。")


@router.get("", response_model=list[JobNoteRead])
def list_notes(job_id: int, db: Session = Depends(get_db)) -> list[JobNoteRead]:
    try:
        return JobNoteService(db).list_notes(job_id)
    except (JobNoteError, SQLAlchemyError) as exc:
        raise note_error(exc) from exc


@router.post("", response_model=JobNoteRead, status_code=status.HTTP_201_CREATED)
def create_note(
    job_id: int, payload: JobNoteCreate, db: Session = Depends(get_db)
) -> JobNoteRead:
    try:
        note = JobNoteService(db).create_human_note(job_id, payload.content)
        db.commit()
        db.refresh(note)
        return JobNoteRead.model_validate(note)
    except (JobNoteError, SQLAlchemyError) as exc:
        db.rollback()
        raise note_error(exc) from exc


@router.patch("/{note_id}", response_model=JobNoteRead)
def update_note(
    job_id: int,
    note_id: int,
    payload: JobNoteUpdate,
    db: Session = Depends(get_db),
) -> JobNoteRead:
    try:
        note = JobNoteService(db).update_human_note(job_id, note_id, payload.content)
        db.commit()
        db.refresh(note)
        return JobNoteRead.model_validate(note)
    except (JobNoteError, SQLAlchemyError) as exc:
        db.rollback()
        raise note_error(exc) from exc


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(job_id: int, note_id: int, db: Session = Depends(get_db)) -> None:
    try:
        JobNoteService(db).delete_human_note(job_id, note_id)
        db.commit()
    except (JobNoteError, SQLAlchemyError) as exc:
        db.rollback()
        raise note_error(exc) from exc
