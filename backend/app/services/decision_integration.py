import logging

from sqlalchemy.orm import Session

from app.services.job_decision_service import JobDecisionService

logger = logging.getLogger(__name__)


def safe_recompute_job_decisions(db: Session, job_ids: list[int]) -> None:
    """Keep Phase 5 precompute from rolling back an accepted Phase 1–4 write."""
    if not job_ids:
        return
    try:
        JobDecisionService(db).recompute(job_ids)
    except Exception as exc:  # noqa: BLE001 - integration must remain fail-open
        db.rollback()
        logger.warning(
            "job_decision_recompute_failed job_count=%s exception_type=%s claude_calls=0",
            len(job_ids),
            type(exc).__name__,
        )
