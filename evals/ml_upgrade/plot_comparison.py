"""Render measured benchmark results; optional benchmark environment only."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/evidra-ml-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve


def plot(folder: Path):
    predictions = json.loads((folder / "predictions.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), layout="constrained")
    for name in ("baseline-0", "logistic-1", "xgboost-2", "catboost-4"):
        rows = predictions[name]
        labels, scores = np.array([r["label"] for r in rows]), np.array([r["score"] for r in rows])
        precision, recall, _ = precision_recall_curve(labels, scores)
        axes[0].plot(recall, precision, label=name)
        indices = sorted(range(len(rows)), key=lambda i: (-scores[i], rows[i]["id"]))
        axes[1].plot(np.arange(1, len(rows) + 1) / len(rows), np.cumsum(labels[indices]) / labels.sum(), label=name)
        actual, predicted = calibration_curve(labels, scores, n_bins=5)
        axes[2].plot(predicted, actual, marker="o", label=name)
    axes[0].set(xlabel="Recall", ylabel="Precision", title="Frozen test: precision–recall")
    axes[1].set(xlabel="Fraction screened", ylabel="Relevant records found", title="Frozen test: screening effort")
    axes[2].set(xlabel="Mean score", ylabel="Observed relevant fraction", title="Uncalibrated score reliability")
    axes[2].plot([0, 1], [0, 1], "k--", alpha=.4)
    for axis in axes:
        axis.legend(fontsize=8)
        axis.grid(alpha=.2)
    fig.suptitle("Wilson-disease review benchmark — not validation for the metformin review", fontsize=11)
    fig.savefig(folder / "comparison.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    plot(parser.parse_args().folder)
