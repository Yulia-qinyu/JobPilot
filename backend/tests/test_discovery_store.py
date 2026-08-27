from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.discovery import (
    DiscoveryExplicitConstraints,
    DiscoverySearchContext,
    DiscoverySessionRead,
)
from app.services.discovery_store import (
    DiscoverySessionExpiredError,
    InMemoryDiscoverySessionStore,
    StoredDiscoverySession,
)


def stored(session_id: str, now: datetime, expires: datetime | None = None):
    context = DiscoverySearchContext(
        session_id=session_id,
        input_kind="bytedance_search_url",
        raw_input="https://jobs.bytedance.com/experienced/position",
        explicit_constraints=DiscoveryExplicitConstraints(),
        source_hints=["bytedance"],
        created_at=now,
        expires_at=expires or now + timedelta(hours=1),
    )
    return StoredDiscoverySession(
        session=DiscoverySessionRead(
            id=session_id,
            state="Ready",
            search_context=context,
            source="bytedance",
            created_at=now,
            expires_at=context.expires_at,
        )
    )


def test_store_create_read_expiry_and_deterministic_eviction() -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    clock_value = [now]
    store = InMemoryDiscoverySessionStore(max_sessions=2, clock=lambda: clock_value[0])
    store.create(stored("one", now))
    store.create(stored("two", now + timedelta(seconds=1)))
    store.create(stored("three", now + timedelta(seconds=2)))
    with pytest.raises(DiscoverySessionExpiredError):
        store.get("one")
    assert store.get("three").session.id == "three"

    expiring = stored("soon", now, now + timedelta(seconds=3))
    store.create(expiring)
    clock_value[0] = now + timedelta(seconds=4)
    with pytest.raises(DiscoverySessionExpiredError):
        store.get("soon")


def test_store_is_thread_safe_for_parallel_reads_and_writes() -> None:
    now = datetime.now(UTC)
    store = InMemoryDiscoverySessionStore(max_sessions=20)

    def create_and_read(index: int) -> str:
        session_id = f"session-{index}"
        store.create(stored(session_id, now + timedelta(seconds=index)))
        return store.get(session_id).session.id

    with ThreadPoolExecutor(max_workers=8) as executor:
        values = list(executor.map(create_and_read, range(20)))
    assert set(values) == {f"session-{index}" for index in range(20)}
    assert store.active_count() == 20
