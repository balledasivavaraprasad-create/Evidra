"""Explicit classification, ranking and calibration evidence for review prioritization."""
from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)


def operating_threshold(labels, scores, target_recall=0.95) -> float:
    """Choose highest precision at target recall using DEVELOPMENT data only."""
    y, p = _validated(labels, scores)
    if not 0 < target_recall <= 1 or not y.any():
        raise ValueError("Threshold selection requires positive support and a valid recall target")
    candidates = []
    for threshold in np.unique(p):
        pred = p >= threshold
        recall = recall_score(y, pred)
        if recall >= target_recall:
            candidates.append((precision_score(y, pred, zero_division=0),
                               fbeta_score(y, pred, beta=2, zero_division=0), float(threshold)))
    return max(candidates)[2]


def _validated(labels, scores):
    y, p = np.asarray(labels), np.asarray(scores, dtype=float)
    if y.ndim != 1 or p.ndim != 1 or not len(y) or len(y) != len(p):
        raise ValueError("Nonempty aligned label and score vectors required")
    if not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("Explicit binary labels and finite [0, 1] scores required")
    return y.astype(int), p


def evaluate_scores(labels, scores, *, threshold=0.5, ids=None) -> dict:
    y, p = _validated(labels, scores)
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold outside [0, 1]")
    names = list(ids) if ids is not None else [str(i) for i in range(len(y))]
    if len(names) != len(y) or len(set(names)) != len(names):
        raise ValueError("Unique aligned ranking IDs required")
    pred = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    positives = int(y.sum())
    both = len(np.unique(y)) == 2
    order = sorted(range(len(y)), key=lambda i: (-p[i], names[i]))
    ranked = y[order]
    result = {
        "n": len(y), "positives": positives, "prevalence": float(y.mean()),
        "threshold": float(threshold), "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)) if both else None,
        "precision": float(precision_score(y, pred)) if pred.any() else None,
        "recall": float(recall_score(y, pred)) if positives else None,
        "f1": float(f1_score(y, pred, zero_division=0)) if positives else None,
        "f2": float(fbeta_score(y, pred, beta=2, zero_division=0)) if positives else None,
        "average_precision": float(average_precision_score(y, p)) if positives else None,
        "roc_auc": float(roc_auc_score(y, p)) if both else None,
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "confusion": {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)},
        "tie_policy": "full_precision_score_desc_then_record_id_asc",
    }
    for percent in (10, 25, 50, 75):
        k = max(1, math.ceil(len(y) * percent / 100))
        hits = int(ranked[:k].sum())
        result[f"precision_at_{percent}pct"] = hits / k
        result[f"recall_at_{percent}pct"] = hits / positives if positives else None
    for target in (0.95, 0.99):
        name = str(round(target * 100))
        if positives:
            n = int(np.flatnonzero(np.cumsum(ranked) >= math.ceil(target * positives))[0]) + 1
            result[f"wss_at_{name}"] = target - n / len(y)
            result[f"screened_at_{name}"] = n
            result[f"actual_recall_at_{name}"] = float(ranked[:n].sum() / positives)
        else:
            result[f"wss_at_{name}"] = result[f"screened_at_{name}"] = None
            result[f"actual_recall_at_{name}"] = None
    return result


def group_bootstrap_ap(labels, scores, groups, *, seed=42, repetitions=200):
    """Descriptive group-bootstrap interval; insufficient replicates remain explicit."""
    y, p = _validated(labels, scores)
    if len(groups) != len(y):
        raise ValueError("Aligned groups required")
    unique = sorted(set(groups))
    indices_by_group = {group: [i for i, g in enumerate(groups) if g == group] for group in unique}
    rng = np.random.default_rng(seed)
    results = []
    for _ in range(repetitions):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        indices = [i for group in sampled for i in indices_by_group[group]]
        if len(np.unique(y[indices])) == 2:
            results.append(average_precision_score(y[indices], p[indices]))
    if len(results) < 20:
        return {"low": None, "high": None, "valid_replicates": len(results)}
    lo, hi = np.quantile(results, [0.025, 0.975])
    return {"low": float(lo), "high": float(hi), "valid_replicates": len(results)}
