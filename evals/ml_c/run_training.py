"""Training script to produce versioned, verified ML review ranker artifact."""
import json
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parents[2] / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.ml_feature.trainer import train_ranker
from app.ml_feature.types import RecordInput, TrainConfig


def main() -> None:
    eval_dir = Path(__file__).resolve().parent
    dataset_file = eval_dir / "dataset.json"
    artifact_dir = eval_dir / "artifact"

    print(f"Loading dataset from {dataset_file}...")
    with open(dataset_file, encoding="utf-8") as f:
        data = json.load(f)

    scope = data.get("review_question")
    records = [RecordInput(**r) for r in data["records"]]
    print(f"Loaded {len(records)} records. Training model for scope: '{scope}'...")

    config = TrainConfig(
        max_features=500,
        ngram_min=1,
        ngram_max=2,
        c_param=1.5,
        class_weight="balanced",
        seed=42,
        val_ratio=0.2,
        test_ratio=0.2,
    )

    manifest = train_ranker(
        records=records,
        config=config,
        output_dir=artifact_dir,
        scope=scope,
        artifact_version="ml_ranker:v1.0.0",
    )

    print("\nTraining successfully completed!")
    print(f"  Artifact version:    {manifest.artifact_version}")
    print(f"  Features in vocab:   {manifest.feature_count}")
    print(f"  Train records count: {manifest.train_records_count}")
    print(f"  Model file SHA-256:  {manifest.model_file_sha256}")
    print(f"  Validation metrics:  {manifest.metrics}")
    print(f"  Artifact saved at:   {artifact_dir}")


if __name__ == "__main__":
    main()
