"""Snapshot restoration, lineage projection, and corpus diff services."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    ConflictKind,
    CorpusRevisionState,
    DecisionEventType,
    GroupLineageOp,
    RestoreMode,
)
from app.contracts.models import (
    CorpusDiffResponse,
    CorpusRevisionResponse,
)
from app.db.models import (
    CorpusMemberModel,
    CorpusRevisionModel,
    GroupLineageModel,
    GroupMemberModel,
    GroupSnapshotModel,
    ReviewConflictModel,
    ReviewEventModel,
    WorkspaceModel,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def get_next_event_sequence(db: Session, workspace_id: str) -> int:
    """Get next monotonically increasing review event sequence for workspace."""
    max_seq = (
        db.query(func.max(ReviewEventModel.sequence))
        .filter_by(workspace_id=workspace_id)
        .scalar()
    )
    return (max_seq or 0) + 1


def project_decision_lineage(
    db: Session,
    corpus_revision_id: str,
    parent_revision_id: str,
) -> None:
    """Project reviewer decisions and track lineage transitions from parent to new corpus revision.

    Rules:
    1. Detects merge, split, extend, and retain transitions across revisions.
    2. Agreeing parent decisions carry forward with full provenance.
    3. Conflicting parent decisions (e.g. INCLUDE vs EXCLUDE) create an unresolved ReviewConflict.
    4. Group splits preserve history and create ReviewConflict flagging ambiguity for reaffirmation.
    5. Single parent decisions carry forward with inherited attribution.
    """
    db.flush()
    rev = db.query(CorpusRevisionModel).filter_by(id=corpus_revision_id).first()
    if not rev:
        return
    ws_id = rev.workspace_id

    # Gather parent groups and their members
    parent_snapshots = (
        db.query(GroupSnapshotModel)
        .filter_by(corpus_revision_id=parent_revision_id)
        .all()
    )
    if not parent_snapshots:
        return

    parent_group_ids = [s.group_id for s in parent_snapshots]
    parent_members = (
        db.query(GroupMemberModel)
        .filter(GroupMemberModel.group_id.in_(parent_group_ids))
        .all()
    )
    parent_members_map: dict[str, set[str]] = {}
    for pm in parent_members:
        parent_members_map.setdefault(pm.group_id, set()).add(pm.source_record_id)

    # Gather child groups and their members in new revision
    child_snapshots = (
        db.query(GroupSnapshotModel)
        .filter_by(corpus_revision_id=corpus_revision_id)
        .all()
    )
    if not child_snapshots:
        return

    child_group_ids = [s.group_id for s in child_snapshots]
    child_members = (
        db.query(GroupMemberModel)
        .filter(GroupMemberModel.group_id.in_(child_group_ids))
        .all()
    )
    child_members_map: dict[str, set[str]] = {}
    for cm in child_members:
        child_members_map.setdefault(cm.group_id, set()).add(cm.source_record_id)

    # Invert parent mapping: source_record_id -> set of parent_group_ids
    record_to_parent_groups: dict[str, set[str]] = {}
    for p_id, recs in parent_members_map.items():
        for r_id in recs:
            record_to_parent_groups.setdefault(r_id, set()).add(p_id)

    # Analyze each child group
    for child_id, child_recs in child_members_map.items():
        # Find all parent groups that share at least one record
        matched_parent_ids: set[str] = set()
        for r_id in child_recs:
            if r_id in record_to_parent_groups:
                matched_parent_ids.update(record_to_parent_groups[r_id])

        if not matched_parent_ids:
            continue

        if len(matched_parent_ids) > 1:
            # MERGE transition
            for p_id in sorted(matched_parent_ids):
                db.add(
                    GroupLineageModel(
                        id=str(uuid4()),
                        corpus_revision_id=corpus_revision_id,
                        parent_group_id=p_id,
                        child_group_id=child_id,
                        operation=GroupLineageOp.MERGE.value,
                        created_at=utc_now(),
                    )
                )

            # Check decisions of all merged parents
            parent_decisions: list[tuple[str, ReviewEventModel, str]] = []
            for p_id in sorted(matched_parent_ids):
                latest_p_ev = (
                    db.query(ReviewEventModel)
                    .filter_by(group_id=p_id, event_type=DecisionEventType.SCREEN_DECISION.value)
                    .order_by(ReviewEventModel.sequence.desc())
                    .first()
                )
                if latest_p_ev:
                    try:
                        p_data = json.loads(latest_p_ev.payload_json)
                        st = p_data.get("status")
                        if st:
                            parent_decisions.append((p_id, latest_p_ev, st))
                    except (json.JSONDecodeError, TypeError, KeyError):
                        pass

            if len(parent_decisions) >= 2:
                statuses = {d[2] for d in parent_decisions}
                if len(statuses) > 1:
                    # Conflicting parents (e.g. INCLUDE vs EXCLUDE)!
                    conflict = ReviewConflictModel(
                        id=str(uuid4()),
                        corpus_revision_id=corpus_revision_id,
                        group_id=child_id,
                        kind=ConflictKind.DECISION_DIVERGENCE.value,
                        conflicting_event_ids_json=json.dumps([d[1].id for d in parent_decisions]),
                        resolution_event_id=None,
                        created_at=utc_now(),
                    )
                    db.add(conflict)
                else:
                    # Agreeing parents! Carry forward with provenance
                    agreed_status = next(iter(statuses))
                    first_ev = parent_decisions[0][1]
                    existing_child_ev = (
                        db.query(ReviewEventModel)
                        .filter_by(group_id=child_id, event_type=DecisionEventType.SCREEN_DECISION.value)
                        .first()
                    )
                    if not existing_child_ev:
                        seq = get_next_event_sequence(db, ws_id)
                        db.add(
                            ReviewEventModel(
                                id=str(uuid4()),
                                workspace_id=ws_id,
                                group_id=child_id,
                                sequence=seq,
                                event_type=DecisionEventType.SCREEN_DECISION.value,
                                payload_json=json.dumps({
                                    "status": agreed_status,
                                    "inherited": True,
                                    "parent_groups": [d[0] for d in parent_decisions],
                                    "parent_events": [d[1].id for d in parent_decisions],
                                }),
                                actor_id=first_ev.actor_id,
                                reason=first_ev.reason or "Inherited decision from agreeing merged parent groups",
                                supersedes_event_id=first_ev.id,
                                created_at=utc_now(),
                            )
                        )
            elif len(parent_decisions) == 1:
                # Single parent had a decision; carry forward
                p_id, p_ev, st = parent_decisions[0]
                existing_child_ev = (
                    db.query(ReviewEventModel)
                    .filter_by(group_id=child_id, event_type=DecisionEventType.SCREEN_DECISION.value)
                    .first()
                )
                if not existing_child_ev:
                    seq = get_next_event_sequence(db, ws_id)
                    db.add(
                        ReviewEventModel(
                            id=str(uuid4()),
                            workspace_id=ws_id,
                            group_id=child_id,
                            sequence=seq,
                            event_type=DecisionEventType.SCREEN_DECISION.value,
                            payload_json=json.dumps({
                                "status": st,
                                "inherited": True,
                                "parent_group": p_id,
                                "parent_event": p_ev.id,
                            }),
                            actor_id=p_ev.actor_id,
                            reason=p_ev.reason or "Inherited decision from parent group",
                            supersedes_event_id=p_ev.id,
                            created_at=utc_now(),
                        )
                    )

        else:
            # Single parent matched
            single_p_id = next(iter(matched_parent_ids))
            parent_recs = parent_members_map.get(single_p_id, set())

            if child_recs == parent_recs:
                # Retained group
                db.add(
                    GroupLineageModel(
                        id=str(uuid4()),
                        corpus_revision_id=corpus_revision_id,
                        parent_group_id=single_p_id,
                        child_group_id=child_id,
                        operation=GroupLineageOp.RETAIN.value,
                        created_at=utc_now(),
                    )
                )
            elif child_recs > parent_recs:
                # Extended group (new records imported)
                db.add(
                    GroupLineageModel(
                        id=str(uuid4()),
                        corpus_revision_id=corpus_revision_id,
                        parent_group_id=single_p_id,
                        child_group_id=child_id,
                        operation=GroupLineageOp.EXTEND.value,
                        created_at=utc_now(),
                    )
                )
                # Carry forward parent decision if child doesn't have one
                p_ev = (
                    db.query(ReviewEventModel)
                    .filter_by(group_id=single_p_id, event_type=DecisionEventType.SCREEN_DECISION.value)
                    .order_by(ReviewEventModel.sequence.desc())
                    .first()
                )
                if p_ev:
                    existing_child_ev = (
                        db.query(ReviewEventModel)
                        .filter_by(group_id=child_id, event_type=DecisionEventType.SCREEN_DECISION.value)
                        .first()
                    )
                    if not existing_child_ev:
                        try:
                            p_data = json.loads(p_ev.payload_json)
                            st = p_data.get("status")
                            if st:
                                seq = get_next_event_sequence(db, ws_id)
                                db.add(
                                    ReviewEventModel(
                                        id=str(uuid4()),
                                        workspace_id=ws_id,
                                        group_id=child_id,
                                        sequence=seq,
                                        event_type=DecisionEventType.SCREEN_DECISION.value,
                                        payload_json=json.dumps({
                                            "status": st,
                                            "inherited": True,
                                            "parent_group": single_p_id,
                                            "parent_event": p_ev.id,
                                        }),
                                        actor_id=p_ev.actor_id,
                                        reason=p_ev.reason or "Inherited decision from extended parent group",
                                        supersedes_event_id=p_ev.id,
                                        created_at=utc_now(),
                                    )
                                )
                        except (json.JSONDecodeError, TypeError, KeyError):
                            pass
            elif child_recs < parent_recs:
                # Split group
                db.add(
                    GroupLineageModel(
                        id=str(uuid4()),
                        corpus_revision_id=corpus_revision_id,
                        parent_group_id=single_p_id,
                        child_group_id=child_id,
                        operation=GroupLineageOp.SPLIT.value,
                        created_at=utc_now(),
                    )
                )
                # Flag split ambiguity for reaffirmation
                p_ev = (
                    db.query(ReviewEventModel)
                    .filter_by(group_id=single_p_id, event_type=DecisionEventType.SCREEN_DECISION.value)
                    .order_by(ReviewEventModel.sequence.desc())
                    .first()
                )
                if p_ev:
                    db.add(
                        ReviewConflictModel(
                            id=str(uuid4()),
                            corpus_revision_id=corpus_revision_id,
                            group_id=child_id,
                            kind=ConflictKind.SPLIT_AMBIGUITY.value,
                            conflicting_event_ids_json=json.dumps([p_ev.id]),
                            resolution_event_id=None,
                            created_at=utc_now(),
                        )
                    )

    db.flush()


def compute_corpus_diff(
    db: Session,
    base_revision_id: str,
    target_revision_id: str,
) -> CorpusDiffResponse:
    """Calculate structured diff between two immutable corpus snapshots."""
    from app.services.corpus import project_effective_group_decision

    base_rev = db.query(CorpusRevisionModel).filter_by(id=base_revision_id).first()
    if not base_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Base corpus revision '{base_revision_id}' not found",
        )

    target_rev = db.query(CorpusRevisionModel).filter_by(id=target_revision_id).first()
    if not target_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target corpus revision '{target_revision_id}' not found",
        )

    # 1. Compare records
    base_members = db.query(CorpusMemberModel).filter_by(corpus_revision_id=base_revision_id).all()
    base_record_ids = {m.source_record_id for m in base_members}

    target_members = db.query(CorpusMemberModel).filter_by(corpus_revision_id=target_revision_id).all()
    target_record_ids = {m.source_record_id for m in target_members}

    added_rec_ids = sorted(target_record_ids - base_record_ids)
    removed_rec_ids = sorted(base_record_ids - target_record_ids)
    retained_rec_ids = target_record_ids & base_record_ids

    # 2. Compare groups and representatives
    base_snapshots = db.query(GroupSnapshotModel).filter_by(corpus_revision_id=base_revision_id).all()
    base_groups = {s.group_id: s.representative_revision_id for s in base_snapshots}

    target_snapshots = db.query(GroupSnapshotModel).filter_by(corpus_revision_id=target_revision_id).all()
    target_groups = {s.group_id: s.representative_revision_id for s in target_snapshots}

    added_groups = len(set(target_groups.keys()) - set(base_groups.keys()))
    removed_groups = len(set(base_groups.keys()) - set(target_groups.keys()))
    common_groups = set(base_groups.keys()) & set(target_groups.keys())

    rep_changes = sum(1 for g in common_groups if base_groups[g] != target_groups[g])

    # 3. Lineage transitions
    lineages = db.query(GroupLineageModel).filter_by(corpus_revision_id=target_revision_id).all()
    merged_groups = len({l.child_group_id for l in lineages if l.operation == GroupLineageOp.MERGE.value})
    split_groups = len({l.child_group_id for l in lineages if l.operation == GroupLineageOp.SPLIT.value})

    # 4. Changed decisions
    changed_decisions = 0
    for g in common_groups:
        st_base, _, _, _ = project_effective_group_decision(db, g, revision_id=base_revision_id)
        st_target, _, _, _ = project_effective_group_decision(db, g, revision_id=target_revision_id)
        if st_base != st_target:
            changed_decisions += 1

    # 5. Conflicts
    conflicts_count = (
        db.query(ReviewConflictModel)
        .filter_by(corpus_revision_id=target_revision_id, resolution_event_id=None)
        .count()
    )

    # 6. Invalidation fingerprint
    invalidation_str = (
        f"{base_revision_id}:{target_revision_id}:{','.join(added_rec_ids)}:"
        f"{','.join(removed_rec_ids)}:{merged_groups}:{split_groups}:{target_rev.criteria_version_id}"
    )
    inv_fingerprint = hashlib.sha256(invalidation_str.encode("utf-8")).hexdigest()

    return CorpusDiffResponse(
        base_revision_id=base_revision_id,
        target_revision_id=target_revision_id,
        added_groups=added_groups,
        removed_groups=removed_groups,
        merged_groups=merged_groups,
        split_groups=split_groups,
        changed_decisions=changed_decisions,
        conflicts_count=conflicts_count,
        added_records=len(added_rec_ids),
        removed_records=len(removed_rec_ids),
        retained_records=len(retained_rec_ids),
        representative_changes=rep_changes,
        invalidation_fingerprint=inv_fingerprint,
        added_record_ids=added_rec_ids,
        removed_record_ids=removed_rec_ids,
    )


def restore_corpus_snapshot(
    db: Session,
    workspace_id: str,
    snapshot_id: str,
    mode: RestoreMode = RestoreMode.EXACT_SNAPSHOT,
    expected_workspace_version: int | None = None,
) -> CorpusRevisionResponse:
    """Restore exact historical corpus snapshot without re-fetching APIs or rerunning algorithms.

    Invariants:
    1. Reopens saved record revisions, partition, representatives, and criteria exactly.
    2. Zero external network calls or LLM invocations.
    3. Failed restores or stale version checks leave workspace untouched.
    4. Appends later reviewer edits rather than mutating history.
    """
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    snapshot = (
        db.query(CorpusRevisionModel)
        .filter_by(id=snapshot_id, workspace_id=workspace_id)
        .first()
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus revision snapshot '{snapshot_id}' not found in workspace",
        )

    if snapshot.state != CorpusRevisionState.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot restore snapshot '{snapshot_id}': state is '{snapshot.state}', expected 'published'",
        )

    if expected_workspace_version is not None and ws.row_version != expected_workspace_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"STALE_VERSION_CONFLICT: Expected workspace version {expected_workspace_version} "
                f"does not match current version {ws.row_version}"
            ),
        )

    # Perform atomic restore update
    ws.current_revision_id = snapshot.id
    ws.row_version += 1
    db.commit()
    db.refresh(snapshot)

    return CorpusRevisionResponse(
        id=snapshot.id,
        workspace_id=snapshot.workspace_id,
        parent_id=snapshot.parent_id,
        criteria_version_id=snapshot.criteria_version_id,
        dedup_version=snapshot.dedup_version,
        state=CorpusRevisionState(snapshot.state),
        published_at=snapshot.published_at,
        decision_seq_cutoff=snapshot.decision_seq_cutoff,
        fingerprint=snapshot.fingerprint,
        group_count=snapshot.group_count,
        record_count=snapshot.record_count,
    )
