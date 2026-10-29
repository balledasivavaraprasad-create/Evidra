"""Normalize a locally downloaded SYNERGY CSV; never downloads during CI.

Uses abstract-screening labels, not final full-text inclusion labels.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


def prepare(source: Path, output: Path):
    rows = list(csv.DictReader(source.open(encoding="utf-8-sig")))
    parent = {r["record_id"]: r["record_id"] for r in rows}

    def root(key):
        while parent[key] != key:
            key = parent[key]
        return key

    def union(a, b):
        if a in parent and b in parent:
            a, b = root(a), root(b)
            parent[max(a, b)] = min(a, b)

    identities = {}
    for row in rows:
        rid = row["record_id"]
        for other in re.findall(r"\d+", row.get("duplicate_record_id", "")):
            union(rid, other)
        doi = row.get("doi", "").strip().lower()
        title = re.sub(r"\W+", " ", row.get("title", "").lower()).strip()
        for key in (["doi:" + doi] if doi else []) + (["title:" + title] if title else []):
            if key in identities:
                union(rid, identities[key])
            identities[key] = rid
    grouped = {}
    for row in rows:
        grouped.setdefault(root(row["record_id"]), []).append(row)
    records, conflicts, missing, missing_title = [], 0, 0, 0
    for gid, group in sorted(grouped.items()):
        labels = {r["label_abstract_screening"] for r in group}
        if len(labels) != 1 or not labels <= {"0", "1"}:
            conflicts += len(group)
            continue
        row = max(group, key=lambda r: (len(r.get("abstract", "")), r["record_id"]))
        if not row.get("title", "").strip():
            missing_title += 1
            continue
        if len(row.get("abstract", "").strip()) < 10:
            missing += 1
            continue
        records.append({"id": "wilson-" + row["record_id"], "group_id": "wilson-" + gid,
                        "title": row["title"], "abstract_text": row["abstract"],
                        "label": int(row["label_abstract_screening"])})
    payload = {
        "dataset_name": "SYNERGY-Appenzeller-Herzog_2020-abstract-screening",
        "review_question": "Comparative effectiveness of common therapies for Wilson disease",
        "provenance": "Public human-screened review benchmark; not metformin-topic validation",
        "label_stage": "title_abstract", "label_origin": "published_human_screening",
        "source_url": "https://raw.githubusercontent.com/asreview/systematic-review-datasets/metadata-v1-final/datasets/Appenzeller-Herzog_2020/output/Appenzeller-Herzog_2020.csv",
        "reference": "https://doi.org/10.1111/liv.14179",
        "license": "CC-BY-4.0; Appenzeller-Herzog et al., via ASReview SYNERGY",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "raw_records": len(rows), "unique_groups": len(grouped),
        "conflicting_rows_quarantined": conflicts, "missing_abstract_groups_manual_only": missing,
        "missing_title_groups_quarantined": missing_title,
        "known_study_ids_available": False, "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: v for k, v in payload.items() if k != "records"}, indent=2))
    print(f"Admissible records: {len(records)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
