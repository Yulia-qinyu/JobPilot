import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock

from app.schemas.fit_analysis import FitAnalysisPreview

PREVIEW_TTL_MINUTES = 30


@dataclass(frozen=True)
class PreviewAnalysisArtifact:
    token: str
    analysis: FitAnalysisPreview
    resume_hash: str
    experience_bank_hash: str
    structured_jd_hash: str
    matcher_model: str
    matcher_prompt_version: str
    matcher_schema_version: str
    created_at: datetime
    expires_at: datetime


class PreviewAnalysisStore:
    """Bounded process-local store for non-persistent preview promotion tokens."""

    def __init__(self, *, max_items: int = 50):
        self.max_items = max_items
        self._items: dict[str, PreviewAnalysisArtifact] = {}
        self._lock = RLock()

    def put(self, artifact: PreviewAnalysisArtifact) -> None:
        with self._lock:
            self._prune()
            if len(self._items) >= self.max_items:
                oldest = min(self._items.values(), key=lambda item: item.created_at)
                self._items.pop(oldest.token, None)
            self._items[artifact.token] = artifact

    def get(self, token: str) -> PreviewAnalysisArtifact | None:
        with self._lock:
            self._prune()
            return self._items.get(token)

    def consume(self, token: str) -> PreviewAnalysisArtifact | None:
        with self._lock:
            self._prune()
            return self._items.pop(token, None)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _prune(self) -> None:
        now = datetime.now(UTC)
        for token, item in list(self._items.items()):
            if item.expires_at <= now:
                self._items.pop(token, None)


def new_artifact(
    *, analysis: FitAnalysisPreview, resume_hash: str, experience_bank_hash: str,
    structured_jd_hash: str, matcher_model: str, matcher_prompt_version: str,
    matcher_schema_version: str,
) -> PreviewAnalysisArtifact:
    now = datetime.now(UTC)
    return PreviewAnalysisArtifact(
        token=secrets.token_urlsafe(32), analysis=analysis,
        resume_hash=resume_hash, experience_bank_hash=experience_bank_hash,
        structured_jd_hash=structured_jd_hash, matcher_model=matcher_model,
        matcher_prompt_version=matcher_prompt_version,
        matcher_schema_version=matcher_schema_version, created_at=now,
        expires_at=now + timedelta(minutes=PREVIEW_TTL_MINUTES),
    )


preview_analysis_store = PreviewAnalysisStore()
