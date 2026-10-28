"""Duplicate Genealogy & Decision Reconciliation domain service."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    DedupEdgeStatus,
    DuplicateConflictClassification,
    DuplicateMergeOperation,
    DuplicateRelationshipStatus,
    EffectiveDecisionState,
    EligibilityStatus,
    GroupLineageOp,
    SourceNamespace,
)
from app.contracts.models import (
    DecisionConflictDetail,
    DuplicateGroupGenealogyResponse,
    DuplicateMatchSignalDetail,
    DuplicateMergeHistoryItem,
    DuplicateReconcileRequest,
    DuplicateRecordMemberDetail,
    DuplicateReverseMergeRequest,
    DuplicateSplitRequest,
    DuplicateWorkspaceSummaryItem,
    DuplicateWorkspaceSummaryResponse,
    FieldProvenanceItem,
    RecordRevisionResponse,
)
from app.db.models import (
    DedupEdgeModel,
    DuplicateMergeEventModel,
    GroupLineageModel,
    GroupMemberModel,
    GroupSnapshotModel,
    MachineResultModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewConflictModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.dedup.matcher import find_candidate_pairs
from app.dedup.normalization import normalize_doi, normalize_pmid, normalize_title
from app.dedup.partitioner import select_group_representative
from app.services.corpus import project_effective_group_decision

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def _get_next_event_sequence(db: Session, workspace_id: str) -> int:
    """Get next monotonically increasing event sequence for workspace."""
    max_seq = (
        db.query(func.max(ReviewEventModel.sequence))
        .filter_by(workspace_id=workspace_id)
        .scalar()
    )
    return (max_seq or 0) + 1


def _safe_json_list(val: str | None) -> list[str]:
    """Safely deserialize JSON array or return empty list."""
    if not val:
        return []
    try:
        data = json.loads(val)
        return data if isinstance(data, list) else [str(data)]
    except (json.JSONDecodeError, TypeError):
        return [val]


def get_duplicate_group_genealogy(
    db: Session,
    workspace_id: str,
    group_id: str,
) -> DuplicateGroupGenealogyResponse:
    """Compile comprehensive duplicate genealogy, matching evidence, conflicts, and field provenance."""
    group = (
        db.query(PaperGroupModel)
        .filter_by(id=group_id, workspace_id=workspace_id)
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found in workspace '{workspace_id}'",
        )

    # 1. Fetch all members and their latest record revisions
    member_links = (
        db.query(GroupMemberModel, SourceRecordModel)
        .join(SourceRecordModel, SourceRecordModel.id == GroupMemberModel.source_record_id)
        .filter(GroupMemberModel.group_id == group_id)
        .all()
    )
    if not member_links:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No source records associated with paper group '{group_id}'",
        )

    source_ids = [m[1].id for m in member_links]
    source_map = {m[1].id: m[1] for m in member_links}

    # Fetch latest revisions for each source record
    revisions = (
        db.query(RecordRevisionModel)
        .filter(RecordRevisionModel.source_record_id.in_(source_ids))
        .order_by(RecordRevisionModel.fetched_at.desc())
        .all()
    )
    rev_by_source: dict[str, RecordRevisionModel] = {}
    for r in revisions:
        if r.source_record_id not in rev_by_source:
            rev_by_source[r.source_record_id] = r

    # Determine canonical / representative record
    # Check if a snapshot exists
    snapshot = (
        db.query(GroupSnapshotModel)
        .filter_by(group_id=group_id)
        .order_by(GroupSnapshotModel.created_at.desc())
        .first()
    )
    canonical_rev_id = snapshot.representative_revision_id if snapshot else None

    # Convert revisions to RecordRevisionResponse for deterministic tie-breaker if needed
    domain_records: list[RecordRevisionResponse] = []
    for s_id, s_rec in source_map.items():
        r = rev_by_source.get(s_id)
        if r:
            try:
                src_ns = SourceNamespace(s_rec.source)
            except ValueError:
                src_ns = SourceNamespace.PUBMED

            domain_records.append(
                RecordRevisionResponse(
                    id=r.id,
                    source_record_id=s_id,
                    source=src_ns,
                    source_namespace=s_rec.source_namespace or s_rec.source,
                    external_id=s_rec.external_id,
                    content_hash=r.content_hash,
                    title=r.title or "",
                    abstract_text=r.abstract_text,
                    authors=_safe_json_list(r.authors_json),
                    year=r.year,
                    journal=r.journal,
                    doi=r.doi,
                    pmid=r.pmid,
                    publication_types=[],
                    fetched_at=r.fetched_at,
                )
            )

    if not canonical_rev_id and domain_records:
        canonical_dto = select_group_representative(domain_records)
        canonical_rev_id = canonical_dto.id

    # 2. Compile member details & individual decisions
    members: list[DuplicateRecordMemberDetail] = []
    eff_state, latest_group_event, screen_res, has_conflict = project_effective_group_decision(db, group_id)

    # Fetch individual screening events across group
    group_events = (
        db.query(ReviewEventModel)
        .filter_by(group_id=group_id)
        .order_by(ReviewEventModel.sequence.asc())
        .all()
    )

    for d_rec in domain_records:
        is_canonical = (d_rec.id == canonical_rev_id)

        # Check decision provenance
        indiv_status = "unscreened"
        dec_source = "none"
        dec_reason = None
        dec_by = None
        dec_at = None

        # Check for latest group-level conflict resolution event
        latest_res_event = None
        for ge in reversed(group_events):
            if ge.event_type == DecisionEventType.CONFLICT_RESOLUTION.value:
                latest_res_event = ge
                break

        # Check for review events specifically targeting this source record first
        found_target_event = False
        for ge in reversed(group_events):
            if latest_res_event and ge.sequence < latest_res_event.sequence:
                break
            try:
                pl = json.loads(ge.payload_json)
                target_rec = pl.get("source_record_id") or pl.get("record_id")
                if target_rec == d_rec.source_record_id:
                    st = pl.get("status") or pl.get("chosen_status") or pl.get("decision")
                    if st:
                        indiv_status = st
                        dec_source = pl.get("actor_type") or ("human" if ge.actor_id != "system" else "automated")
                        dec_reason = ge.reason or pl.get("reason")
                        dec_by = ge.actor_id
                        dec_at = ge.created_at
                        found_target_event = True
                        break
            except (json.JSONDecodeError, ValueError):
                continue

        if not found_target_event:
            if latest_res_event:
                try:
                    pl = json.loads(latest_res_event.payload_json)
                    st = pl.get("status") or pl.get("chosen_status")
                    if st:
                        indiv_status = st
                        dec_source = "human"
                        dec_reason = latest_res_event.reason
                        dec_by = latest_res_event.actor_id
                        dec_at = latest_res_event.created_at
                except (json.JSONDecodeError, ValueError):
                    pass
            elif latest_group_event:
                try:
                    pl = json.loads(latest_group_event.payload_json)
                    st = pl.get("status") or pl.get("chosen_status")
                    if st:
                        indiv_status = st
                        dec_source = "human"
                        dec_reason = latest_group_event.reason
                        dec_by = latest_group_event.actor_id
                        dec_at = latest_group_event.created_at
                except (json.JSONDecodeError, ValueError):
                    pass
            elif screen_res:
                indiv_status = screen_res.status.value
                dec_source = "automated"
                dec_reason = screen_res.rationale

        members.append(
            DuplicateRecordMemberDetail(
                source_record_id=d_rec.source_record_id,
                record_revision_id=d_rec.id,
                external_id=d_rec.external_id,
                source_namespace=d_rec.source,
                title=d_rec.title,
                authors=d_rec.authors,
                year=d_rec.year,
                doi=d_rec.doi,
                pmid=d_rec.pmid,
                journal=d_rec.journal,
                abstract_text=d_rec.abstract_text,
                is_canonical=is_canonical,
                individual_decision=indiv_status,
                decision_source=dec_source,
                decision_rationale=dec_reason,
                decision_by=dec_by,
                decision_at=dec_at,
            )
        )

    # 3. Compile Pairwise Match Signals
    pairwise_signals: list[DuplicateMatchSignalDetail] = []
    edges = (
        db.query(DedupEdgeModel)
        .filter(DedupEdgeModel.workspace_id == workspace_id)
        .filter(
            (DedupEdgeModel.record_id_a.in_(source_ids))
            | (DedupEdgeModel.record_id_b.in_(source_ids))
        )
        .all()
    )

    seen_pairs: set[tuple[str, str]] = set()

    for edge in edges:
        if edge.record_id_a in source_ids and edge.record_id_b in source_ids:
            pair = (edge.record_id_a, edge.record_id_b)
            rev_pair = (edge.record_id_b, edge.record_id_a)
            if pair in seen_pairs or rev_pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            try:
                ev_data = json.loads(edge.evidence_json)
            except (json.JSONDecodeError, TypeError):
                ev_data = {}

            signals_list: list[str] = []
            if isinstance(ev_data, dict):
                if ev_data.get("exact_doi"):
                    signals_list.append(f"Exact DOI Match ({ev_data.get('exact_doi')})")
                if ev_data.get("exact_pmid"):
                    signals_list.append(f"Exact PMID Match ({ev_data.get('exact_pmid')})")
                if ev_data.get("title_similarity", 0) >= 0.95:
                    signals_list.append(f"Normalized Title Match ({round(ev_data.get('title_similarity', 1.0)*100)}%)")
                if ev_data.get("author_token_overlap"):
                    signals_list.append("Author Token Overlap")
                if ev_data.get("year_match"):
                    signals_list.append("Publication Year Agreement")
                if ev_data.get("manual_override"):
                    signals_list.append(f"Human Override: {ev_data.get('reason', 'Confirmed duplicate')}")

            if not signals_list:
                signals_list.append(f"Score {round(edge.score * 100)}% via {edge.method_version}")

            pairwise_signals.append(
                DuplicateMatchSignalDetail(
                    record_id_a=edge.record_id_a,
                    record_id_b=edge.record_id_b,
                    score=edge.score,
                    status=DuplicateRelationshipStatus(edge.status),
                    signals=signals_list,
                    evidence_detail=ev_data if isinstance(ev_data, dict) else {},
                )
            )

    # If members > 1 and no persisted edge, run matcher to provide actual signals
    if len(domain_records) > 1 and not pairwise_signals:
        computed_cands = find_candidate_pairs(domain_records)
        for cand in computed_cands:
            signals_list = []
            if cand.evidence.get("exact_doi"):
                signals_list.append(f"Exact DOI Match ({cand.evidence.get('exact_doi')})")
            if cand.evidence.get("exact_pmid"):
                signals_list.append(f"Exact PMID Match ({cand.evidence.get('exact_pmid')})")
            if cand.evidence.get("title_similarity", 0) >= 0.95:
                signals_list.append(f"Normalized Title Match ({round(cand.evidence.get('title_similarity', 1.0)*100)}%)")
            if not signals_list:
                signals_list.append(f"Deterministic Match Score {round(cand.score * 100)}%")

            pairwise_signals.append(
                DuplicateMatchSignalDetail(
                    record_id_a=cand.record_id_a,
                    record_id_b=cand.record_id_b,
                    score=cand.score,
                    status=DuplicateRelationshipStatus.PROBABLE if cand.score >= 0.85 else DuplicateRelationshipStatus.POSSIBLE,
                    signals=signals_list,
                    evidence_detail=cand.evidence,
                )
            )

    # 4. Detect Decision Conflicts
    active_conflicts: list[DecisionConflictDetail] = []
    db_conflicts = (
        db.query(ReviewConflictModel)
        .filter_by(group_id=group_id, resolution_event_id=None)
        .all()
    )

    for c in db_conflicts:
        try:
            ev_ids = json.loads(c.conflicting_event_ids_json)
        except (json.JSONDecodeError, TypeError):
            ev_ids = []

        competing_events = (
            db.query(ReviewEventModel)
            .filter(ReviewEventModel.id.in_(ev_ids))
            .all()
        )
        comp_decisions = []
        for ce in competing_events:
            try:
                pl = json.loads(ce.payload_json)
                st = pl.get("status") or pl.get("chosen_status")
            except (json.JSONDecodeError, ValueError):
                st = "unknown"
            comp_decisions.append({
                "event_id": ce.id,
                "status": st,
                "actor_id": ce.actor_id,
                "reason": ce.reason,
                "created_at": ce.created_at.isoformat(),
            })

        active_conflicts.append(
            DecisionConflictDetail(
                conflict_id=c.id,
                classification=DuplicateConflictClassification(c.kind) if c.kind in [e.value for e in DuplicateConflictClassification] else DuplicateConflictClassification.DECISION_DIVERGENCE,
                affected_records=source_ids,
                competing_decisions=comp_decisions,
                explanation=f"Conflicting decisions detected across parent groups for duplicate records in {group_id}.",
                is_resolved=False,
            )
        )

    # Check for un-materialized divergence (e.g. human said include, ML said exclude)
    if not active_conflicts and screen_res and latest_group_event:
        try:
            pl = json.loads(latest_group_event.payload_json)
            h_stat = pl.get("status") or pl.get("chosen_status")
            if h_stat and screen_res.status and h_stat != screen_res.status.value:
                active_conflicts.append(
                    DecisionConflictDetail(
                        conflict_id=None,
                        classification=DuplicateConflictClassification.AUTOMATED_VS_HUMAN,
                        affected_records=source_ids,
                        competing_decisions=[
                            {"source": "human", "status": h_stat, "actor_id": latest_group_event.actor_id, "reason": latest_group_event.reason},
                            {"source": "automated", "status": screen_res.status.value, "actor_id": screen_res.method_version, "reason": screen_res.rationale},
                        ],
                        explanation=f"Human reviewer decision ({h_stat.upper()}) differs from automated machine suggestion ({screen_res.status.value.upper()}).",
                        is_resolved=True,  # Resolved because human decision strictly supersedes machine suggestion
                        resolution=f"Human decision ({h_stat.upper()}) strictly supersedes machine suggestion.",
                        resolved_by=latest_group_event.actor_id,
                        resolved_at=latest_group_event.created_at,
                    )
                )
        except (json.JSONDecodeError, ValueError):
            pass

    # 5. Field-Level Metadata Provenance
    canonical_rec = next((m for m in members if m.is_canonical), members[0] if members else None)
    field_provenance: list[FieldProvenanceItem] = []

    if canonical_rec:
        fields_to_compare = [
            ("title", canonical_rec.title, "Title"),
            ("doi", canonical_rec.doi, "DOI"),
            ("pmid", canonical_rec.pmid, "PMID"),
            ("authors", ", ".join(canonical_rec.authors), "Authors"),
            ("year", str(canonical_rec.year) if canonical_rec.year else None, "Publication Year"),
            ("journal", canonical_rec.journal, "Journal"),
            ("abstract", (canonical_rec.abstract_text[:120] + "...") if canonical_rec.abstract_text else None, "Abstract"),
        ]

        for f_name, canon_val, label in fields_to_compare:
            alternatives = []
            has_discrepancy = False

            for other in members:
                if other.source_record_id == canonical_rec.source_record_id:
                    continue

                if f_name == "title":
                    other_val = other.title
                elif f_name == "doi":
                    other_val = other.doi
                elif f_name == "pmid":
                    other_val = other.pmid
                elif f_name == "authors":
                    other_val = ", ".join(other.authors)
                elif f_name == "year":
                    other_val = str(other.year) if other.year else None
                elif f_name == "journal":
                    other_val = other.journal
                else:
                    other_val = (other.abstract_text[:120] + "...") if other.abstract_text else None

                alternatives.append({
                    "source_record_id": other.source_record_id,
                    "source": other.source_namespace,
                    "external_id": other.external_id,
                    "value": other_val,
                })

                if canon_val and other_val and canon_val.strip().lower() != other_val.strip().lower():
                    has_discrepancy = True

            field_provenance.append(
                FieldProvenanceItem(
                    field_name=label,
                    canonical_value=canon_val,
                    canonical_source=canonical_rec.source_namespace,
                    source_record_id=canonical_rec.source_record_id,
                    alternatives=alternatives,
                    has_discrepancy=has_discrepancy,
                )
            )

    # 6. Merge & Split History
    merge_history: list[DuplicateMergeHistoryItem] = []
    merge_events = (
        db.query(DuplicateMergeEventModel)
        .filter_by(group_id=group_id)
        .order_by(DuplicateMergeEventModel.created_at.desc())
        .all()
    )

    for me in merge_events:
        merge_history.append(
            DuplicateMergeHistoryItem(
                event_id=me.id,
                operation=DuplicateMergeOperation(me.operation) if me.operation in [e.value for e in DuplicateMergeOperation] else DuplicateMergeOperation.MERGE,
                affected_source_ids=_safe_json_list(me.affected_source_ids_json),
                canonical_record_id=me.canonical_record_id,
                actor_id=me.actor_id,
                reason=me.reason,
                timestamp=me.created_at,
                can_reverse=(me.status == "active"),
                reversal_blockers=[] if me.status == "active" else ["Merge event has already been reversed or superseded."],
                is_reversed=(me.status == "reversed"),
            )
        )

    # Also include GroupLineageModel records if any
    lineage_records = (
        db.query(GroupLineageModel)
        .filter((GroupLineageModel.child_group_id == group_id) | (GroupLineageModel.parent_group_id == group_id))
        .all()
    )
    for lin in lineage_records:
        if not any(mh.event_id == lin.id for mh in merge_history):
            merge_history.append(
                DuplicateMergeHistoryItem(
                    event_id=lin.id,
                    operation=DuplicateMergeOperation.MERGE if lin.operation == "merge" else DuplicateMergeOperation.SPLIT,
                    affected_source_ids=source_ids,
                    canonical_record_id=canonical_rev_id,
                    actor_id="system:corpus_processor",
                    reason=f"Lineage transition: {lin.operation} across corpus revisions",
                    timestamp=lin.created_at,
                    can_reverse=False,
                    reversal_blockers=["Historical revision lineage cannot be reversed without snapshot restore."],
                    is_reversed=False,
                )
            )

    return DuplicateGroupGenealogyResponse(
        group_id=group.id,
        workspace_id=workspace_id,
        canonical_record_id=canonical_rec.source_record_id if canonical_rec else source_ids[0],
        membership_fingerprint=group.membership_fingerprint,
        row_version=group.row_version,
        effective_decision=eff_state.value,
        members=members,
        pairwise_signals=pairwise_signals,
        active_conflicts=active_conflicts,
        field_provenance=field_provenance,
        merge_history=merge_history,
    )


def get_workspace_duplicate_overview(
    db: Session,
    workspace_id: str,
    conflict_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> DuplicateWorkspaceSummaryResponse:
    """Retrieve workspace overview of duplicate groups, conflict ledger, and candidate pairs."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # 1. Count duplicate groups (groups with member count > 1)
    dup_group_counts = (
        db.query(GroupMemberModel.group_id, func.count(GroupMemberModel.source_record_id).label("m_count"))
        .join(PaperGroupModel, PaperGroupModel.id == GroupMemberModel.group_id)
        .filter(PaperGroupModel.workspace_id == workspace_id)
        .group_by(GroupMemberModel.group_id)
        .having(func.count(GroupMemberModel.source_record_id) > 1)
        .all()
    )

    dup_group_ids = [row[0] for row in dup_group_counts]
    total_dup_groups = len(dup_group_ids)
    total_dup_records = sum(row[1] for row in dup_group_counts)

    # 2. Count active and resolved conflicts
    active_conflicts_query = (
        db.query(ReviewConflictModel)
        .filter(ReviewConflictModel.group_id.in_(dup_group_ids))
        .filter(ReviewConflictModel.resolution_event_id.is_(None))
        .all()
    )
    groups_with_conflicts = len(set(c.group_id for c in active_conflicts_query))

    resolved_conflicts_count = (
        db.query(ReviewConflictModel)
        .filter(ReviewConflictModel.group_id.in_(dup_group_ids))
        .filter(ReviewConflictModel.resolution_event_id.is_not(None))
        .count()
    )

    # 3. Count pending candidate pairs in dedup_edges
    pending_edges_count = (
        db.query(DedupEdgeModel)
        .filter_by(workspace_id=workspace_id, status=DedupEdgeStatus.PROPOSED.value)
        .count()
    )

    # 4. Build summary items for duplicate groups
    summary_items: list[DuplicateWorkspaceSummaryItem] = []

    for grp_id, m_count in dup_group_counts:
        has_conf = any(c.group_id == grp_id for c in active_conflicts_query)
        if conflict_only and not has_conf:
            continue

        conf_types = [c.kind for c in active_conflicts_query if c.group_id == grp_id]

        grp = db.query(PaperGroupModel).filter_by(id=grp_id).first()
        eff_state, _, _, _ = project_effective_group_decision(db, grp_id)

        # Get representative title & sources
        members = (
            db.query(SourceRecordModel, RecordRevisionModel)
            .join(GroupMemberModel, GroupMemberModel.source_record_id == SourceRecordModel.id)
            .join(RecordRevisionModel, RecordRevisionModel.source_record_id == SourceRecordModel.id)
            .filter(GroupMemberModel.group_id == grp_id)
            .all()
        )
        sources = list(set(m[0].source for m in members))
        title = members[0][1].title if members and members[0][1].title else "Untitled Study"

        summary_items.append(
            DuplicateWorkspaceSummaryItem(
                group_id=grp_id,
                canonical_title=title,
                member_count=m_count,
                sources=sources,
                effective_decision=eff_state.value,
                has_unresolved_conflict=has_conf,
                conflict_types=conf_types,
                confidence_label="Confirmed" if not has_conf else "Needs Review",
                created_at=grp.created_at if grp else utc_now(),
            )
        )

    paginated = summary_items[offset : offset + limit]

    return DuplicateWorkspaceSummaryResponse(
        workspace_id=workspace_id,
        total_duplicate_groups=total_dup_groups,
        total_duplicate_records=total_dup_records,
        groups_with_conflicts=groups_with_conflicts,
        resolved_conflicts_count=resolved_conflicts_count,
        pending_candidate_pairs=pending_edges_count,
        groups=paginated,
    )


def reconcile_duplicate_conflict(
    db: Session,
    workspace_id: str,
    group_id: str,
    payload: DuplicateReconcileRequest,
) -> DuplicateGroupGenealogyResponse:
    """Safely reconcile conflicting decisions across duplicate records with full audit trail."""
    group = (
        db.query(PaperGroupModel)
        .filter_by(id=group_id, workspace_id=workspace_id)
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found",
        )

    # 1. Concurrency Check
    if group.row_version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"STALE_VERSION_CONFLICT: Expected version {payload.expected_version} does not match current version {group.row_version}",
        )

    # 2. Append review event
    seq = _get_next_event_sequence(db, workspace_id)
    event = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.CONFLICT_RESOLUTION.value,
        payload_json=json.dumps({
            "status": payload.chosen_decision.value,
            "chosen_status": payload.chosen_decision.value,
            "reconciliation": True,
            "apply_to_all_members": payload.apply_to_all_members,
        }),
        reason=payload.reason,
        created_at=utc_now(),
    )
    db.add(event)
    db.flush()

    # 3. Resolve active conflicts in ReviewConflictModel
    active_conflicts = (
        db.query(ReviewConflictModel)
        .filter_by(group_id=group_id, resolution_event_id=None)
        .all()
    )
    for c in active_conflicts:
        c.resolution_event_id = event.id

    # 4. Log DuplicateMergeEventModel
    member_ids = [
        m.source_record_id
        for m in db.query(GroupMemberModel).filter_by(group_id=group_id).all()
    ]
    merge_event = DuplicateMergeEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group.id,
        canonical_record_id=member_ids[0] if member_ids else None,
        operation=DuplicateMergeOperation.RECONCILIATION.value,
        affected_source_ids_json=json.dumps(member_ids),
        match_evidence_json=json.dumps({"reconciled_decision": payload.chosen_decision.value}),
        actor_id=payload.actor_id,
        reason=payload.reason,
        status="active",
        created_at=utc_now(),
    )
    db.add(merge_event)

    group.row_version += 1
    db.commit()

    return get_duplicate_group_genealogy(db, workspace_id, group_id)


def split_duplicate_group(
    db: Session,
    workspace_id: str,
    group_id: str,
    payload: DuplicateSplitRequest,
) -> DuplicateGroupGenealogyResponse:
    """Safely split one or more records out of a duplicate group into an independent group."""
    group = (
        db.query(PaperGroupModel)
        .filter_by(id=group_id, workspace_id=workspace_id)
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found",
        )

    if group.row_version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"STALE_VERSION_CONFLICT: Expected version {payload.expected_version} does not match current version {group.row_version}",
        )

    current_members = (
        db.query(GroupMemberModel)
        .filter_by(group_id=group_id)
        .all()
    )
    current_source_ids = [m.source_record_id for m in current_members]

    # Validate split IDs
    for sid in payload.source_record_ids_to_split:
        if sid not in current_source_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Source record '{sid}' is not a member of duplicate group '{group_id}'",
            )

    remaining_ids = [sid for sid in current_source_ids if sid not in payload.source_record_ids_to_split]
    if not remaining_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot split all records out of group; at least one member must remain.",
        )

    # 1. Create new group for split records
    new_group_id = f"grp-{uuid4().hex[:12]}"
    new_fp = hashlib.sha256(",".join(sorted(payload.source_record_ids_to_split)).encode()).hexdigest()
    new_group = PaperGroupModel(
        id=new_group_id,
        workspace_id=workspace_id,
        membership_fingerprint=new_fp,
        row_version=1,
        created_at=utc_now(),
    )
    db.add(new_group)
    db.flush()

    # 2. Re-assign member records
    for m in current_members:
        if m.source_record_id in payload.source_record_ids_to_split:
            db.delete(m)
            db.add(GroupMemberModel(group_id=new_group_id, source_record_id=m.source_record_id))

    # Update original group fingerprint
    group.membership_fingerprint = hashlib.sha256(",".join(sorted(remaining_ids)).encode()).hexdigest()

    # 3. Enforce cannot-link constraints if requested
    if payload.mark_as_cannot_link:
        for rem_id in remaining_ids:
            for split_id in payload.source_record_ids_to_split:
                existing_edge = (
                    db.query(DedupEdgeModel)
                    .filter_by(workspace_id=workspace_id, record_id_a=rem_id, record_id_b=split_id)
                    .first()
                )
                if not existing_edge:
                    existing_edge = (
                        db.query(DedupEdgeModel)
                        .filter_by(workspace_id=workspace_id, record_id_a=split_id, record_id_b=rem_id)
                        .first()
                    )

                if existing_edge:
                    existing_edge.status = DedupEdgeStatus.REJECTED.value
                    try:
                        ev_map = json.loads(existing_edge.evidence_json or "{}")
                    except (json.JSONDecodeError, TypeError):
                        ev_map = {}
                    ev_map["cannot_link"] = True
                    ev_map["reason"] = payload.reason
                    existing_edge.evidence_json = json.dumps(ev_map)
                else:
                    db.add(
                        DedupEdgeModel(
                            id=str(uuid4()),
                            workspace_id=workspace_id,
                            record_id_a=rem_id,
                            record_id_b=split_id,
                            score=0.0,
                            method_version="human_split:v1.0.0",
                            evidence_json=json.dumps({"cannot_link": True, "reason": payload.reason}),
                            status=DedupEdgeStatus.REJECTED.value,
                            created_at=utc_now(),
                        )
                    )

    # 4. Audit events
    seq = _get_next_event_sequence(db, workspace_id)
    split_event = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.MERGE_SPLIT.value,
        payload_json=json.dumps({
            "split_group_id": new_group_id,
            "split_records": payload.source_record_ids_to_split,
            "remaining_records": remaining_ids,
            "reason": payload.reason,
        }),
        reason=payload.reason,
        created_at=utc_now(),
    )
    db.add(split_event)

    merge_event = DuplicateMergeEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group.id,
        canonical_record_id=remaining_ids[0],
        operation=DuplicateMergeOperation.SPLIT.value,
        affected_source_ids_json=json.dumps(payload.source_record_ids_to_split),
        match_evidence_json=json.dumps({"new_group_id": new_group_id}),
        actor_id=payload.actor_id,
        reason=payload.reason,
        status="active",
        created_at=utc_now(),
    )
    db.add(merge_event)

    group.row_version += 1
    db.commit()

    return get_duplicate_group_genealogy(db, workspace_id, group_id)


def reverse_merge_event(
    db: Session,
    workspace_id: str,
    group_id: str,
    payload: DuplicateReverseMergeRequest,
) -> DuplicateGroupGenealogyResponse:
    """Safely reverse an earlier merge operation without deleting historical records."""
    group = (
        db.query(PaperGroupModel)
        .filter_by(id=group_id, workspace_id=workspace_id)
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found",
        )

    if group.row_version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"STALE_VERSION_CONFLICT: Expected version {payload.expected_version} does not match current version {group.row_version}",
        )

    merge_event = db.query(DuplicateMergeEventModel).filter_by(id=payload.merge_event_id, group_id=group_id).first()
    if not merge_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merge event '{payload.merge_event_id}' not found for group '{group_id}'",
        )

    if merge_event.status == "reversed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merge event has already been reversed.",
        )

    affected_ids = _safe_json_list(merge_event.affected_source_ids_json)

    # Reversal action: separate non-canonical affected records into their own independent groups
    current_members = db.query(GroupMemberModel).filter_by(group_id=group_id).all()
    if len(current_members) > 1 and affected_ids:
        canonical_id = current_members[0].source_record_id
        for m in current_members[1:]:
            if m.source_record_id in affected_ids:
                new_grp_id = f"pg-{uuid4().hex[:12]}"
                new_grp = PaperGroupModel(
                    id=new_grp_id,
                    workspace_id=workspace_id,
                    membership_fingerprint=hashlib.sha256(m.source_record_id.encode()).hexdigest(),
                    row_version=1,
                    created_at=utc_now(),
                )
                db.add(new_grp)
                db.flush()
                db.delete(m)
                db.add(GroupMemberModel(group_id=new_grp_id, source_record_id=m.source_record_id))

        group.membership_fingerprint = hashlib.sha256(canonical_id.encode()).hexdigest()

    # Mark event as reversed
    merge_event.status = "reversed"
    merge_event.reversal_event_id = str(uuid4())

    # Log audit event
    seq = _get_next_event_sequence(db, workspace_id)
    rev_event = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.MERGE_REVERSAL.value,
        payload_json=json.dumps({
            "reversed_merge_id": merge_event.id,
            "affected_records": affected_ids,
            "reason": payload.reason,
        }),
        reason=payload.reason,
        created_at=utc_now(),
    )
    db.add(rev_event)

    group.row_version += 1
    db.commit()

    return get_duplicate_group_genealogy(db, workspace_id, group_id)
