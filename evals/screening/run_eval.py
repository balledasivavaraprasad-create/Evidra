"""Evaluation runner for explainable screening rules benchmark (B02)."""
from __future__ import annotations

import json
from pathlib import Path

from app.contracts.models import RecordRevisionResponse
from app.screening import ScreeningEngine, get_default_criteria_version


def run_evaluation() -> dict:
    """Evaluate screening rules against benchmark test cases."""
    eval_dir = Path(__file__).resolve().parent
    fixtures_path = eval_dir / "fixtures.json"

    with open(fixtures_path, encoding="utf-8") as f:
        benchmark = json.load(f)

    engine = ScreeningEngine()
    criteria = get_default_criteria_version()

    total_cases = len(benchmark["cases"])
    correct = 0
    results = []

    for case in benchmark["cases"]:
        rec = RecordRevisionResponse.model_validate(case["record"])
        screen_result = engine.screen_record(rec, criteria)

        expected_status = case["expected_status"]
        actual_status = screen_result.status.value
        status_match = (actual_status == expected_status)

        expected_reasons = set(case.get("expected_reasons", []))
        actual_reasons = set(screen_result.reasons)
        reasons_match = expected_reasons.issubset(actual_reasons) if expected_reasons else (len(actual_reasons) == 0 or expected_status == "include")

        is_passed = status_match and reasons_match
        if is_passed:
            correct += 1

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "expected_status": expected_status,
                "actual_status": actual_status,
                "status_match": status_match,
                "expected_reasons": list(expected_reasons),
                "actual_reasons": list(actual_reasons),
                "passed": is_passed,
            }
        )

    accuracy = round(correct / total_cases, 4) if total_cases > 0 else 0.0
    return {
        "benchmark_name": benchmark["benchmark_name"],
        "total_cases": total_cases,
        "correct_predictions": correct,
        "accuracy": accuracy,
        "case_evaluations": results,
    }


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result, indent=2))
