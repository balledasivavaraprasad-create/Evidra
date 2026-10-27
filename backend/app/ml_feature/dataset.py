"""Dataset validation, text preprocessing, and leakage-safe group splitting."""
from __future__ import annotations

import hashlib
import random

from app.ml_feature.types import RecordInput


def prepare_text(title: str, abstract_text: str | None) -> str:
    """Combine title and abstract text into a canonical preprocessed representation."""
    cleaned_title = (title or "").strip()
    cleaned_abstract = (abstract_text or "").strip()
    if cleaned_abstract:
        return f"{cleaned_title}. {cleaned_abstract}"
    return cleaned_title


def compute_records_hash(records: list[RecordInput]) -> str:
    """Calculate deterministic SHA-256 fingerprint for a split of records."""
    hasher = hashlib.sha256()
    for rec in sorted(records, key=lambda r: r.id):
        hasher.update(rec.id.encode("utf-8"))
        hasher.update(str(rec.label).encode("utf-8"))
        hasher.update((rec.title or "").encode("utf-8"))
        hasher.update((rec.abstract_text or "").encode("utf-8"))
    return hasher.hexdigest()


def validate_dataset(records: list[RecordInput]) -> tuple[bool, list[str]]:
    """Validate that records form an admissible supervised training dataset."""
    errors: list[str] = []
    if not records or len(records) < 4:
        errors.append(f"Dataset too small ({len(records)} records); minimum required is 4")
        return False, errors

    labels: set[int] = set()
    for idx, r in enumerate(records):
        if not r.id or not r.id.strip():
            errors.append(f"Record at index {idx} has missing id")
        if not r.title or not r.title.strip():
            errors.append(f"Record {r.id} has empty title")
        if r.label is None or r.label not in (0, 1):
            errors.append(f"Record {r.id} has invalid label '{r.label}'; must be 0 or 1")
        else:
            labels.add(r.label)

    if len(labels) < 2:
        errors.append(
            f"Dataset must contain both positive (1) and negative (0) classes; observed classes: {labels}"
        )

    return len(errors) == 0, errors


def create_leakage_free_split(
    records: list[RecordInput],
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[RecordInput], list[RecordInput], list[RecordInput]]:
    """Partition records into train, validation, and test splits without study/group leakage.

    All records sharing the same group_id (e.g. duplicate pairs or same-study publications)
    are strictly assigned to the exact same split.
    """
    is_valid, errors = validate_dataset(records)
    if not is_valid:
        raise ValueError(f"Cannot split invalid dataset: {'; '.join(errors)}")

    # 1. Cluster records by group identity (fallback to record ID)
    group_to_records: dict[str, list[RecordInput]] = {}
    for r in records:
        gid = r.group_id if r.group_id else f"solo_{r.id}"
        group_to_records.setdefault(gid, []).append(r)

    # 2. Stratify groups by majority/presence of positive label
    pos_groups: list[str] = []
    neg_groups: list[str] = []

    for gid, group_recs in group_to_records.items():
        if any(rec.label == 1 for rec in group_recs):
            pos_groups.append(gid)
        else:
            neg_groups.append(gid)

    rng = random.Random(seed)
    rng.shuffle(pos_groups)
    rng.shuffle(neg_groups)

    def split_group_list(groups: list[str]) -> tuple[list[str], list[str], list[str]]:
        n = len(groups)
        n_test = max(1, round(n * test_ratio)) if n >= 4 else (1 if n >= 3 else 0)
        n_val = max(1, round(n * val_ratio)) if n >= 5 else (1 if n >= 3 else 0)

        test_g = groups[:n_test]
        val_g = groups[n_test : n_test + n_val]
        train_g = groups[n_test + n_val :]

        # Guarantee at least 1 group in train
        if not train_g and val_g:
            train_g.append(val_g.pop())
        return train_g, val_g, test_g

    pos_train, pos_val, pos_test = split_group_list(pos_groups)
    neg_train, neg_val, neg_test = split_group_list(neg_groups)

    train_groups = set(pos_train + neg_train)
    val_groups = set(pos_val + neg_val)
    test_groups = set(pos_test + neg_test)

    train_records = [r for gid in train_groups for r in group_to_records[gid]]
    val_records = [r for gid in val_groups for r in group_to_records[gid]]
    test_records = [r for gid in test_groups for r in group_to_records[gid]]

    # Ensure train split contains both classes
    train_labels = {r.label for r in train_records}
    if 0 not in train_labels or 1 not in train_labels:
        raise ValueError(
            f"Training split must contain both classes 0 and 1; observed: {train_labels}"
        )

    return train_records, val_records, test_records
