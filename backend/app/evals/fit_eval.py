from statistics import median

from app.schemas.fit_analysis import RequirementMatch
from app.services.match_score import MatchScoreService


def evaluate_cases(cases: list[dict]) -> dict[str, float]:
    total_requirements = 0
    correct_matches = 0
    evidence_cases = 0
    correct_evidence = 0
    expected_gap_count = 0
    predicted_gap_count = 0
    correct_gap_count = 0
    cited_count = 0
    unsupported_count = 0
    stable_scores = 0
    latencies: list[float] = []

    for case in cases:
        requirements = {item["requirement_id"]: item for item in case["requirements"]}
        eligible_evidence = {item["evidence_source_id"] for item in case["evidence"]}
        expected = case["expected_matches"]
        predictions = case["prediction"]["requirement_matches"]
        predicted_by_id = {item["requirement_id"]: item for item in predictions}
        total_requirements += len(expected)
        for requirement_id, expected_item in expected.items():
            predicted = predicted_by_id.get(requirement_id)
            if predicted and predicted["match_status"] == expected_item["match_status"]:
                correct_matches += 1
            evidence_cases += 1
            if predicted and set(predicted["evidence_source_ids"]) == set(
                expected_item["evidence_source_ids"]
            ):
                correct_evidence += 1

        expected_gaps = set(case["expected_gap_requirement_ids"])
        predicted_gaps = {
            item["requirement_id"]
            for item in predictions
            if item["match_status"] in {"Partial", "Missing"}
        }
        expected_gap_count += len(expected_gaps)
        predicted_gap_count += len(predicted_gaps)
        correct_gap_count += len(expected_gaps & predicted_gaps)

        for item in predictions:
            cited_count += len(item["evidence_source_ids"])
            unsupported_count += sum(
                source_id not in eligible_evidence for source_id in item["evidence_source_ids"]
            )

        score_matches = [
            RequirementMatch(
                requirement_id=item["requirement_id"],
                requirement_text=requirements[item["requirement_id"]]["text"],
                importance=item["importance"],
                is_hard_requirement=item["is_hard_requirement"],
                hard_requirement_category=item["hard_requirement_category"],
                match_status=item["match_status"],
                reason=item["reason"],
                confidence=item["confidence"],
                evidence_sources=[],
            )
            for item in predictions
        ]
        scores = {MatchScoreService().score(score_matches) for _ in range(10)}
        stable_scores += int(len(scores) == 1)
        latencies.append(float(case.get("latency_seconds", 0)))

    case_count = len(cases)
    return {
        "requirement_matching_accuracy": correct_matches / total_requirements
        if total_requirements
        else 0,
        "evidence_accuracy": correct_evidence / evidence_cases if evidence_cases else 0,
        "gap_precision": correct_gap_count / predicted_gap_count if predicted_gap_count else 0,
        "gap_recall": correct_gap_count / expected_gap_count if expected_gap_count else 0,
        "score_stability": stable_scores / case_count if case_count else 0,
        "unsupported_evidence_rate": unsupported_count / cited_count if cited_count else 0,
        "latency_p50_seconds": median(latencies) if latencies else 0,
    }
