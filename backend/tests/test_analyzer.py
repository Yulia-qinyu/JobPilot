import logging
from unittest.mock import Mock

import pytest

from app.schemas.analysis import JDRequirements, MatchAnalysis, ResumeProfile
from app.services.analyzer import JobAnalyzer


def test_analyzer_runs_three_modules_and_combines_result(
    caplog: pytest.LogCaptureFixture,
) -> None:
    profile = ResumeProfile(skills=["Roadmapping"])
    requirements = JDRequirements(role="AI Product Manager", required_skills=["Roadmapping"])
    match = MatchAnalysis(match_score=82, recommendation="Strong Apply")
    resume_parser = Mock()
    jd_parser = Mock()
    matcher = Mock()
    resume_parser.parse.return_value = profile
    jd_parser.parse.return_value = requirements
    matcher.analyze.return_value = match

    with caplog.at_level(logging.INFO):
        result = JobAnalyzer(resume_parser, jd_parser, matcher).analyze(
            "resume text", "AI Product Manager", "job description"
        )

    resume_parser.parse.assert_called_once_with("resume text")
    jd_parser.parse.assert_called_once_with("AI Product Manager", "job description")
    matcher.analyze.assert_called_once_with("AI Product Manager", profile, requirements)
    assert result.match_analysis.match_score == 82
    assert "stage=resume_parser" in caplog.text
    assert "stage=jd_parser" in caplog.text
    assert "stage=match_analyzer" in caplog.text
    assert "claude_api_calls=3" in caplog.text
    assert "claude_calls_sequential=true" in caplog.text
