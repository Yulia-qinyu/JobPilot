from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.planning import (
    AddAdviceToPlanRequest,
    PlanningGenerateRequest,
    PlanningTodayRead,
)
from app.schemas.workspace import PlanItemRead
from app.services.claude_client import ClaudeStructuredClient
from app.services.planning_service import (
    PlanningError,
    PlanningNotFoundError,
    PlanningService,
)
from app.services.workspace_service import WorkspaceError

router = APIRouter(prefix="/api/planning", tags=["Application Planning Agent"])


def planning_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PlanningNotFoundError):
        return HTTPException(404, detail=str(exc))
    if isinstance(exc, (PlanningError, WorkspaceError)):
        return HTTPException(422, detail=str(exc))
    return HTTPException(503, detail="Planning operation failed.")


@router.get("/today", response_model=PlanningTodayRead)
def get_today(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> PlanningTodayRead:
    return PlanningService(db, settings).get_today()


@router.post("/today", response_model=PlanningTodayRead)
def generate_today(
    payload: PlanningGenerateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlanningTodayRead:
    try:
        return PlanningService(db, settings).generate(
            payload, ClaudeStructuredClient(settings)
        )
    except (PlanningError, WorkspaceError, SQLAlchemyError) as exc:
        db.rollback()
        raise planning_error(exc) from exc


@router.post(
    "/snapshots/{snapshot_id}/items/{item_id}/add-to-plan",
    response_model=PlanItemRead,
)
def add_advice_to_plan(
    snapshot_id: int,
    item_id: str,
    payload: AddAdviceToPlanRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlanItemRead:
    try:
        return PlanningService(db, settings).add_to_plan(snapshot_id, item_id, payload)
    except (PlanningError, WorkspaceError, SQLAlchemyError) as exc:
        db.rollback()
        raise planning_error(exc) from exc
