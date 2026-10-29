"""Explicit separate retrospective experiment; not part of static model selection."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.ml_feature.active_learning import simulate_review
from app.ml_feature.types import RecordInput


def run(dataset: Path, output: Path):
    raw = json.loads(dataset.read_text())
    records = [RecordInput(**r) for r in raw["records"]]
    # Declared balanced seeds emulate a reviewer supplying two known examples of each class.
    initial = [r.id for r in records if r.label == 0][:2] + [r.id for r in records if r.label == 1][:2]
    runs = [simulate_review(records, initial, budget=100, seed=seed, policy=policy)
            for seed in (42, 43) for policy in ("relevance", "mixed", "random")]
    output.write_text(json.dumps({"dataset": raw["dataset_name"],
                                 "initial_seed_policy": "two known positives and two known negatives",
                                 "runs": runs}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.dataset, args.output)
