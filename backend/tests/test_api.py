import logging
from io import BytesIO
from unittest.mock import Mock

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.routes.analysis import get_analyzer
from app.schemas.analysis import AnalysisResponse, JDRequirements, MatchAnalysis, ResumeProfile

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_rejects_unsupported_resume_before_api_call() -> None:
    response = client.post(
        "/api/analyze",
        files={"resume": ("resume.txt", b"resume", "text/plain")},
        data={
            "target_position": "AI Product Manager",
            "job_description": "A sufficiently long job description requiring product leadership skills.",
        },
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF and DOCX resumes are supported."


def test_analyze_returns_structured_response(caplog: pytest.LogCaptureFixture) -> None:
    document = Document()
    document.add_paragraph("Ada Lovelace — Product Manager")
    buffer = BytesIO()
    document.save(buffer)
    expected = AnalysisResponse(
        resume_profile=ResumeProfile(skills=["Product strategy"]),
        jd_requirements=JDRequirements(
            role="AI Product Manager", required_skills=["Product strategy"]
        ),
        match_analysis=MatchAnalysis(match_score=75, recommendation="Apply"),
    )
    fake_analyzer = Mock()
    fake_analyzer.analyze.return_value = expected
    app.dependency_overrides[get_analyzer] = lambda: fake_analyzer
    try:
        with caplog.at_level(logging.INFO):
            response = client.post(
                "/api/analyze",
                files={
                    "resume": (
                        "resume.docx",
                        buffer.getvalue(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={
                    "target_position": "AI Product Manager",
                    "job_description": "Lead AI product strategy and partner with engineering from discovery through launch.",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["match_analysis"] == expected.match_analysis.model_dump()
    fake_analyzer.analyze.assert_called_once()
    assert "stage=resume_file_read" in caplog.text
    assert "stage=resume_text_extraction" in caplog.text
    assert "total_elapsed_seconds=" in caplog.text
