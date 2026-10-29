"""Bounded offline development selection and one-time frozen-test reporting.

Run from repository root with backend/.venv/bin/python. Never invoked by ordinary CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import importlib.metadata
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import joblib
import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.frozen import FrozenEstimator

from app.ml_feature.advanced import FEATURE_SCHEMA, build_challenger, feature_rows
from app.ml_feature.dataset import compute_records_hash, create_leakage_free_split, prepare_text
from app.ml_feature.evaluation import evaluate_scores, group_bootstrap_ap, operating_threshold
from app.ml_feature.pipeline import build_pipeline
from app.ml_feature.trainer import compute_file_sha256
from app.ml_feature.types import ArtifactManifest, RecordInput, TrainConfig


def inputs(records, schema):
    return (feature_rows(records) if schema == FEATURE_SCHEMA else
            [prepare_text(r.title[:50000], (r.abstract_text or "")[:50000]) for r in records])


def probabilities(model, records, schema):
    return np.asarray(model.predict_proba(inputs(records, schema)))[:, list(model.classes_).index(1)]


def run(dataset_path: Path, output: Path, *, trials=2, seed=42, iterations=120):
    output.mkdir(parents=True, exist_ok=False)
    raw = json.loads(dataset_path.read_text())
    records = [RecordInput(**r) for r in raw["records"]]
    train, development, test = create_leakage_free_split(records, seed=seed)
    if not development or not test or any(len({r.label for r in split}) != 2 for split in (train, development, test)):
        raise ValueError("Independent train/development/test partitions with both classes required")
    # Calibration gets disjoint groups, threshold/model selection gets the remainder.
    if min(sum(r.label == c for r in development) for c in (0, 1)) >= 10:
        calibration, selection, unused = create_leakage_free_split(
            development, val_ratio=0.4, test_ratio=0.1, seed=seed + 1)
        selection = selection + unused
    else:
        calibration, selection = [], development
    splits = {"train": train, "calibration": calibration, "selection": selection, "test": test}
    split_manifest = {key: {"ids": [r.id for r in values], "hash": compute_records_hash(values),
                           "n": len(values), "positives": sum(r.label == 1 for r in values)}
                      for key, values in splits.items()}
    (output / "splits.json").write_text(json.dumps(split_manifest, indent=2))
    metadata = {k: v for k, v in raw.items() if k != "records"}
    protocol = {"seed": seed, "trials_per_booster": trials, "iterations": iterations,
                "early_stopping": "not used: fixed bounded tree counts; no eval_set touches test data",
                "libraries": {name: importlib.metadata.version(name) for name in ("scikit-learn", "catboost", "joblib")},
                "selection": "development precision at >=95% recall; then F2, AP; ties prefer linear baseline",
                "test_policy": "Frozen test is evaluated only after selection; never tune against this report",
                "confidence": "Descriptive group-bootstrap AP interval, not prospective clinical validation",
                "data": metadata, "dataset_sha256": compute_file_sha256(dataset_path),
                "hardware": platform.platform(), "python": platform.python_version(),
                "sklearn": sklearn.__version__, "created_at": datetime.now(UTC).isoformat()}
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    y_train = [r.label for r in train]
    positive_weight = y_train.count(0) / y_train.count(1)
    configurations = [("baseline", 1.0, False, "text-v1"), ("logistic", 1.0, False, FEATURE_SCHEMA)]
    configurations += [(family, (3.0, 8.0, 1.0)[i % 3], bool(i % 2), FEATURE_SCHEMA)
                       for family in ("xgboost", "catboost") for i in range(trials)]
    ledger, fitted = [], []
    for index, (family, strength, svd, schema) in enumerate(configurations):
        started = time.perf_counter()
        entry = {"id": f"{family}-{index}", "family": family, "strength": strength,
                 "svd": svd, "schema": schema, "status": "failed"}
        try:
            base = (build_pipeline(TrainConfig(max_features=2000, seed=seed)) if family == "baseline" else
                    build_challenger(family, seed=seed, strength=strength, svd=svd,
                                     positive_weight=positive_weight, character=family == "logistic",
                                     iterations=iterations))
            base.fit(inputs(train, schema), y_train)
            variants = [(base, False)]
            if calibration:
                calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
                calibrated.fit(inputs(calibration, schema), [r.label for r in calibration])
                variants.append((calibrated, True))
            for model, calibrated in variants:
                scores = probabilities(model, selection, schema)
                threshold = operating_threshold([r.label for r in selection], scores)
                metrics = evaluate_scores([r.label for r in selection], scores, threshold=threshold,
                                          ids=[r.id for r in selection])
                candidate = dict(entry, status="completed", calibrated=calibrated,
                                 threshold=threshold, development=metrics,
                                 feature_count=int(base.named_steps["features"].transform(inputs(train[:1], schema)).shape[1])
                                 if schema == FEATURE_SCHEMA else len(base.named_steps["tfidfvectorizer"].vocabulary_),
                                 duration_seconds=time.perf_counter() - started)
                ledger.append(candidate)
                fitted.append((candidate, model))
            print(f"Completed {family} (SVD={svd})", flush=True)
        except (ValueError, ImportError, RuntimeError, OSError) as exc:
            ledger.append(dict(entry, error=f"{type(exc).__name__}: {exc}"))
            print(f"Failed {family}: {exc}", flush=True)
        (output / "trials.json").write_text(json.dumps(ledger, indent=2))
    if len({r[0]["family"] for r in fitted}) < 4:
        raise RuntimeError("Required candidate families did not all run; see trials.json")
    def utility(candidate):
        metrics = candidate[0]["development"]
        # Predeclared deterministic tie preference; selection uses no test labels.
        return (round(metrics["precision"] or 0, 4), round(metrics["f2"] or 0, 4),
                round(metrics["average_precision"] or 0, 4), candidate[0]["family"] == "baseline",
                candidate[0]["family"] == "logistic", not candidate[0]["calibrated"])
    winner, model = max(fitted, key=utility)
    report = {"protocol": protocol, "selected_on_development": winner,
              "deployment": "NOT_PROMOTED: independent benchmark/synthetic data is not validation for the active metformin review",
              "test": {}, "baselines": {}}
    predictions = {}
    # One final evaluation pass across frozen candidates. No later optimization.
    for entry, fitted_model in fitted:
        key = entry["id"] + ("-calibrated" if entry["calibrated"] else "")
        timings = []
        for _ in range(5):
            t0 = time.perf_counter()
            scores = probabilities(fitted_model, test, entry["schema"])
            timings.append((time.perf_counter() - t0) * 1000)
        metrics = evaluate_scores([r.label for r in test], scores,
                                  threshold=entry["threshold"], ids=[r.id for r in test])
        metrics["ap_group_bootstrap_95pct"] = group_bootstrap_ap(
            [r.label for r in test], scores, [r.group_id or r.id for r in test], repetitions=100)
        metrics["warm_batch_ms_p50"] = float(np.median(timings[1:]))
        metrics["warm_batch_ms_p95"] = float(np.quantile(timings[1:], .95))
        metrics["first_batch_ms"] = timings[0]
        observed, predicted = calibration_curve([r.label for r in test], scores, n_bins=5)
        metrics["reliability"] = {"observed": observed.tolist(), "predicted": predicted.tolist()}
        report["test"][key] = metrics
        predictions[key] = [{"id": r.id, "label": r.label, "score": float(s)} for r, s in zip(test, scores, strict=True)]
    for name, scores in {
        "fixed_order": np.linspace(1, 0, len(test)),
        "seeded_random": np.random.default_rng(seed).random(len(test)),
    }.items():
        report["baselines"][name] = evaluate_scores([r.label for r in test], scores, ids=[r.id for r in test])
    # A candidate bundle is integrable by the existing runtime, but promotion is separate.
    artifact = output / "candidate"
    artifact.mkdir()
    joblib.dump(model, artifact / "model.joblib", compress=3)
    feature_count = winner["feature_count"]
    manifest = ArtifactManifest(
        artifact_version="ml_upgrade:v2", model_type=winner["family"],
        sklearn_version=sklearn.__version__, joblib_version=joblib.__version__,
        created_at=datetime.now(UTC).isoformat(), scope=raw["review_question"],
        feature_count=feature_count, train_records_count=len(train),
        train_hash=compute_records_hash(train), val_hash=compute_records_hash(development),
        test_hash=compute_records_hash(test), model_file_sha256=compute_file_sha256(artifact / "model.joblib"),
        config={"input_schema": winner["schema"], "selected": winner,
                "data_provenance": metadata, "calibration_hash": compute_records_hash(calibration),
                "score_semantics": "ranking_score_not_clinical_probability"},
    )
    (artifact / "manifest.json").write_text(manifest.model_dump_json(indent=2))
    report["artifact_bytes"] = (artifact / "model.joblib").stat().st_size
    (output / "report.json").write_text(json.dumps(report, indent=2))
    (output / "predictions.json").write_text(json.dumps(predictions, indent=2))
    lines = ["# Model comparison", "", f"Dataset: {raw['dataset_name']}", "",
             report["deployment"], "", f"Development-selected candidate: {winner['id']}; calibrated={winner['calibrated']}", "",
             "| Candidate | Accuracy | Precision | Recall | F1 | AP | WSS@95 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, m in report["test"].items():
        values = [m[k] for k in ("accuracy", "precision", "recall", "f1", "average_precision", "wss_at_95")]
        lines.append("| " + name + " | " + " | ".join("N/A" if v is None else f"{v:.4f}" for v in values) + " |")
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, choices=range(1, 4), default=2)
    parser.add_argument("--iterations", type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 500:
        parser.error("iterations must be in [1, 500]")
    run(args.dataset, args.output, trials=args.trials, iterations=args.iterations)
