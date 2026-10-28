"""Stage-specific fingerprint generation and execution cache resolution for selective graph processing."""
from __future__ import annotations

import hashlib
import logging

from sqlalchemy.orm import Session

from app.db.models import MachineResultModel, PicoAnnotationModel

logger = logging.getLogger(__name__)


def compute_screening_fingerprint(
    record_id: str,
    content_hash: str,
    criteria_hash: str,
    method_version: str,
) -> str:
    """Generate deterministic SHA-256 fingerprint for a screening evaluation input."""
    raw = f"screen:{record_id}:{content_hash}:{criteria_hash}:{method_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_pico_fingerprint(
    record_id: str,
    content_hash: str,
    method_version: str,
) -> str:
    """Generate deterministic SHA-256 fingerprint for a PICO span extraction input."""
    raw = f"pico:{record_id}:{content_hash}:{method_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_machine_result(
    db: Session,
    stage: str,
    fingerprint: str,
) -> MachineResultModel | None:
    """Retrieve existing machine result for exact matching stage and input fingerprint."""
    return (
        db.query(MachineResultModel)
        .filter_by(stage=stage, input_fingerprint=fingerprint)
        .order_by(MachineResultModel.created_at.desc())
        .first()
    )


def get_cached_pico_annotations(
    db: Session,
    record_revision_id: str,
    expected_text_hash: str,
) -> list[PicoAnnotationModel]:
    """Retrieve existing PICO annotations for a record revision matching expected text hash."""
    results = (
        db.query(PicoAnnotationModel)
        .filter_by(record_revision_id=record_revision_id, text_hash=expected_text_hash)
        .all()
    )
    return results
