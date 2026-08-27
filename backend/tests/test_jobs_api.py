from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routes.jobs import get_job_fetcher, get_job_parser
from app.schemas.analysis import JDRequirements, KeyRequirement
from app.services.claude_client import ClaudeServiceError
from app.services.job_ingestion import JobIngestionError

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as db:
        yield db


def fake_parser() -> Mock:
    parser = Mock()
    parser.client.model = "test-model"
    parser.PROMPT_VERSION = "job-jd-v3"
    parser.SCHEMA_VERSION = "jd-requirements-v3"
    parser.parse.return_value = JDRequirements(
        company="Example AI",
        role="AI Product Manager",
        location="Sydney",
        role_summary="负责 AI 产品从发现到交付。",
        key_requirements=[
            KeyRequirement(
                title="产品交付",
                explanation="推动跨职能团队交付产品。",
                priority="high",
            )
        ],
        knowledge_topics=["LLM", "SQL"],
        responsibilities=["Own roadmap"],
        required_skills=["Product strategy"],
    )
    return parser


def setup_function() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = override_db


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_paste_preview_create_update_detail_and_dashboard_persist() -> None:
    parser = fake_parser()
    app.dependency_overrides[get_job_parser] = lambda: parser
    client = TestClient(app)
    jd = (
        "某科技公司招聘 AI 产品经理，负责产品策略、跨团队交付、SQL 分析与 LLM 产品评估。"
        "候选人需要推进用户研究、路线图规划、实验设计和产品上线复盘。"
    )

    preview_response = client.post("/api/jobs/preview/jd", json={"job_description": jd})
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["structured_jd"]["role_summary"] == "负责 AI 产品从发现到交付。"
    assert preview["structured_jd"]["knowledge_topics"] == ["LLM", "SQL"]
    parser.parse.assert_called_once()

    create_response = client.post(
        "/api/jobs",
        json={**preview, "company": "Corrected Company", "role": "AI PM"},
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]
    decision_response = client.get(f"/api/jobs/{job_id}/decision")
    assert decision_response.status_code == 200
    assert decision_response.json()["final_decision"] is None

    update_response = client.patch(
        f"/api/jobs/{job_id}",
        json={"status": "Preparing", "notes": "准备作品集"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "Preparing"

    with TestClient(app) as reloaded_client:
        detail = reloaded_client.get(f"/api/jobs/{job_id}")
        dashboard = reloaded_client.get("/api/dashboard")
    assert detail.status_code == 200
    assert detail.json()["notes"] == "准备作品集"
    assert detail.json()["structured_jd"]["company"] == "Corrected Company"
    assert dashboard.json()["counts"] == {
        "total": 1,
        "applied": 0,
        "interviews": 0,
        "offers": 0,
    }
    assert parser.parse.call_count == 1


@pytest.mark.parametrize(
    ("code", "expected_status", "expected_message"),
    [
        ("AI_SERVICE_UNAVAILABLE", 502, "AI 服务暂时不可用，请稍后重试。"),
        ("JOB_CONTENT_UNPARSEABLE", 422, "未能识别该职位信息，请检查 JD 内容或稍后重试。"),
        ("AI_REQUEST_INVALID", 502, "AI 请求暂时无法完成，请稍后重试。"),
    ],
)
def test_jd_preview_maps_claude_errors_safely(
    code: str, expected_status: int, expected_message: str
) -> None:
    parser = fake_parser()
    parser.parse.side_effect = ClaudeServiceError("internal detail", code=code)
    app.dependency_overrides[get_job_parser] = lambda: parser
    response = TestClient(app).post(
        "/api/jobs/preview/jd",
        json={
            "job_description": "这是一份长度足够的虚构中文职位描述，用于验证安全错误映射，不包含真实用户信息。"
            * 2
        },
    )
    assert response.status_code == expected_status
    assert response.json()["detail"] == {"code": code, "message": expected_message}
    assert "internal detail" not in response.text


def test_url_retrieval_failure_returns_manual_paste_fallback() -> None:
    fetcher = Mock()
    fetcher.fetch.side_effect = JobIngestionError("blocked")
    app.dependency_overrides[get_job_parser] = fake_parser
    app.dependency_overrides[get_job_fetcher] = lambda: fetcher
    response = TestClient(app).post(
        "/api/jobs/preview/url", json={"url": "https://jobs.example.com/opening"}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "JOB_URL_UNREADABLE",
        "message": "无法自动读取该岗位，请手动粘贴职位描述。",
    }


def test_cors_preflight_allows_browser_job_patch() -> None:
    response = TestClient(app).options(
        "/api/jobs/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        },
    )
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]
