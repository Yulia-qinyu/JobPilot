from unittest.mock import Mock

from app.schemas.analysis import JDRequirements, JDRequirementsOutput, MatchAnalysis, ResumeProfile
from app.services.matcher import Matcher


def test_matcher_requests_simplified_chinese_without_changing_recommendation_enum() -> None:
    client = Mock()
    client.generate.return_value = MatchAnalysis(match_score=70, recommendation="Apply")

    result = Matcher(client).analyze(
        "AI Product Manager",
        ResumeProfile(skills=["Python"]),
        JDRequirements(role="AI Product Manager", required_skills=["Python"]),
    )

    prompt = client.generate.call_args.kwargs["prompt"]
    assert "Write every user-facing string in Simplified Chinese" in prompt
    assert "Keep the recommendation field" in prompt
    assert "Merge obviously duplicated or highly overlapping gaps" in prompt
    assert result.recommendation == "Apply"


def test_jd_parser_prompt_requests_non_personalized_quick_overview() -> None:
    from app.services.jd_parser import JDParser

    client = Mock()
    client.generate.return_value = JDRequirementsOutput(
        role="AI Product Manager",
        company="",
        location="",
        recruitment_type="",
        published_date="",
        role_summary="负责 AI 产品规划与交付。",
        key_requirements=[],
        knowledge_topics=["LLM"],
        responsibilities=[],
        required_skills=[],
        preferred_skills=[],
        ai_requirements=[],
        product_requirements=[],
        technical_requirements=[],
        domain_requirements=[],
    )
    result = JDParser(client).parse(None, "A sufficiently detailed fictional job description.")
    prompt = client.generate.call_args.kwargs["prompt"]
    assert client.generate.call_args.kwargs["output_model"] is JDRequirementsOutput
    assert "JD Quick Overview" in prompt
    assert "Do not compare against a resume" in prompt
    assert "Never invent" in prompt
    assert result.role == "AI Product Manager"
    assert result.company is None
    assert result.knowledge_topics == ["LLM"]
