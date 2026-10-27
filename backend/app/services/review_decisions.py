"""Reviewer decision persistence, optimistic locking, PICO verification, and conflict resolution."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    DedupEdgeStatus,
    EligibilityStatus,
)
from app.contracts.models import (
    ConflictResolveRequest,
    DecisionCommand,
    DedupOverrideRequest,
    PicoOverrideRequest,
    ReviewEventResponse,
)
from app.db.models import (
    DedupEdgeModel,
    GroupMemberModel,
    PaperGroupModel,
    PicoAnnotationModel,
    RecordRevisionModel,
    ReviewConflictModel,
    ReviewEventModel,
    WorkspaceModel,
)
from app.pico.validator import compute_text_hash

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def _get_next_event_sequence(db: Session, workspace_id: str) -> int:
    """Get monotonically increasing event sequence for workspace."""
    max_seq = (
        db.query(func.max(ReviewEventModel.sequence))
        .filter_by(workspace_id=workspace_id)
        .scalar()
    )
    return (max_seq or 0) + 1


def record_screening_decision(
    db: Session,
    group_id: str,
    command: DecisionCommand,
    actor_id: str = "human-reviewer",
) -> ReviewEventResponse:
    """Record an append-only reviewer eligibility decision with optimistic locking.

    Invariants:
    1. Human decision strictly wins over machine suggestion.
    2. Exclusion requires an explicit, non-empty clinical/methodological reason.
    3. Optimistic locking: expected_version must match group.row_version; otherwise 409 Conflict.
    4. Review events are append-only; undo creates a superseding event.
    """
    group = db.query(PaperGroupModel).filter_by(id=group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found",
        )

    # 1. Optimistic locking check
    if group.row_version != command.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"STALE_VERSION_CONFLICT: Expected version {command.expected_version} "
                f"does not match current group version {group.row_version}"
            ),
        )

    # 2. Exclude requires non-empty reason
    if command.status == EligibilityStatus.EXCLUDE and (not command.reason or not command.reason.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Exclusion requires an explicit reason explaining the clinical or methodological basis.",
        )

    # 3. Next sequence
    seq = _get_next_event_sequence(db, group.workspace_id)

    # 4. Append review event
    event = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=group.workspace_id,
        group_id=group.id,
        sequence=seq,
        event_type=DecisionEventType.SCREEN_DECISION.value,
        payload_json=json.dumps({"status": command.status.value}),
        actor_id=actor_id,
        reason=command.reason.strip() if command.reason else None,
        supersedes_event_id=None,
        created_at=utc_now(),
    )
    db.add(event)

    # 5. Increment group row version
    group.row_version += 1
    db.commit()

    return ReviewEventResponse(
        id=event.id,
        sequence=event.sequence,
        workspace_id=event.workspace_id,
        group_id=event.group_id,
        event_type=DecisionEventType.SCREEN_DECISION,
        payload=json.loads(event.payload_json),
        actor_id=event.actor_id,
        reason=event.reason,
        supersedes_event_id=event.supersedes_event_id,
        created_at=event.created_at,
    )


def save_pico_annotations(
    db: Session,
    group_id: str,
    request: PicoOverrideRequest,
    actor_id: str = "human-reviewer",
) -> ReviewEventResponse:
    """Save verified human PICO annotation offsets bound to immutable text revision.

    Invariants:
    1. Spans use half-open Unicode code-point offsets: 0 <= start_cp < end_cp <= len(text).
    2. Exact quote validation: text[start_cp:end_cp] == quote.
    3. Content hash validation: matches immutable abstract_text content hash.
    4. Overlapping spans across distinct labels (P, I, C, O) are permitted.
    5. Optimistic concurrency check on group row_version.
    """
    group = db.query(PaperGroupModel).filter_by(id=group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found",
        )

    # Optimistic locking
    if group.row_version != request.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"STALE_VERSION_CONFLICT: Expected version {request.expected_version} "
                f"does not match current group version {group.row_version}"
            ),
        )

    # Find target revision
    rev = db.query(RecordRevisionModel).filter_by(id=request.record_revision_id).first()
    if not rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record revision '{request.record_revision_id}' not found",
        )

    # Validate content hash
    text = rev.abstract_text or ""
    actual_hash = compute_text_hash(text)
    if actual_hash != request.content_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"TEXT_REVISION_HASH_MISMATCH: Provided hash '{request.content_hash}' "
                f"does not match stored text hash '{actual_hash}'"
            ),
        )

    # Validate each span
    text_len = len(text)
    for span in request.spans:
        if not (0 <= span.start_cp < span.end_cp <= text_len):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid span bounds: [{span.start_cp}, {span.end_cp}) "
                    f"for text length {text_len}"
                ),
            )
        extracted = text[span.start_cp : span.end_cp]
        if extracted != span.quote:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Span quote mismatch for label {span.label}: expected quote '{span.quote}', "
                    f"found '{extracted}'"
                ),
            )

    seq = _get_next_event_sequence(db, group.workspace_id)
    event_id = str(uuid4())

    event = ReviewEventModel(
        id=event_id,
        workspace_id=group.workspace_id,
        group_id=group.id,
        sequence=seq,
        event_type=DecisionEventType.PICO_OVERRIDE.value,
        payload_json=json.dumps({"spans": [s.model_dump() for s in request.spans]}),
        actor_id=actor_id,
        reason=None,
        supersedes_event_id=None,
        created_at=utc_now(),
    )
    db.add(event)

    # Persist annotations
    for span in request.spans:
        db.add(
            PicoAnnotationModel(
                id=str(uuid4()),
                event_id=event_id,
                record_revision_id=rev.id,
                label=span.label.value,
                start_cp=span.start_cp,
                end_cp=span.end_cp,
                quote=span.quote,
                provenance=span.provenance or "human_override",
                created_at=utc_now(),
            )
        )

    group.row_version += 1
    db.commit()

    return ReviewEventResponse(
        id=event.id,
        sequence=event.sequence,
        workspace_id=event.workspace_id,
        group_id=event.group_id,
        event_type=DecisionEventType.PICO_OVERRIDE,
        payload=json.loads(event.payload_json),
        actor_id=event.actor_id,
        reason=None,
        supersedes_event_id=None,
        created_at=event.created_at,
    )


def record_dedup_override(
    db: Session,
    workspace_id: str,
    request: DedupOverrideRequest,
    actor_id: str = "human-reviewer",
) -> ReviewEventResponse:
    """Confirm a proposed duplicate pair or enforce a cannot-link constraint."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # Find existing edge
    edge = (
        db.query(DedupEdgeModel)
        .filter_by(workspace_id=workspace_id, record_id_a=request.record_id_a, record_id_b=request.record_id_b)
        .first()
    )
    if not edge:
        edge = (
            db.query(DedupEdgeModel)
            .filter_by(workspace_id=workspace_id, record_id_a=request.record_id_b, record_id_b=request.record_id_a)
            .first()
        )

    new_status = DedupEdgeStatus.CONFIRMED.value if request.confirm else DedupEdgeStatus.REJECTED.value

    if edge:
        edge.status = new_status
    else:
        edge = DedupEdgeModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            record_id_a=request.record_id_a,
            record_id_b=request.record_id_b,
            score=1.0 if request.confirm else 0.0,
            method_version="human_override:v1.0.0",
            evidence_json=json.dumps({"manual_override": True, "reason": request.reason}),
            status=new_status,
            reviewer_event_id=None,
            created_at=utc_now(),
        )
        db.add(edge)

    # Find associated group
    member = db.query(GroupMemberModel).filter_by(source_record_id=request.record_id_a).first()
    group_id = member.group_id if member else f"grp-{uuid4().hex[:12]}"

    seq = _get_next_event_sequence(db, workspace_id)
    event = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group_id,
        sequence=seq,
        event_type=DecisionEventType.DEDUP_OVERRIDE.value,
        payload_json=json.dumps(
            {
                "record_id_a": request.record_id_a,
                "record_id_b": request.record_id_b,
                "confirm": request.confirm,
            }
        ),
        actor_id=actor_id,
        reason=request.reason,
        supersedes_event_id=None,
        created_at=utc_now(),
    )
    db.add(event)
    edge.reviewer_event_id = event.id
    db.commit()

    return ReviewEventResponse(
        id=event.id,
        sequence=event.sequence,
        workspace_id=event.workspace_id,
        group_id=event.group_id,
        event_type=DecisionEventType.DEDUP_OVERRIDE,
        payload=json.loads(event.payload_json),
        actor_id=event.actor_id,
        reason=event.reason,
        supersedes_event_id=None,
        created_at=event.created_at,
    )


def resolve_group_conflict(
    db: Session,
    conflict_id: str,
    request: ConflictResolveRequest,
    actor_id: str = "human-reviewer",
) -> ReviewEventResponse:
    """Manually resolve an inherited screening divergence conflict."""
    conflict = db.query(ReviewConflictModel).filter_by(id=conflict_id).first()
    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conflict '{conflict_id}' not found",
        )

    group = db.query(PaperGroupModel).filter_by(id=conflict.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{conflict.group_id}' not found",
        )

    if group.row_version != request.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"STALE_VERSION_CONFLICT: Expected version {request.expected_version} "
                f"does not match current group version {group.row_version}"
            ),
        )

    seq = _get_next_event_sequence(db, group.workspace_id)
    event = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=group.workspace_id,
        group_id=group.id,
        sequence=seq,
        event_type=DecisionEventType.CONFLICT_RESOLUTION.value,
        payload_json=json.dumps({"chosen_status": request.chosen_status.value}),
        actor_id=actor_id,
        reason=request.reason,
        supersedes_event_id=None,
        created_at=utc_now(),
    )
    db.add(event)
    conflict.resolution_event_id = event.id
    group.row_version += 1
    db.commit()

    return ReviewEventResponse(
        id=event.id,
        sequence=event.sequence,
        workspace_id=event.workspace_id,
        group_id=event.group_id,
        event_type=DecisionEventType.CONFLICT_RESOLUTION,
        payload=json.loads(event.payload_json),
        actor_id=event.actor_id,
        reason=event.reason,
        supersedes_event_id=None,
        created_at=event.created_at,
    )
