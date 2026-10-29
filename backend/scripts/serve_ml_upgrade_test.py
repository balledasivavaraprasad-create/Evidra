"""Disposable, explicitly synthetic ML browser-test server; no production DB access."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if os.environ.get("APP_ENV") != "test" or os.environ.get("SOURCE_MODE") != "fixture":
    raise SystemExit("Only APP_ENV=test SOURCE_MODE=fixture is supported")

from app.ml_feature.trainer import train_ranker
from app.ml_feature.types import RecordInput, TrainConfig
from app.testing.serve import run_test_server

if __name__ == "__main__":
    dataset = json.loads((ROOT.parent / "evals/ml_c/dataset.json").read_text())
    with tempfile.TemporaryDirectory(prefix="evidra-ml-browser-artifact-") as directory:
        train_ranker([RecordInput(**r) for r in dataset["records"]], TrainConfig(max_features=500), directory,
                     scope="In adults with type 2 diabetes, how does metformin affect HbA1c?")
        os.environ["EVIDRA_ML_ARTIFACT_DIR"] = directory
        run_test_server(port=8891)
