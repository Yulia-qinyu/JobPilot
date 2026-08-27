from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.profile_repository import ProfileRepository
from app.routes.job_analysis import get_requirement_matcher
from app.routes.jobs import get_preview_matcher
from app.schemas.analysis import JDRequirements, KeyRequirement, ResumeProfile, WorkExperience
from app.schemas.fit_analysis import FitAnalysisOutput, PreparationOutput, RequirementMatchOutput
from app.schemas.job import JobCreate
from app.services.claude_client import ClaudeServiceError
from app.services.evidence_catalog import EvidenceCatalogBuilder
from app.services.job_service import JobService
from app.services.profile_service import ProfileService
from app.services.requirement_catalog import RequirementCatalogBuilder

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


def seed_case() -> tuple[int, Mock]:
    with TestingSession() as db:
        ProfileService(db).replace_resume(
            "master.docx",
            "private resume body",
            ResumeProfile(
                skills=["SQL"],
                work_experience=[
                    WorkExperience(
                        company="Acme", title="Product Manager", highlights=["Ran A/B tests."]
                    )
                ],
            ),
        )
        job = JobService(db, Settings()).create(
            JobCreate(
                company="Example",
                role="Product Manager",
                original_jd="A sufficiently detailed fictional Product Manager job description.",
                structured_jd=JDRequirements(
                    role="Product Manager",
                    key_requirements=[
                        KeyRequirement(
                            title="A/B testing",
                            explanation="Use experiments to improve product outcomes.",
                            priority="high",
                        )
                    ],
                ),
            )
        )
        requirement_id = (
            RequirementCatalogBuilder().build(job.structured_jd).requirements[0].requirement_id
        )
        evidence_id = next(
            iter(
                EvidenceCatalogBuilder()
                .build(ProfileRepository(db).get_full_profile())
                .by_catalog_id
            )
        )

    matcher = Mock()
    matcher.client.model = "test-model"
    matcher.PROMPT_VERSION = "prompt-test"
    matcher.SCHEMA_VERSION = "schema-test"
    matcher.analyze.return_value = FitAnalysisOutput(
        summary="具备实验相关证据。",
        requirement_matches=[
            RequirementMatchOutput(
                requirement_id=requirement_id,
                importance="Important",
                is_hard_requirement=False,
                hard_requirement_category="none",
                match_status="Strong",
                reason="经历事实明确提到 A/B tests。",
                confidence="High",
                evidence_source_ids=[evidence_id],
            )
        ],
        suggested_preparation=[
            PreparationOutput(
                title="准备实验案例",
                action="整理实验目标、指标和结果。",
                priority="High",
                requirement_ids=[requirement_id],
            )
        ],
    )
    return job.id, matcher


def test_pending_analyze_persist_reload_and_manual_reanalysis_use_no_parsers() -> None:
    job_id, matcher = seed_case()
    app.dependency_overrides[get_requirement_matcher] = lambda: matcher
    client = TestClient(app)

    assert client.get(f"/api/jobs/{job_id}/analysis").json()["analysis"] is None
    with (
        patch("app.services.resume_parser.ResumeParser.parse", side_effect=AssertionError),
        patch("app.services.jd_parser.JDParser.parse", side_effect=AssertionError),
    ):
        created = client.post(f"/api/jobs/{job_id}/analysis")
        reloaded = client.get(f"/api/jobs/{job_id}/analysis")
        rerun = client.post(f"/api/jobs/{job_id}/analysis")

    assert created.status_code == 200
    assert created.json()["analysis"]["match_score"] == 100
    assert created.json()["analysis"]["strengths"][0]["title"] == "A/B testing"
    decision = client.get(f"/api/jobs/{job_id}/decision").json()
    assert decision["final_decision"] == "Consider"
    assert reloaded.json()["analysis"]["id"] == created.json()["analysis"]["id"]
    assert rerun.json()["analysis"]["id"] == created.json()["analysis"]["id"]
    assert matcher.analyze.call_count == 2


def test_preview_analysis_does_not_create_or_update_workspace_jobs() -> None:
    job_id, matcher = seed_case()
    app.dependency_overrides[get_preview_matcher] = lambda: matcher
    client = TestClient(app)
    job = client.get(f"/api/jobs/{job_id}").json()
    before = client.get("/api/jobs").json()

    response = client.post(
        "/api/jobs/preview/analysis",
        json={"structured_jd": job["structured_jd"]},
    )
    after = client.get("/api/jobs").json()

    assert response.status_code == 200
    assert response.json()["match_score"] == 100
    assert before == after
    assert matcher.analyze.call_count == 1


def test_stale_analysis_is_detected_without_new_claude_call() -> None:
    job_id, matcher = seed_case()
    app.dependency_overrides[get_requirement_matcher] = lambda: matcher
    client = TestClient(app)
    assert client.post(f"/api/jobs/{job_id}/analysis").status_code == 200

    with TestingSession() as db:
        experience_id = ProfileRepository(db).get_full_profile().experiences[0].id
        ProfileService(db).add_fact(experience_id, "Confirmed new metric evidence.", True)

    state = client.get(f"/api/jobs/{job_id}/analysis").json()
    assert state["is_stale"] is True
    assert state["stale_reasons"] == ["experience_bank"]
    assert matcher.analyze.call_count == 1


@pytest.mark.parametrize(
    ("error_code", "expected_status", "expected_message"),
    [
        ("AI_SERVICE_UNAVAILABLE", 502, "AI 服务暂时不可用，请稍后重试。"),
        ("JOB_CONTENT_UNPARSEABLE", 422, "未能生成可靠的匹配分析，请重新尝试。"),
    ],
)
def test_fit_analysis_maps_claude_errors_safely(
    error_code: str, expected_status: int, expected_message: str
) -> None:
    job_id, matcher = seed_case()
    matcher.analyze.side_effect = ClaudeServiceError(
        "private resume and Claude internals", code=error_code
    )
    app.dependency_overrides[get_requirement_matcher] = lambda: matcher
    response = TestClient(app).post(f"/api/jobs/{job_id}/analysis")
    assert response.status_code == expected_status
    assert response.json()["detail"]["message"] == expected_message
    assert "private resume" not in response.text
