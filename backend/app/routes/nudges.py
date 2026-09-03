from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.nudge import Nudge
from app.services.nudge_service import NudgeService

router = APIRouter(prefix="/api/nudges", tags=["Smart Nudges"])


@router.get("", response_model=list[Nudge])
def list_nudges(db: Session = Depends(get_db)) -> list[Nudge]:
    """Deterministic, strategy-aware recommendations.

    Read-only: at most three nudges, stable ordering, explainable ``reason``
    fields, an empty list is a valid response, and no LLM call is made.
    """

    return NudgeService(db, get_settings()).list_nudges()
