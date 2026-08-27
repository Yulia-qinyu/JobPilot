from decimal import ROUND_HALF_UP, Decimal

from app.schemas.fit_analysis import FitRecommendation, RequirementMatch

IMPORTANCE_WEIGHTS = {"Critical": Decimal(5), "Important": Decimal(3), "Preferred": Decimal(1)}
MATCH_VALUES = {"Strong": Decimal(1), "Partial": Decimal("0.5"), "Missing": Decimal(0)}
RECOMMENDATION_ORDER: list[FitRecommendation] = ["Skip", "Stretch", "Apply", "Strong Apply"]


class NoScorableRequirementsError(ValueError):
    pass


class MatchScoreService:
    def score(self, matches: list[RequirementMatch]) -> int:
        if not matches:
            raise NoScorableRequirementsError("No scored requirements are available.")
        denominator = sum((IMPORTANCE_WEIGHTS[item.importance] for item in matches), Decimal(0))
        if denominator <= 0:
            raise NoScorableRequirementsError("Requirement weights must be positive.")
        numerator = sum(
            (
                IMPORTANCE_WEIGHTS[item.importance] * MATCH_VALUES[item.match_status]
                for item in matches
            ),
            Decimal(0),
        )
        return int(
            ((numerator / denominator) * Decimal(100)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        )

    def recommendation(self, score: int, matches: list[RequirementMatch]) -> FitRecommendation:
        if score >= 85:
            base: FitRecommendation = "Strong Apply"
        elif score >= 70:
            base = "Apply"
        elif score >= 55:
            base = "Stretch"
        else:
            base = "Skip"

        missing_hard = [
            item for item in matches if item.is_hard_requirement and item.match_status == "Missing"
        ]
        if not missing_hard:
            return base
        if len(missing_hard) >= 2 or any(
            item.hard_requirement_category in {"eligibility", "qualification"}
            for item in missing_hard
        ):
            return "Skip"

        # One experience/other hard gap caps the result at Stretch and always downgrades it.
        base_index = RECOMMENDATION_ORDER.index(base)
        downgraded_index = max(0, base_index - 1)
        stretch_index = RECOMMENDATION_ORDER.index("Stretch")
        return RECOMMENDATION_ORDER[min(downgraded_index, stretch_index)]
