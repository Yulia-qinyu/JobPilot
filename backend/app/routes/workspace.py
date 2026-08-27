from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workspace import (
    ApplicationStatusCreate,
    ApplicationStatusDeleteRequest,
    ApplicationStatusDeleteResult,
    ApplicationStatusRead,
    ApplicationStatusUpdate,
    PlanItemCreate,
    PlanItemRead,
    PlanItemUpdate,
    StrategyRead,
    StrategyUpdate,
)
from app.services.workspace_service import (
    WorkspaceConflictError,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceService,
)

router = APIRouter(prefix="/api/workspace", tags=["Application Workspace"])


def service(db: Session) -> WorkspaceService:
    return WorkspaceService(db)


def workspace_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkspaceNotFoundError):
        return HTTPException(404, detail=str(exc))
    if isinstance(exc, WorkspaceConflictError):
        return HTTPException(409, detail=str(exc))
    if isinstance(exc, WorkspaceError):
        return HTTPException(422, detail=str(exc))
    return HTTPException(503, detail="Workspace operation failed.")


@router.get("/strategy", response_model=StrategyRead)
def get_strategy(db: Session = Depends(get_db)) -> StrategyRead:
    return service(db).get_strategy()


@router.patch("/strategy", response_model=StrategyRead)
def update_strategy(payload: StrategyUpdate, db: Session = Depends(get_db)) -> StrategyRead:
    try:
        return service(db).update_strategy(payload.job_search_strategy)
    except SQLAlchemyError as exc:
        db.rollback(); raise workspace_error(exc) from exc


@router.get("/application-statuses", response_model=list[ApplicationStatusRead])
def list_statuses(db: Session = Depends(get_db)) -> list[ApplicationStatusRead]:
    return service(db).list_statuses()


@router.post("/application-statuses", response_model=ApplicationStatusRead, status_code=status.HTTP_201_CREATED)
def create_status(payload: ApplicationStatusCreate, db: Session = Depends(get_db)) -> ApplicationStatusRead:
    try: return service(db).create_status(payload)
    except (WorkspaceError, SQLAlchemyError) as exc: db.rollback(); raise workspace_error(exc) from exc


@router.patch("/application-statuses/{status_id}", response_model=ApplicationStatusRead)
def update_status(status_id: int, payload: ApplicationStatusUpdate, db: Session = Depends(get_db)) -> ApplicationStatusRead:
    try: return service(db).update_status(status_id, payload)
    except (WorkspaceError, SQLAlchemyError) as exc: db.rollback(); raise workspace_error(exc) from exc


@router.delete("/application-statuses/{status_id}", response_model=ApplicationStatusDeleteResult)
def delete_status(status_id: int, payload: ApplicationStatusDeleteRequest = Body(default=ApplicationStatusDeleteRequest()), db: Session = Depends(get_db)) -> ApplicationStatusDeleteResult:
    try: return service(db).delete_status(status_id, payload.migrate_to_status_id)
    except (WorkspaceError, SQLAlchemyError) as exc: db.rollback(); raise workspace_error(exc) from exc


@router.get("/plan-items", response_model=list[PlanItemRead])
def list_plans(db: Session = Depends(get_db)) -> list[PlanItemRead]:
    return service(db).list_plans()


@router.post("/plan-items", response_model=PlanItemRead, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanItemCreate, db: Session = Depends(get_db)) -> PlanItemRead:
    try: return service(db).create_plan(payload)
    except (WorkspaceError, SQLAlchemyError) as exc: db.rollback(); raise workspace_error(exc) from exc


@router.patch("/plan-items/{plan_id}", response_model=PlanItemRead)
def update_plan(plan_id: int, payload: PlanItemUpdate, db: Session = Depends(get_db)) -> PlanItemRead:
    try: return service(db).update_plan(plan_id, payload)
    except (WorkspaceError, SQLAlchemyError) as exc: db.rollback(); raise workspace_error(exc) from exc


@router.delete("/plan-items/{plan_id}", status_code=204)
def delete_plan(plan_id: int, db: Session = Depends(get_db)) -> None:
    try: service(db).delete_plan(plan_id)
    except (WorkspaceError, SQLAlchemyError) as exc: db.rollback(); raise workspace_error(exc) from exc
