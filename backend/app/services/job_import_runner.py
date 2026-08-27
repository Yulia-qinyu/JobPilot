from threading import Lock

from fastapi import BackgroundTasks

from app.config import Settings
from app.db.session import SessionLocal
from app.services.job_import_service import JobImportService
from app.services.job_sources.bytedance import ByteDanceJobSource
from app.services.job_sources.greenhouse import GreenhouseJobSource
from app.services.job_sources.registry import JobSourceRegistry


def build_source_registry(
    settings: Settings, *, include_greenhouse: bool = False
) -> JobSourceRegistry:
    adapters = [ByteDanceJobSource(settings)]
    if include_greenhouse:
        adapters.append(GreenhouseJobSource(settings))
    return JobSourceRegistry(adapters)


class InProcessJobImportRunner:
    """Single-process execution boundary for the local portfolio deployment."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._worker_lock = Lock()

    def enqueue(self, background_tasks: BackgroundTasks, session_id: int) -> None:
        background_tasks.add_task(self.run, session_id)

    def run(self, session_id: int) -> None:
        with self._worker_lock, SessionLocal() as db:
            registry = build_source_registry(self.settings)
            try:
                JobImportService(db, self.settings, registry).run(session_id)
            finally:
                registry.close()
