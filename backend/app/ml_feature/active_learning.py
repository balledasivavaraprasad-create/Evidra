"""Offline sequential-label simulation; never retrains from a reviewer click."""
from __future__ import annotations

import numpy as np

from app.ml_feature.advanced import build_challenger, feature_rows
from app.ml_feature.types import RecordInput


def simulate_review(records: list[RecordInput], seed_ids: list[str], *, budget=100,
                    batch_size=10, seed=42, policy="mixed") -> dict:
    """Retrospective experiment. Hidden labels are used only by the label oracle/report.

    The estimator receives features of the pool but labels of reviewed records only.
    Recall here is oracle-measured simulation recall, not a production stop criterion.
    """
    if policy not in {"mixed", "relevance", "random"}:
        raise ValueError("Unknown selection policy")
    if not 1 <= budget <= 500 or not 1 <= batch_size <= 50:
        raise ValueError("Simulation budget/batch bounds exceeded")
    mapping = {r.id: r for r in records}
    if len(mapping) != len(records) or len(set(seed_ids)) != len(seed_ids):
        raise ValueError("Unique record and seed IDs required")
    if any(r.label not in (0, 1) for r in records) or any(rid not in mapping for rid in seed_ids):
        raise ValueError("Fully labelled benchmark and valid seed IDs required")
    reviewed = list(seed_ids)
    if len(reviewed) < 4 or {mapping[rid].label for rid in reviewed} != {0, 1}:
        raise ValueError("At least four seed labels with both classes required")
    if len(reviewed) > budget:
        raise ValueError("Seed labels exceed the review budget")
    rng = np.random.default_rng(seed)
    total_positive = sum(r.label == 1 for r in records)
    history, fit_label_ids = [], []
    while len(reviewed) < min(budget, len(records)):
        reviewed_set = set(reviewed)
        remaining = [r for r in records if r.id not in reviewed_set]
        training = [mapping[rid] for rid in reviewed]
        count = min(batch_size, budget - len(reviewed), len(remaining))
        if policy == "random":
            chosen = rng.choice(len(remaining), size=count, replace=False).tolist()
        else:
            estimator = build_challenger("logistic", seed=seed, max_features=1000)
            estimator.fit(feature_rows(training), [r.label for r in training])
            fit_label_ids.append(list(reviewed))
            scores = estimator.predict_proba(feature_rows(remaining))[:, 1]
            relevant = sorted(range(len(remaining)), key=lambda i: (-scores[i], remaining[i].id))
            if policy == "relevance":
                chosen = relevant[:count]
            else:
                uncertainty = sorted(range(len(remaining)), key=lambda i: (abs(scores[i] - .5), remaining[i].id))
                n_relevant, n_uncertain = max(1, int(.7 * count)), int(.2 * count)
                chosen = relevant[:n_relevant]
                chosen += [i for i in uncertainty if i not in chosen][:n_uncertain]
                rest = [i for i in range(len(remaining)) if i not in chosen]
                chosen += rng.choice(rest, size=count - len(chosen), replace=False).tolist()
        # Labels of chosen papers become visible only on the following fit.
        reviewed.extend(remaining[i].id for i in chosen)
        hits = sum(mapping[rid].label == 1 for rid in reviewed)
        history.append({"reviewed": len(reviewed), "positives_found": hits,
                        "oracle_recall": hits / total_positive if total_positive else None})
    return {"policy": policy, "seed": seed, "initial_ids": seed_ids,
            "queried_ids": reviewed, "history": history, "fit_label_ids": fit_label_ids,
            "mode": "retrospective_simulation_not_prospective_validation"}
