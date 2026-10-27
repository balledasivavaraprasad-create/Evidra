"""Evaluation runner evaluating review prioritization quality on held-out test records."""
import json
import sys
import time
from pathlib import Path
from sklearn.metrics import average_precision_score, roc_auc_score

# Add backend to sys.path
backend_path = Path(__file__).resolve().parents[2] / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.ml_feature.dataset import create_leakage_free_split
from app.ml_feature.ranker import load_ranker
from app.ml_feature.types import RankingContext, RecordInput


def compute_wss(labels: list[int], scores: list[float], recall_target: float = 0.95) -> float:
    """Compute Work Saved over Sampling (WSS@Recall) for systematic review prioritization."""
    total_relevant = sum(labels)
    total_records = len(labels)
    if total_relevant == 0 or total_records == 0:
        return 0.0

    target_found = int(round(total_relevant * recall_target))
    # Sort indices by score descending
    sorted_indices = sorted(range(total_records), key=lambda i: scores[i], reverse=True)

    found = 0
    screened = 0
    for idx in sorted_indices:
        screened += 1
        if labels[idx] == 1:
            found += 1
        if found >= target_found:
            break

    # WSS@R = (N - Screened) / N - (1 - R)
    wss = ((total_records - screened) / total_records) - (1.0 - recall_target)
    return round(float(wss), 4)


def main() -> None:
    eval_dir = Path(__file__).resolve().parent
    dataset_file = eval_dir / "dataset.json"
    artifact_dir = eval_dir / "artifact"
    report_file = eval_dir / "benchmark_report.json"

    with open(dataset_file, encoding="utf-8") as f:
        data = json.load(f)

    scope = data["review_question"]
    records = [RecordInput(**r) for r in data["records"]]

    # Recreate the exact same leakage-free split
    _, _, test_records = create_leakage_free_split(
        records,
        val_ratio=0.2,
        test_ratio=0.2,
        seed=42,
    )

    print(f"Loaded {len(test_records)} held-out test records (zero overlap with training split).")
    test_labels = [r.label for r in test_records]
    pos_count = sum(test_labels)
    neg_count = len(test_labels) - pos_count
    print(f"Test Class Balance: {pos_count} Relevant / {neg_count} Excluded")

    # Load and verify artifact
    ranker = load_ranker(artifact_dir, expected_scope=scope)

    # Measure inference latency
    t0 = time.perf_counter()
    context = RankingContext(review_question=scope)
    batch = ranker.rank_records(test_records, context)
    latency_ms = (time.perf_counter() - t0) * 1000

    # Map scores back to original test records order
    scores_by_id = {item.record_id: item.score for item in batch.items}
    ordered_scores = [scores_by_id[r.id] for r in test_records]

    # Calculate metrics
    auc = roc_auc_score(test_labels, ordered_scores) if len(set(test_labels)) > 1 else 1.0
    pr_auc = average_precision_score(test_labels, ordered_scores) if len(set(test_labels)) > 1 else 1.0
    wss_95 = compute_wss(test_labels, ordered_scores, recall_target=0.95)

    # Top-K Precision
    top_5_ids = [item.record_id for item in batch.items[:5]]
    labels_by_id = {r.id: r.label for r in test_records}
    p_at_5 = sum(labels_by_id[rid] for rid in top_5_ids) / 5.0

    report = {
        "evaluation_name": "ML Review Prioritization Evaluation",
        "scope": scope,
        "artifact_version": ranker.manifest.artifact_version,
        "total_test_records": len(test_records),
        "relevant_count": pos_count,
        "excluded_count": neg_count,
        "metrics": {
            "roc_auc": round(float(auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "wss_at_95": round(float(wss_95), 4),
            "precision_at_5": round(float(p_at_5), 4),
            "inference_total_ms": round(float(latency_ms), 3),
            "inference_per_record_ms": round(float(latency_ms / len(test_records)), 3),
        },
        "top_5_prioritized_records": [
            {
                "rank": item.rank,
                "record_id": item.record_id,
                "score": item.score,
                "true_label": labels_by_id[item.record_id],
            }
            for item in batch.items[:5]
        ],
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n================== BENCHMARK REPORT ==================")
    print(f"ROC-AUC:                {report['metrics']['roc_auc']:.4f}")
    print(f"PR-AUC (Avg Precision): {report['metrics']['pr_auc']:.4f}")
    print(f"WSS@95 (Work Saved):    {report['metrics']['wss_at_95']:.4f}")
    print(f"Precision@5:            {report['metrics']['precision_at_5']:.4f}")
    print(f"Per-record Latency:     {report['metrics']['inference_per_record_ms']:.3f} ms")
    print("======================================================")
    print(f"Report saved to {report_file}")


if __name__ == "__main__":
    main()
