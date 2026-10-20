from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Job
from app.db.session import get_db
from app.main import app
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as db:
        yield db


def setup_function() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = override_db
    with TestingSession() as db:
        ProfileRepository(db).ensure_default_profile()
        db.add(
            Job(
                id=1,
                user_profile_id=DEFAULT_PROFILE_ID,
                company="京东",
                role="产品经理",
                location="北京、上海",
                original_jd="",
                structured_jd={},
                status="Interested",
                source_content_hash="q" * 64,
            )
        )
        db.commit()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_note_api_only_creates_human_notes_and_protects_agent_notes() -> None:
    client = TestClient(app)
    created = client.post("/api/jobs/1/notes", json={"content": "HR 说本周反馈"})
    assert created.status_code == 201
    assert created.json()["author_type"] == "human"
    note_id = created.json()["id"]

    listed = client.get("/api/jobs/1/notes")
    assert listed.status_code == 200
    assert listed.json()[0]["content"] == "HR 说本周反馈"

    updated = client.patch(
        f"/api/jobs/1/notes/{note_id}", json={"content": "HR 说下周反馈"}
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "HR 说下周反馈"
    assert client.delete(f"/api/jobs/1/notes/{note_id}").status_code == 204
    assert client.get("/api/jobs/1/notes").json() == []


def test_note_api_does_not_accept_author_type() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/jobs/1/notes",
        json={"content": "冒充 Agent", "author_type": "agent"},
    )
    assert response.status_code == 201
    assert response.json()["author_type"] == "human"


def test_my_jobs_location_filter_and_latest_note_are_additive() -> None:
    client = TestClient(app)
    assert client.post(
        "/api/jobs/1/notes", json={"content": "等待下一轮通知"}
    ).status_code == 201
    matched = client.get(
        "/api/job-decisions?page=1&page_size=50&sort=recent&location=%E5%8C%97%E4%BA%AC"
    )
    assert matched.status_code == 200
    assert len(matched.json()["items"]) == 1
    assert matched.json()["items"][0]["latest_note"]["content"] == "等待下一轮通知"

    missing = client.get(
        "/api/job-decisions?page=1&page_size=50&sort=recent&location=%E6%B7%B1%E5%9C%B3"
    )
    assert missing.status_code == 200
    assert missing.json()["items"] == []
