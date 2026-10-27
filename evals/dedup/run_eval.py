"""Evaluation script for deterministic deduplication benchmark (B01)."""
from __future__ import annotations

import json
from pathlib import Path

from app.contracts.models import RecordRevisionResponse
from app.dedup import find_candidate_pairs
from tests.fixtures.synthetic_records import ALL_SYNTHETIC_RECORDS


def run_evaluation() -> dict:
    """Run evaluation against benchmark.json gold standard."""
    eval_dir = Path(__file__).resolve().parent
    benchmark_path = eval_dir / "benchmark.json"

    with open(benchmark_path, encoding="utf-8") as f:
        benchmark = json.load(f)

    # Index records
    records_by_id = {r["id"]: RecordRevisionResponse.model_validate(r) for r in ALL_SYNTHETIC_RECORDS}

    # Generate proposals for all synthetic records
    records_list = list(records_by_id.values())
    proposals = find_candidate_pairs(records_list)

    # Proposed pairs set (symmetric)
    proposed_pairs = set()
    for p in proposals:
        proposed_pairs.add((p.record_id_a, p.record_id_b))
        proposed_pairs.add((p.record_id_b, p.record_id_a))

    # Evaluate against gold standard pairs
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    pair_results = []

    for item in benchmark["pairs"]:
        ra = item["record_a"]
        rb = item["record_b"]
        is_dup_ground_truth = item["is_duplicate_paper"]
        is_proposed = (ra, rb) in proposed_pairs or (rb, ra) in proposed_pairs

        if is_dup_ground_truth and is_proposed:
            tp += 1
            verdict = "TP"
        elif not is_dup_ground_truth and is_proposed:
            fp += 1
            verdict = "FP"
        elif is_dup_ground_truth and not is_proposed:
            fn += 1
            verdict = "FN"
        else:
            tn += 1
            verdict = "TN"

        pair_results.append(
            {
                "pair_id": item["pair_id"],
                "category": item["category"],
                "ground_truth_duplicate": is_dup_ground_truth,
                "proposed_as_duplicate": is_proposed,
                "verdict": verdict,
                "description": item["description"],
            }
        )

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    report = {
        "benchmark": benchmark["benchmark_name"],
        "total_benchmark_pairs": len(benchmark["pairs"]),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "study_vs_paper_false_merges": 0 if fp == 0 else fp,
        "pair_results": pair_results,
    }
    return report


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result, indent=2))
