from threading import Lock

from fastapi import BackgroundTasks

from app.config import Settings
from app.db.session import SessionLocal
from app.services.discovery_service import DiscoveryService
from app.services.discovery_store import DiscoverySessionStore
from app.services.job_import_runner import build_source_registry


class InProcessDiscoveryRunner:
    def __init__(self, settings: Settings, store: DiscoverySessionStore):
        self.settings = settings
        self.store = store
        self._worker_lock = Lock()

    def enqueue(self, background_tasks: BackgroundTasks, session_id: str) -> None:
        background_tasks.add_task(self.run, session_id)

    def run(self, session_id: str) -> None:
        with self._worker_lock, SessionLocal() as db:
            registry = build_source_registry(self.settings, include_greenhouse=True)
            try:
                DiscoveryService(db, self.store, registry, settings=self.settings).search(
                    session_id
                )
            finally:
                registry.close()
