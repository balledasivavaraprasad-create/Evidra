"""Unified evaluation runner for Evidra deduplication and screening algorithms (B03).

Computes comprehensive metrics:
- Confusion matrix (TP, FP, FN, TN)
- Precision, Recall, Specificity, Balanced Accuracy, and Macro-F1
- Abstention / Maybe rate
- Explanation reason completeness
- Generates reproducible results summary and updates evals/manifest.json
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.contracts.models import RecordRevisionResponse
from app.dedup import find_candidate_pairs
from app.screening import ScreeningEngine, get_default_criteria_version
from tests.fixtures.synthetic_records import ALL_SYNTHETIC_RECORDS


def compute_file_hash(path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def evaluate_deduplication(evals_dir: Path) -> dict[str, Any]:
    """Run deduplication benchmark evaluation."""
    bench_file = evals_dir / "dedup" / "benchmark.json"
    with open(bench_file, encoding="utf-8") as f:
        benchmark = json.load(f)

    records_by_id = {r["id"]: RecordRevisionResponse.model_validate(r) for r in ALL_SYNTHETIC_RECORDS}
    records_list = list(records_by_id.values())
    proposals = find_candidate_pairs(records_list)

    proposed_pairs = set()
    for p in proposals:
        proposed_pairs.add((p.record_id_a, p.record_id_b))
        proposed_pairs.add((p.record_id_b, p.record_id_a))

    tp = fp = fn = tn = 0
    study_vs_paper_false_merges = 0

    for item in benchmark["pairs"]:
        ra, rb = item["record_a"], item["record_b"]
        gt_dup = item["is_duplicate_paper"]
        is_proposed = (ra, rb) in proposed_pairs or (rb, ra) in proposed_pairs

        if gt_dup and is_proposed:
            tp += 1
        elif not gt_dup and is_proposed:
            fp += 1
            if item.get("is_same_study", False):
                study_vs_paper_false_merges += 1
        elif gt_dup and not is_proposed:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    balanced_acc = (recall + specificity) / 2.0

    return {
        "benchmark_file": "evals/dedup/benchmark.json",
        "benchmark_sha256": compute_file_hash(bench_file),
        "total_pairs": len(benchmark["pairs"]),
        "confusion_matrix": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "f1_score": round(f1, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "study_vs_paper_false_merges": study_vs_paper_false_merges,
    }


def evaluate_screening(evals_dir: Path) -> dict[str, Any]:
    """Run screening benchmark evaluation."""
    fixtures_file = evals_dir / "screening" / "fixtures.json"
    with open(fixtures_file, encoding="utf-8") as f:
        benchmark = json.load(f)

    engine = ScreeningEngine()
    criteria = get_default_criteria_version()

    total_cases = len(benchmark["cases"])
    status_matches = 0
    reason_matches = 0
    maybe_count = 0

    status_counts = {"include": 0, "exclude": 0, "maybe": 0}

    for case in benchmark["cases"]:
        rec = RecordRevisionResponse.model_validate(case["record"])
        res = engine.screen_record(rec, criteria)

        actual_status = res.status.value
        status_counts[actual_status] = status_counts.get(actual_status, 0) + 1
        if actual_status == "maybe":
            maybe_count += 1

        expected_status = case["expected_status"]
        if actual_status == expected_status:
            status_matches += 1

        expected_reasons = set(case.get("expected_reasons", []))
        actual_reasons = set(res.reasons)
        if expected_reasons.issubset(actual_reasons) if expected_reasons else (len(actual_reasons) == 0 or expected_status == "include"):
            reason_matches += 1

    accuracy = status_matches / total_cases if total_cases > 0 else 0.0
    reason_completeness = reason_matches / total_cases if total_cases > 0 else 0.0
    maybe_rate = maybe_count / total_cases if total_cases > 0 else 0.0

    return {
        "benchmark_file": "evals/screening/fixtures.json",
        "benchmark_sha256": compute_file_hash(fixtures_file),
        "total_cases": total_cases,
        "status_distribution": status_counts,
        "accuracy": round(accuracy, 4),
        "reason_completeness": round(reason_completeness, 4),
        "maybe_rate": round(maybe_rate, 4),
    }


def main():
    root = Path(__file__).resolve().parent.parent
    evals_dir = root / "evals"

    dedup_results = evaluate_deduplication(evals_dir)
    screening_results = evaluate_screening(evals_dir)

    manifest = {
        "manifest_version": "1.0.0",
        "generated_by": "dev-B (T2 Deduplication and Screening Owner)",
        "platform_environment": "macOS / Linux, Python 3.12, SQLite 3.x",
        "algorithms": {
            "dedup": {
                "method_version": "dedup-rules-v1.0.0",
                "evaluation": dedup_results,
            },
            "screening": {
                "method_version": "screening-rules-v1.0.0",
                "evaluation": screening_results,
            },
        },
    }

    manifest_path = evals_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("Evaluations completed successfully.")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
