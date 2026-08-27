from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.discovery import (
    AddDiscoveryResultResponse,
    DiscoveryContextUpdate,
    DiscoveryResultPage,
    DiscoverySessionCreate,
    DiscoverySessionRead,
)
from app.services.discovery_runner import InProcessDiscoveryRunner
from app.services.discovery_service import DiscoveryError, DiscoveryService
from app.services.discovery_store import (
    DiscoverySessionExpiredError,
    DiscoverySessionNotFoundError,
    InMemoryDiscoverySessionStore,
)
from app.services.job_import_runner import build_source_registry
from app.services.job_sources.bytedance import JobSourceError

router = APIRouter(prefix="/api/discovery/sessions", tags=["Discovery"])


@lru_cache
def get_discovery_store() -> InMemoryDiscoverySessionStore:
    settings = get_settings()
    return InMemoryDiscoverySessionStore(
        ttl_minutes=settings.discovery_ttl_minutes,
        max_sessions=settings.discovery_max_sessions,
        max_results=settings.discovery_max_results,
    )


@lru_cache
def get_discovery_runner() -> InProcessDiscoveryRunner:
    return InProcessDiscoveryRunner(get_settings(), get_discovery_store())


def discovery_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DiscoverySessionExpiredError):
        return HTTPException(
            status_code=410,
            detail={"code": "DISCOVERY_SESSION_EXPIRED", "message": "搜索会话已过期，请重新搜索。"},
        )
    if isinstance(exc, DiscoverySessionNotFoundError):
        return HTTPException(status_code=404, detail="Discovery session not found.")
    if isinstance(exc, (DiscoveryError, JobSourceError)):
        code = getattr(exc, "code", "DISCOVERY_ERROR")
        messages = {
            "UNSUPPORTED_JOB_SOURCE_URL": "当前还不支持从该招聘站批量搜索。你可以粘贴单个岗位链接或 JD。",
            "PERSONALIZATION_NOT_AVAILABLE": "个性化推荐将在后续阶段开放。",
            "DISCOVERY_RESULT_NOT_FOUND": "未找到该临时岗位。",
            "DISCOVERY_NOT_COMPLETE": "搜索尚未完成。",
            "NO_SUPPORTED_SOURCES": "已理解当前搜索条件，但对应公司的官方招聘源尚未支持批量搜索。你可以粘贴单个岗位链接或 JD。",
        }
        message = str(exc) if code == "NO_SUPPORTED_SOURCES" else messages.get(
            code, "岗位发现暂时无法完成。"
        )
        return HTTPException(
            status_code=422,
            detail={"code": code, "message": message},
        )
    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=503, detail="My Jobs 暂时无法更新。")
    return HTTPException(status_code=500, detail="岗位发现暂时不可用。")


@router.post("", response_model=DiscoverySessionRead, status_code=status.HTTP_201_CREATED)
def create_discovery_session(
    payload: DiscoverySessionCreate,
    db: Session = Depends(get_db),
    store: InMemoryDiscoverySessionStore = Depends(get_discovery_store),
) -> DiscoverySessionRead:
    settings = get_settings()
    registry = build_source_registry(settings, include_greenhouse=True)
    try:
        return DiscoveryService(db, store, registry, settings=settings).create_session(
            payload.input, payload.personalization_enabled
        )
    except (DiscoveryError, JobSourceError) as exc:
        raise discovery_error(exc) from exc
    finally:
        registry.close()


@router.patch("/{session_id}/context", response_model=DiscoverySessionRead)
def update_discovery_context(
    session_id: str,
    payload: DiscoveryContextUpdate,
    db: Session = Depends(get_db),
    store: InMemoryDiscoverySessionStore = Depends(get_discovery_store),
) -> DiscoverySessionRead:
    settings = get_settings()
    registry = build_source_registry(settings, include_greenhouse=True)
    try:
        return DiscoveryService(db, store, registry, settings=settings).update_context(
            session_id, payload
        )
    except (
        DiscoveryError,
        DiscoverySessionExpiredError,
        DiscoverySessionNotFoundError,
        JobSourceError,
    ) as exc:
        raise discovery_error(exc) from exc
    finally:
        registry.close()


@router.post("/{session_id}/search", response_model=DiscoverySessionRead, status_code=202)
def execute_discovery_search(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    store: InMemoryDiscoverySessionStore = Depends(get_discovery_store),
    runner: InProcessDiscoveryRunner = Depends(get_discovery_runner),
) -> DiscoverySessionRead:
    try:
        session = DiscoveryService(db, store).get_session(session_id)
        if session.state != "Ready":
            raise DiscoveryError("搜索会话状态不允许启动。", "DISCOVERY_INVALID_STATE")
        runner.enqueue(background_tasks, session_id)
        return session
    except (DiscoveryError, DiscoverySessionExpiredError, DiscoverySessionNotFoundError) as exc:
        raise discovery_error(exc) from exc


@router.get("/{session_id}", response_model=DiscoverySessionRead)
def get_discovery_session(
    session_id: str,
    db: Session = Depends(get_db),
    store: InMemoryDiscoverySessionStore = Depends(get_discovery_store),
) -> DiscoverySessionRead:
    try:
        return DiscoveryService(db, store).get_session(session_id)
    except (DiscoverySessionExpiredError, DiscoverySessionNotFoundError) as exc:
        raise discovery_error(exc) from exc


@router.get("/{session_id}/results", response_model=DiscoveryResultPage)
def get_discovery_results(
    session_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25),
    location: str | None = Query(default=None, max_length=120),
    company: str | None = Query(default=None, max_length=120),
    role_family: str | None = Query(default=None, max_length=40),
    relevance: str | None = Query(default=None, pattern="^(High|Medium|Low)$"),
    already_in_my_jobs: bool | None = None,
    source: str | None = Query(default=None, max_length=40),
    recruitment_type: str | None = Query(
        default=None, pattern="^(campus|experienced)$"
    ),
    include_excluded: bool = False,
    sort: str = Query(default="relevance", pattern="^(relevance|published|company)$"),
    db: Session = Depends(get_db),
    store: InMemoryDiscoverySessionStore = Depends(get_discovery_store),
) -> DiscoveryResultPage:
    if page_size not in {25, 50, 100}:
        raise HTTPException(status_code=422, detail="page_size must be 25, 50, or 100.")
    try:
        return DiscoveryService(db, store).result_page(
            session_id,
            page=page,
            page_size=page_size,
            location=location,
            company=company,
            role_family=role_family,
            relevance=relevance,
            already_in_my_jobs=already_in_my_jobs,
            source=source,
            sort=sort,
            include_excluded=include_excluded,
            recruitment_type=recruitment_type,
        )
    except (DiscoverySessionExpiredError, DiscoverySessionNotFoundError) as exc:
        raise discovery_error(exc) from exc


@router.post(
    "/{session_id}/results/{result_id}/my-job",
    response_model=AddDiscoveryResultResponse,
)
def add_discovery_result_to_my_jobs(
    session_id: str,
    result_id: str,
    db: Session = Depends(get_db),
    store: InMemoryDiscoverySessionStore = Depends(get_discovery_store),
) -> AddDiscoveryResultResponse:
    try:
        return DiscoveryService(db, store).add_to_my_jobs(session_id, result_id)
    except (
        DiscoveryError,
        DiscoverySessionExpiredError,
        DiscoverySessionNotFoundError,
        SQLAlchemyError,
        ValueError,
    ) as exc:
        db.rollback()
        raise discovery_error(exc) from exc
