import json
from pathlib import Path

from app.evals.fit_eval import evaluate_cases


def test_synthetic_fit_evaluation_metrics() -> None:
    dataset = Path(__file__).parents[1] / "evals" / "fit_analysis_cases.json"
    metrics = evaluate_cases(json.loads(dataset.read_text(encoding="utf-8")))
    assert metrics["requirement_matching_accuracy"] == 1
    assert metrics["evidence_accuracy"] == 1
    assert metrics["gap_precision"] == 1
    assert metrics["gap_recall"] == 1
    assert metrics["score_stability"] == 1
    assert metrics["unsupported_evidence_rate"] == 0
    assert metrics["latency_p50_seconds"] == 16
