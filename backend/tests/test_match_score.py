import pytest
from pydantic import ValidationError

from app.schemas.fit_analysis import RequirementMatch
from app.services.match_score import MatchScoreService, NoScorableRequirementsError


def match(
    importance: str = "Important",
    status: str = "Strong",
    *,
    hard: bool = False,
    category: str = "none",
) -> RequirementMatch:
    return RequirementMatch(
        requirement_id=f"{importance}-{status}-{category}",
        requirement_text="Requirement",
        importance=importance,
        is_hard_requirement=hard,
        hard_requirement_category=category,
        match_status=status,
        reason="Reason",
        confidence="High",
        evidence_sources=[],
    )


def test_deterministic_weighted_score_and_stability() -> None:
    service = MatchScoreService()
    matches = [
        match("Critical", "Strong"),
        match("Important", "Partial"),
        match("Preferred", "Missing"),
    ]
    assert service.score(matches) == 72
    assert {service.score(matches) for _ in range(20)} == {72}


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "Strong Apply"),
        (85, "Strong Apply"),
        (84, "Apply"),
        (70, "Apply"),
        (69, "Stretch"),
        (55, "Stretch"),
        (54, "Skip"),
        (0, "Skip"),
    ],
)
def test_recommendation_boundaries(score: int, expected: str) -> None:
    assert MatchScoreService().recommendation(score, []) == expected


def test_hard_requirement_categories_change_recommendation_not_score() -> None:
    service = MatchScoreService()
    experience_gap = match("Critical", "Missing", hard=True, category="experience")
    eligibility_gap = match("Critical", "Missing", hard=True, category="eligibility")
    other_strengths = [match("Critical", "Strong"), match("Critical", "Strong")]

    assert service.score([experience_gap, *other_strengths]) == 67
    assert service.recommendation(90, [experience_gap, *other_strengths]) == "Stretch"
    assert service.recommendation(90, [eligibility_gap, *other_strengths]) == "Skip"
    assert (
        service.recommendation(
            90, [experience_gap, match("Critical", "Missing", hard=True, category="other")]
        )
        == "Skip"
    )


def test_empty_and_invalid_requirement_edges() -> None:
    with pytest.raises(NoScorableRequirementsError):
        MatchScoreService().score([])
    with pytest.raises(ValidationError):
        match(status="Unknown")
