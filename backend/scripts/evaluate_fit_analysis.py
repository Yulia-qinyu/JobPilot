import json
from pathlib import Path

from app.evals.fit_eval import evaluate_cases


def main() -> None:
    dataset = Path(__file__).parents[1] / "evals" / "fit_analysis_cases.json"
    cases = json.loads(dataset.read_text(encoding="utf-8"))
    print(json.dumps(evaluate_cases(cases), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
