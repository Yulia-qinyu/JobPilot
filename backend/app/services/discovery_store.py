from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Protocol

from app.schemas.discovery import DiscoveryResult, DiscoverySessionRead
from app.schemas.discovery_personalization import PersonalizedRankingInput
from app.services.job_sources.base import ImportedJobDraft


class DiscoveryStoreError(LookupError):
    pass


class DiscoverySessionNotFoundError(DiscoveryStoreError):
    pass


class DiscoverySessionExpiredError(DiscoveryStoreError):
    pass


@dataclass
class StoredDiscoverySession:
    session: DiscoverySessionRead
    results: list[DiscoveryResult] = field(default_factory=list)
    drafts: dict[str, ImportedJobDraft] = field(default_factory=dict)
    personalization_input: PersonalizedRankingInput | None = None


class DiscoverySessionStore(Protocol):
    def create(self, value: StoredDiscoverySession) -> StoredDiscoverySession: ...
    def get(self, session_id: str) -> StoredDiscoverySession: ...
    def save(self, value: StoredDiscoverySession) -> None: ...


class InMemoryDiscoverySessionStore:
    def __init__(
        self,
        *,
        ttl_minutes: int = 60,
        max_sessions: int = 20,
        max_results: int = 500,
        clock: Callable[[], datetime] | None = None,
    ):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_sessions = max_sessions
        self.max_results = max_results
        self.clock = clock or (lambda: datetime.now(UTC))
        self._sessions: dict[str, StoredDiscoverySession] = {}
        self._expired: set[str] = set()
        self._lock = RLock()

    def create(self, value: StoredDiscoverySession) -> StoredDiscoverySession:
        with self._lock:
            self._purge_expired()
            if len(self._sessions) >= self.max_sessions:
                oldest_id = min(
                    self._sessions,
                    key=lambda item: self._sessions[item].session.created_at,
                )
                self._sessions.pop(oldest_id)
                self._expired.add(oldest_id)
            self._sessions[value.session.id] = deepcopy(value)
            self._trim_tombstones()
            return deepcopy(value)

    def get(self, session_id: str) -> StoredDiscoverySession:
        with self._lock:
            self._purge_expired()
            value = self._sessions.get(session_id)
            if value is None:
                if session_id in self._expired:
                    raise DiscoverySessionExpiredError(session_id)
                raise DiscoverySessionNotFoundError(session_id)
            return deepcopy(value)

    def save(self, value: StoredDiscoverySession) -> None:
        with self._lock:
            self._purge_expired()
            if value.session.id not in self._sessions:
                if value.session.id in self._expired:
                    raise DiscoverySessionExpiredError(value.session.id)
                raise DiscoverySessionNotFoundError(value.session.id)
            value.results = value.results[: self.max_results]
            self._sessions[value.session.id] = deepcopy(value)

    def active_count(self) -> int:
        with self._lock:
            self._purge_expired()
            return len(self._sessions)

    def _purge_expired(self) -> None:
        now = self.clock()
        for session_id, value in list(self._sessions.items()):
            if value.session.expires_at <= now:
                self._sessions.pop(session_id)
                self._expired.add(session_id)
        self._trim_tombstones()

    def _trim_tombstones(self) -> None:
        while len(self._expired) > self.max_sessions * 2:
            self._expired.pop()
