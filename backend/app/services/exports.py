"""Sanitized CSV export service with formula-injection prevention and audit provenance."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.enums import EffectiveDecisionState
from app.contracts.models import ExportResponse
from app.db.models import (
    CorpusRevisionModel,
    ExportModel,
    GroupSnapshotModel,
    MachineResultModel,
    RecordRevisionModel,
    SourceRecordModel,
)
from app.services.corpus import (
    project_effective_group_decision,
)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def sanitize_formula_injection(val: str | None) -> str:
    """Escape spreadsheet formula injection characters (=, +, -, @, \\t, \\r).

    Prepends a single quote (') so spreadsheet applications treat cell strictly as plain text.
    Does NOT alter the database or raw literature records.
    """
    if not val:
        return ""
    text_val = str(val)
    if text_val and text_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text_val}"
    return text_val


def export_corpus_studies(
    db: Session,
    revision_id: str,
    export_format: str = "csv",
    created_by: str = "human-reviewer",
) -> ExportResponse:
    """Export confirmed included studies with formula-injection sanitization.

    Invariants:
    1. Only exports groups whose effective decision is INCLUDE.
    2. Exports exactly one representative revision per paper group.
    3. Omits unresolved conflicts.
    4. Formula injection characters are escaped.
    5. Generated file has deterministic SHA-256 recorded in ExportModel.
    """
    corpus_rev = db.query(CorpusRevisionModel).filter_by(id=revision_id).first()
    if not corpus_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus revision '{revision_id}' not found",
        )

    snapshots = (
        db.query(GroupSnapshotModel)
        .filter_by(corpus_revision_id=revision_id)
        .all()
    )

    included_rows: list[dict[str, str]] = []

    for snap in snapshots:
        group_id = snap.group_id
        # Check effective status
        eff_status, human_event, _screen_res, has_conflict = project_effective_group_decision(
            db=db,
            group_id=group_id,
            revision_id=revision_id,
        )

        # Invariant: only INCLUDE and never export unresolved conflicts
        if eff_status != EffectiveDecisionState.INCLUDE or has_conflict:
            continue

        rep_rev = db.query(RecordRevisionModel).filter_by(id=snap.representative_revision_id).first()
        if not rep_rev:
            continue
        src_rec = db.query(SourceRecordModel).filter_by(id=rep_rev.source_record_id).first()
        if not src_rec:
            continue

        authors = []
        if rep_rev.authors_json:
            try:
                authors = json.loads(rep_rev.authors_json)
            except (json.JSONDecodeError, TypeError, ValueError):
                authors = []

        # Find PICO machine summary if available
        pico_summary = ""
        pico_machine = (
            db.query(MachineResultModel)
            .filter_by(group_id=group_id, stage="pico")
            .order_by(MachineResultModel.created_at.desc())
            .first()
        )
        if pico_machine:
            try:
                p_data = json.loads(pico_machine.output_json)
                spans = p_data.get("spans", [])
                pico_summary = "; ".join([f"{s.get('label')}: {s.get('quote')}" for s in spans])
            except (json.JSONDecodeError, TypeError, ValueError):
                pico_summary = ""

        row = {
            "group_id": sanitize_formula_injection(group_id),
            "record_id": sanitize_formula_injection(src_rec.id),
            "source": sanitize_formula_injection(src_rec.source),
            "external_id": sanitize_formula_injection(src_rec.external_id),
            "doi": sanitize_formula_injection(rep_rev.doi),
            "pmid": sanitize_formula_injection(rep_rev.pmid),
            "title": sanitize_formula_injection(rep_rev.title),
            "authors": sanitize_formula_injection(", ".join(authors)),
            "year": sanitize_formula_injection(str(rep_rev.year) if rep_rev.year else ""),
            "journal": sanitize_formula_injection(rep_rev.journal),
            "abstract": sanitize_formula_injection(rep_rev.abstract_text),
            "effective_decision": "include",
            "decision_provenance": "human_decision" if human_event else "machine_suggestion",
            "pico_summary": sanitize_formula_injection(pico_summary),
        }
        included_rows.append(row)

    # Sort rows deterministically by group_id
    included_rows.sort(key=lambda r: r["group_id"])

    # Generate CSV string
    output = io.StringIO()
    fields = [
        "group_id",
        "record_id",
        "source",
        "external_id",
        "doi",
        "pmid",
        "title",
        "authors",
        "year",
        "journal",
        "abstract",
        "effective_decision",
        "decision_provenance",
        "pico_summary",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in included_rows:
        writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8")
    sha256_checksum = hashlib.sha256(csv_bytes).hexdigest()

    # Save to export folder
    export_id = f"exp-{uuid4().hex[:12]}"
    exports_dir = Path("backend/data/exports")
    exports_dir.mkdir(parents=True, exist_ok=True)
    file_path = exports_dir / f"{export_id}.csv"
    file_path.write_bytes(csv_bytes)

    export_model = ExportModel(
        id=export_id,
        workspace_id=corpus_rev.workspace_id,
        corpus_revision_id=corpus_rev.id,
        format=export_format,
        record_count=len(included_rows),
        sha256_checksum=sha256_checksum,
        file_path=str(file_path),
        created_by=created_by,
        created_at=utc_now(),
    )
    db.add(export_model)
    db.commit()

    return ExportResponse(
        id=export_id,
        revision_id=revision_id,
        format=export_format,
        record_count=len(included_rows),
        sha256_checksum=sha256_checksum,
        download_url=f"/api/v1/exports/{export_id}/download",
        created_at=export_model.created_at,
    )
