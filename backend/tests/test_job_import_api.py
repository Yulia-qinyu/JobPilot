from collections.abc import Generator
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routes.job_imports import get_import_runner

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as db:
        yield db


def setup_function() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = override_db


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_create_returns_202_and_progress_persists_without_running_inline() -> None:
    runner = Mock()
    app.dependency_overrides[get_import_runner] = lambda: runner
    client = TestClient(app)
    response = client.post(
        "/api/job-imports",
        json={"search_url": "https://jobs.bytedance.com/experienced/position?location=CT_11"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "Queued"
    assert payload["discovered_count"] == 0
    runner.enqueue.assert_called_once()

    reloaded = client.get(f"/api/job-imports/{payload['id']}")
    assert reloaded.status_code == 200
    assert reloaded.json()["search_url"].startswith(
        "https://jobs.bytedance.com/experienced/position"
    )
    jobs = client.get(f"/api/job-imports/{payload['id']}/jobs")
    assert jobs.status_code == 200
    assert jobs.json()["jobs"] == []


def test_invalid_source_url_is_rejected_safely() -> None:
    response = TestClient(app).post(
        "/api/job-imports", json={"search_url": "https://evil.example/jobs"}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNSUPPORTED_JOB_SOURCE_URL"
