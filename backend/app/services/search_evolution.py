"""Search Evolution Time Machine domain service.

Tracks how search strategies and retrieved literature evolve across versions.
Provides deterministic field-level diffs, screening decision carryover preservation,
absence-without-deletion tracking, and non-destructive query configuration restoration.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    EffectiveDecisionState,
    JobState,
    SearchEvolutionCategory,
    SourceNamespace,
)
from app.contracts.models import (
    QueryASTNode,
    QueryVersionResponse,
    SearchEvolutionDiffResponse,
    SearchEvolutionDiffSummary,
    SearchEvolutionMetadataFieldDiff,
    SearchEvolutionRecordDiff,
    SearchEvolutionVersionSummary,
    SearchExecutionResponse,
    SearchRestoreResponse,
)
from app.db.models import (
    GroupMemberModel,
    PaperGroupModel,
    QueryMembershipModel,
    QueryVersionModel,
    RecordRevisionModel,
    ReviewConflictModel,
    ReviewEventModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def _safe_json_list(val: str | None) -> list[str]:
    """Safely deserialize a JSON array or return empty list."""
    if not val:
        return []
    try:
        res = json.loads(val)
        return res if isinstance(res, list) else []
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def _resolve_record_screening_state(
    db: Session,
    source_record_id: str,
) -> tuple[EffectiveDecisionState, str | None, str | None]:
    """Resolve the active screening decision for a source record via its paper group.

    Returns:
        (decision_state, decision_reason, preserved_from_version_id)
    """
    # 1. Locate paper group membership
    member = (
        db.query(GroupMemberModel)
        .filter_by(source_record_id=source_record_id)
        .first()
    )
    if not member:
        return EffectiveDecisionState.UNSCREENED, None, None

    group_id = member.group_id

    # 2. Check for active review conflict
    conflict = (
        db.query(ReviewConflictModel)
        .filter(ReviewConflictModel.group_id == group_id, ReviewConflictModel.resolution_event_id.is_(None))
        .first()
    )
    if conflict:
        return EffectiveDecisionState.CONFLICT, f"Unresolved conflict: {conflict.kind}", None

    # 3. Check for human review decision
    latest_event = (
        db.query(ReviewEventModel)
        .filter(
            ReviewEventModel.group_id == group_id,
            ReviewEventModel.event_type.in_([
                DecisionEventType.SCREEN_DECISION.value,
                DecisionEventType.CONFLICT_RESOLUTION.value,
            ]),
        )
        .order_by(ReviewEventModel.sequence.desc())
        .first()
    )

    if latest_event:
        try:
            payload = json.loads(latest_event.payload_json) if latest_event.payload_json else {}
        except (json.JSONDecodeError, ValueError, TypeError):
            payload = {}

        dec_str = payload.get("decision")
        reason = payload.get("notes") or (
            ", ".join(payload.get("exclusion_reasons", [])) if payload.get("exclusion_reasons") else None
        )

        if dec_str == "include":
            return EffectiveDecisionState.INCLUDE, reason, None
        if dec_str == "exclude":
            return EffectiveDecisionState.EXCLUDE, reason, None
        if dec_str == "maybe":
            return EffectiveDecisionState.MAYBE, reason, None

    # 4. Check paper group pre-screen state
    group = db.query(PaperGroupModel).filter_by(id=group_id).first()
    if group and group.pre_screen_result_json:
        try:
            machine_res = json.loads(group.pre_screen_result_json)
            pred = machine_res.get("prediction")
            reason = machine_res.get("rationale")
            if pred == "include":
                return EffectiveDecisionState.INCLUDE, reason, None
            if pred == "exclude":
                return EffectiveDecisionState.EXCLUDE, reason, None
            if pred == "maybe":
                return EffectiveDecisionState.MAYBE, reason, None
        except (json.JSONDecodeError, ValueError, TypeError) as err:
            logger.debug('Failed to parse pre_screen_result_json: %s', err)

    return EffectiveDecisionState.UNSCREENED, None, None


def _get_version_record_memberships(
    db: Session,
    query_version_id: str,
) -> dict[str, tuple[SourceRecordModel, RecordRevisionModel]]:
    """Get mapping of source_record_id -> (SourceRecordModel, RecordRevisionModel) for a query version."""
    rows = (
        db.query(QueryMembershipModel, SourceRecordModel, RecordRevisionModel)
        .join(SearchExecutionModel, SearchExecutionModel.id == QueryMembershipModel.search_execution_id)
        .join(SourceRecordModel, SourceRecordModel.id == QueryMembershipModel.source_record_id)
        .join(RecordRevisionModel, RecordRevisionModel.id == QueryMembershipModel.record_revision_id)
        .filter(SearchExecutionModel.query_version_id == query_version_id)
        .all()
    )

    record_map: dict[str, tuple[SourceRecordModel, RecordRevisionModel]] = {}
    for _membership, source_rec, revision in rows:
        record_map[source_rec.id] = (source_rec, revision)
    return record_map


def list_search_versions(
    db: Session,
    workspace_id: str,
) -> list[SearchEvolutionVersionSummary]:
    """List all search versions for workspace with timeline summaries and executed provider counts."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    q_rows = (
        db.query(QueryVersionModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(QueryVersionModel.sequence.asc())
        .all()
    )

    results: list[SearchEvolutionVersionSummary] = []
    seen_source_ids_cumulative: set[str] = set()

    for qv in q_rows:
        # Load executions
        executions = (
            db.query(SearchExecutionModel)
            .filter_by(query_version_id=qv.id)
            .order_by(SearchExecutionModel.counted_at.asc())
            .all()
        )
        exec_dtos = []
        for ex in executions:
            try:
                st = JobState(ex.status)
            except ValueError:
                st = JobState.SUCCEEDED
            exec_dtos.append(
                SearchExecutionResponse(
                    id=ex.id,
                    query_version_id=ex.query_version_id,
                    source=SourceNamespace(ex.source),
                    exact_query=ex.exact_query,
                    synonym_setting=ex.synonym_setting,
                    hit_count=ex.hit_count,
                    counted_at=ex.counted_at,
                    status=st,
                    partial=ex.partial,
                    cap=ex.cap,
                    raw_hash=ex.raw_hash,
                )
            )

        # Memberships for this version
        memberships_map = _get_version_record_memberships(db, qv.id)
        current_record_ids = set(memberships_map.keys())

        # Calculate new vs repeated
        if not seen_source_ids_cumulative:
            new_count = len(current_record_ids)
            repeated_count = 0
        else:
            new_count = len(current_record_ids - seen_source_ids_cumulative)
            repeated_count = len(current_record_ids & seen_source_ids_cumulative)

        # Calculate screened vs unscreened
        screened_count = 0
        unscreened_count = 0
        for src_id in current_record_ids:
            state, _, _ = _resolve_record_screening_state(db, src_id)
            if state in (EffectiveDecisionState.INCLUDE, EffectiveDecisionState.EXCLUDE, EffectiveDecisionState.MAYBE):
                screened_count += 1
            else:
                unscreened_count += 1

        seen_source_ids_cumulative.update(current_record_ids)

        sources_raw = _safe_json_list(qv.sources_json)
        sources = [SourceNamespace(s) for s in sources_raw if s in [sn.value for sn in SourceNamespace]]

        results.append(
            SearchEvolutionVersionSummary(
                id=qv.id,
                sequence=qv.sequence,
                workspace_id=qv.workspace_id,
                parent_id=qv.parent_id,
                restored_from_version_id=qv.restored_from_version_id,
                change_description=qv.change_description,
                created_at=qv.created_at,
                sources=sources,
                start_date=qv.start_date,
                end_date=qv.end_date,
                total_records=len(current_record_ids),
                screened_records=screened_count,
                unscreened_records=unscreened_count,
                new_records_count=new_count,
                repeated_records_count=repeated_count,
                executions=exec_dtos,
            )
        )

    # Return descending by sequence for timeline display
    results.reverse()
    return results


def get_search_version_detail(
    db: Session,
    workspace_id: str,
    version_id: str,
) -> SearchEvolutionVersionSummary:
    """Retrieve detailed summary and execution history for a single search version."""
    qv = (
        db.query(QueryVersionModel)
        .filter_by(id=version_id, workspace_id=workspace_id)
        .first()
    )
    if not qv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search version '{version_id}' not found in workspace",
        )

    versions = list_search_versions(db, workspace_id)
    for v in versions:
        if v.id == version_id:
            return v

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Search version '{version_id}' summary could not be computed",
    )


def compute_field_diffs(
    base_rev: RecordRevisionModel,
    target_rev: RecordRevisionModel,
) -> list[SearchEvolutionMetadataFieldDiff]:
    """Compare fields between two revisions of the same record and return changed fields."""
    diffs: list[SearchEvolutionMetadataFieldDiff] = []

    # Title
    base_title = (base_rev.title or "").strip()
    target_title = (target_rev.title or "").strip()
    if base_title != target_title:
        diffs.append(
            SearchEvolutionMetadataFieldDiff(
                field_name="title",
                base_value=base_title,
                target_value=target_title,
            )
        )

    # Abstract
    base_abs = (base_rev.abstract_text or "").strip()
    target_abs = (target_rev.abstract_text or "").strip()
    if base_abs != target_abs:
        diffs.append(
            SearchEvolutionMetadataFieldDiff(
                field_name="abstract",
                base_value=base_abs,
                target_value=target_abs,
            )
        )

    # Year
    if base_rev.year != target_rev.year:
        diffs.append(
            SearchEvolutionMetadataFieldDiff(
                field_name="year",
                base_value=str(base_rev.year) if base_rev.year is not None else None,
                target_value=str(target_rev.year) if target_rev.year is not None else None,
            )
        )

    # Journal
    base_j = (base_rev.journal or "").strip()
    target_j = (target_rev.journal or "").strip()
    if base_j != target_j:
        diffs.append(
            SearchEvolutionMetadataFieldDiff(
                field_name="journal",
                base_value=base_j or None,
                target_value=target_j or None,
            )
        )

    # Authors
    base_authors = ", ".join(_safe_json_list(base_rev.authors_json))
    target_authors = ", ".join(_safe_json_list(target_rev.authors_json))
    if base_authors != target_authors:
        diffs.append(
            SearchEvolutionMetadataFieldDiff(
                field_name="authors",
                base_value=base_authors or None,
                target_value=target_authors or None,
            )
        )

    # DOI
    base_doi = (base_rev.doi or "").strip().lower()
    target_doi = (target_rev.doi or "").strip().lower()
    if base_doi != target_doi:
        diffs.append(
            SearchEvolutionMetadataFieldDiff(
                field_name="doi",
                base_value=base_rev.doi,
                target_value=target_rev.doi,
            )
        )

    # PMID
    base_pmid = (base_rev.pmid or "").strip()
    target_pmid = (target_rev.pmid or "").strip()
    if base_pmid != target_pmid:
        diffs.append(
            SearchEvolutionMetadataFieldDiff(
                field_name="pmid",
                base_value=base_rev.pmid,
                target_value=target_rev.pmid,
            )
        )

    return diffs


def compute_search_evolution_diff(
    db: Session,
    workspace_id: str,
    target_version_id: str,
    base_version_id: str | None = None,
) -> SearchEvolutionDiffResponse:
    """Compute rich 6-way diff between base search version and target search version."""
    target_qv = (
        db.query(QueryVersionModel)
        .filter_by(id=target_version_id, workspace_id=workspace_id)
        .first()
    )
    if not target_qv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target search version '{target_version_id}' not found in workspace",
        )

    # Determine base version if not explicitly supplied
    base_qv: QueryVersionModel | None = None
    if base_version_id:
        base_qv = (
            db.query(QueryVersionModel)
            .filter_by(id=base_version_id, workspace_id=workspace_id)
            .first()
        )
        if not base_qv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Base search version '{base_version_id}' not found in workspace",
            )
    else:
        # Predecessor: check parent_id first, then sequence - 1
        if target_qv.parent_id:
            base_qv = (
                db.query(QueryVersionModel)
                .filter_by(id=target_qv.parent_id, workspace_id=workspace_id)
                .first()
            )
        if not base_qv:
            base_qv = (
                db.query(QueryVersionModel)
                .filter(
                    QueryVersionModel.workspace_id == workspace_id,
                    QueryVersionModel.sequence < target_qv.sequence,
                )
                .order_by(QueryVersionModel.sequence.desc())
                .first()
            )

    target_memberships = _get_version_record_memberships(db, target_qv.id)
    base_memberships = (
        _get_version_record_memberships(db, base_qv.id) if base_qv else {}
    )

    all_source_ids = set(target_memberships.keys()) | set(base_memberships.keys())

    record_diffs: list[SearchEvolutionRecordDiff] = []

    newly_discovered_count = 0
    repeated_count = 0
    missing_from_newer_count = 0
    metadata_changed_count = 0
    conflicts_count = 0
    screened_target_count = 0
    unscreened_target_count = 0

    for src_id in all_source_ids:
        in_target = src_id in target_memberships
        in_base = src_id in base_memberships

        # Screening state resolution
        decision_state, decision_reason, preserved_from = _resolve_record_screening_state(db, src_id)

        if in_target:
            source_rec, target_rev = target_memberships[src_id]
            is_screened = decision_state in (
                EffectiveDecisionState.INCLUDE,
                EffectiveDecisionState.EXCLUDE,
                EffectiveDecisionState.MAYBE,
            )
            if is_screened:
                screened_target_count += 1
            else:
                unscreened_target_count += 1
        else:
            source_rec, base_rev = base_memberships[src_id]
            target_rev = None  # type: ignore[assignment]

        # Determine category & field diffs
        category: SearchEvolutionCategory
        field_diffs: list[SearchEvolutionMetadataFieldDiff] = []
        base_rev_id: str | None = None
        target_rev_id: str | None = None
        metadata_changed_since_screening = False

        if decision_state == EffectiveDecisionState.CONFLICT:
            category = SearchEvolutionCategory.CONFLICT
            conflicts_count += 1
            if in_target:
                target_rev_id = target_rev.id
            if in_base:
                base_rev_id = base_memberships[src_id][1].id

        elif in_target and not in_base:
            category = SearchEvolutionCategory.NEWLY_DISCOVERED
            newly_discovered_count += 1
            target_rev_id = target_rev.id

        elif in_base and not in_target:
            # Absence without deletion: Record was present in earlier search but not in newer search.
            # It is retained in review corpus and screening decisions remain intact.
            category = SearchEvolutionCategory.MISSING_FROM_NEWER
            missing_from_newer_count += 1
            base_rev_id = base_memberships[src_id][1].id

        else:
            # In both Base and Target
            base_rev = base_memberships[src_id][1]
            base_rev_id = base_rev.id
            target_rev_id = target_rev.id

            diffs = compute_field_diffs(base_rev, target_rev)
            if diffs or (base_rev.content_hash != target_rev.content_hash):
                category = SearchEvolutionCategory.METADATA_CHANGED
                metadata_changed_count += 1
                field_diffs = diffs
                if decision_state in (
                    EffectiveDecisionState.INCLUDE,
                    EffectiveDecisionState.EXCLUDE,
                    EffectiveDecisionState.MAYBE,
                ):
                    metadata_changed_since_screening = True
            else:
                category = SearchEvolutionCategory.REPEATED
                repeated_count += 1

        # Use target revision display data if available, otherwise base revision
        display_rev = target_rev if in_target else base_memberships[src_id][1]
        authors = _safe_json_list(display_rev.authors_json)

        # Source enum
        try:
            src_enum = SourceNamespace(source_rec.source)
        except ValueError:
            src_enum = SourceNamespace.PUBMED

        record_diffs.append(
            SearchEvolutionRecordDiff(
                source_record_id=source_rec.id,
                external_id=source_rec.external_id,
                source=src_enum,
                title=display_rev.title,
                authors=authors,
                year=display_rev.year,
                journal=display_rev.journal,
                doi=display_rev.doi,
                pmid=display_rev.pmid,
                category=category,
                base_record_revision_id=base_rev_id,
                target_record_revision_id=target_rev_id,
                field_diffs=field_diffs,
                screening_decision=decision_state,
                screening_reason=decision_reason,
                screening_preserved_from_version_id=preserved_from or (base_qv.id if in_base and in_target else None),
                metadata_changed_since_screening=metadata_changed_since_screening,
            )
        )

    # Sort record diffs: newly discovered first, then metadata changed, conflicts, repeated, missing from newer
    category_order = {
        SearchEvolutionCategory.NEWLY_DISCOVERED: 0,
        SearchEvolutionCategory.METADATA_CHANGED: 1,
        SearchEvolutionCategory.CONFLICT: 2,
        SearchEvolutionCategory.REPEATED: 3,
        SearchEvolutionCategory.MISSING_FROM_NEWER: 4,
    }
    record_diffs.sort(key=lambda r: (category_order.get(r.category, 5), r.title.lower()))

    summary = SearchEvolutionDiffSummary(
        base_version_id=base_qv.id if base_qv else "none",
        base_sequence=base_qv.sequence if base_qv else 0,
        target_version_id=target_qv.id,
        target_sequence=target_qv.sequence,
        total_base_records=len(base_memberships),
        total_target_records=len(target_memberships),
        newly_discovered_count=newly_discovered_count,
        repeated_count=repeated_count,
        missing_from_newer_count=missing_from_newer_count,
        metadata_changed_count=metadata_changed_count,
        conflicts_count=conflicts_count,
        screened_target_count=screened_target_count,
        unscreened_target_count=unscreened_target_count,
    )

    return SearchEvolutionDiffResponse(
        summary=summary,
        records=record_diffs,
    )


def restore_search_configuration(
    db: Session,
    workspace_id: str,
    target_version_id: str,
    reason: str | None = None,
    actor_id: str | None = "researcher",
) -> SearchRestoreResponse:
    """Safely restore a prior search query configuration into a new active version.

    Non-destructive invariant:
    - Never deletes, overwrites, or truncates any historical search versions or records.
    - Preserves all human reviewer decisions on existing paper groups.
    - Creates a new query version with restored AST and metadata, linking restored_from_version_id.
    """
    target_qv = (
        db.query(QueryVersionModel)
        .filter_by(id=target_version_id, workspace_id=workspace_id)
        .first()
    )
    if not target_qv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query version '{target_version_id}' not found in workspace",
        )

    # Next sequence
    max_seq = (
        db.query(func.max(QueryVersionModel.sequence))
        .filter_by(workspace_id=workspace_id)
        .scalar()
    ) or 0
    new_sequence = max_seq + 1

    desc = f"Restored search strategy from Version {target_qv.sequence}"
    if reason and reason.strip():
        desc += f": {reason.strip()}"

    new_qv = QueryVersionModel(
        workspace_id=workspace_id,
        parent_id=target_qv.id,
        sequence=new_sequence,
        ast_json=target_qv.ast_json,
        start_date=target_qv.start_date,
        end_date=target_qv.end_date,
        sources_json=target_qv.sources_json,
        criteria_version_id=target_qv.criteria_version_id,
        content_hash=target_qv.content_hash,
        change_description=desc,
        restored_from_version_id=target_qv.id,
    )
    db.add(new_qv)
    db.commit()
    db.refresh(new_qv)

    # Parse DTO fields
    ast_node = QueryASTNode.model_validate_json(new_qv.ast_json)
    sources_raw = _safe_json_list(new_qv.sources_json)
    sources = [SourceNamespace(s) for s in sources_raw if s in [sn.value for sn in SourceNamespace]]

    q_resp = QueryVersionResponse(
        id=new_qv.id,
        workspace_id=new_qv.workspace_id,
        parent_id=new_qv.parent_id,
        sequence=new_qv.sequence,
        ast=ast_node,
        start_date=new_qv.start_date,
        end_date=new_qv.end_date,
        sources=sources,
        criteria_version_id=new_qv.criteria_version_id,
        content_hash=new_qv.content_hash,
        change_description=new_qv.change_description,
        restored_from_version_id=new_qv.restored_from_version_id,
        created_at=new_qv.created_at,
    )

    return SearchRestoreResponse(
        restored_query=q_resp,
        restored_from_version_id=target_qv.id,
        message=f"Successfully restored search strategy from Version {target_qv.sequence} as Version {new_sequence}",
    )
