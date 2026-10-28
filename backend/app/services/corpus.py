"""Corpus processing, deduplication, screening, and effective decision projection services."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.enums import (
    CorpusRevisionState,
    DecisionEventType,
    DedupEdgeStatus,
    EffectiveDecisionState,
    EligibilityStatus,
    SourceNamespace,
)
from app.contracts.models import (
    CorpusRevisionResponse,
    PaperGroupDetail,
    PaperGroupSummary,
    PicoResult,
    RecordRevisionResponse,
    ReviewConflictResponse,
    ReviewEventResponse,
    ScreenResult,
    StructuredSection,
)
from app.db.models import (
    CorpusMemberModel,
    CorpusQueryModel,
    CorpusRevisionModel,
    CriteriaVersionModel,
    DedupEdgeModel,
    GroupMemberModel,
    GroupSnapshotModel,
    MachineResultModel,
    PaperGroupModel,
    PicoAnnotationModel,
    QueryMembershipModel,
    RecordRevisionModel,
    ReviewConflictModel,
    ReviewEventModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.dedup import DeduplicationEngine
from app.pico import RuleBasedPicoExtractor
from app.screening import ScreeningEngine, get_default_criteria_version

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def model_to_record_revision_response(
    rev: RecordRevisionModel,
    src: SourceRecordModel,
) -> RecordRevisionResponse:
    """Map SQLAlchemy RecordRevisionModel and SourceRecordModel to Pydantic RecordRevisionResponse."""
    structured_sections = None
    if rev.structured_sections_json:
        try:
            raw_sections = json.loads(rev.structured_sections_json)
            if isinstance(raw_sections, list):
                structured_sections = [StructuredSection(**sec) for sec in raw_sections]
        except (json.JSONDecodeError, TypeError, ValueError):
            structured_sections = None

    authors = []
    if rev.authors_json:
        try:
            authors = json.loads(rev.authors_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            authors = []

    languages = []
    if rev.language_json:
        try:
            languages = json.loads(rev.language_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            languages = []

    pub_types = []
    if rev.publication_types_json:
        try:
            pub_types = json.loads(rev.publication_types_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            pub_types = []

    source_val = SourceNamespace.PUBMED if src.source == "pubmed" else (
        SourceNamespace.EUROPEPMC if src.source == "europepmc" else SourceNamespace.SYNTHETIC
    )

    return RecordRevisionResponse(
        id=rev.id,
        source_record_id=src.id,
        content_hash=rev.content_hash,
        title=rev.title,
        abstract_text=rev.abstract_text,
        structured_sections=structured_sections,
        authors=authors,
        year=rev.year,
        journal=rev.journal,
        pages=rev.pages,
        language=languages,
        publication_types=pub_types,
        doi=rev.doi,
        pmid=rev.pmid,
        source=source_val,
        source_namespace=src.source_namespace,
        external_id=src.external_id,
        fetched_at=rev.fetched_at,
    )


def project_effective_group_decision(
    db: Session,
    group_id: str,
    revision_id: str | None = None,
) -> tuple[EffectiveDecisionState, ReviewEventModel | None, ScreenResult | None, bool]:
    """Project the effective decision state of a paper group.

    Invariant Rules:
    1. Human review event strictly supersedes machine suggestion.
    2. Active un-resolved conflict yields EffectiveDecisionState.CONFLICT.
    3. Absent a human event, machine suggestion reflects in status.
    4. If no decision and no machine result, returns EffectiveDecisionState.UNSCREENED.
    """
    # 1. Check for active un-resolved conflicts
    conflict = (
        db.query(ReviewConflictModel)
        .filter_by(group_id=group_id, resolution_event_id=None)
        .first()
    )
    if conflict:
        return (EffectiveDecisionState.CONFLICT, None, None, True)

    # 2. Check for latest human screen decision event
    latest_event = (
        db.query(ReviewEventModel)
        .filter_by(group_id=group_id, event_type=DecisionEventType.SCREEN_DECISION.value)
        .order_by(ReviewEventModel.sequence.desc())
        .first()
    )

    # 3. Retrieve machine screening result if available
    machine_res_query = (
        db.query(MachineResultModel)
        .filter_by(group_id=group_id, stage="screening")
    )
    if revision_id:
        machine_res_query = machine_res_query.filter_by(corpus_revision_id=revision_id)
    machine_res_row = machine_res_query.order_by(MachineResultModel.created_at.desc()).first()

    screen_res: ScreenResult | None = None
    if machine_res_row:
        try:
            data = json.loads(machine_res_row.output_json)
            screen_res = ScreenResult(**data)
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            logger.warning("Failed to deserialize screen_result for group %s: %s", group_id, e)

    # 4. Human event wins
    if latest_event:
        try:
            payload = json.loads(latest_event.payload_json)
            status_str = payload.get("status")
            if status_str == EligibilityStatus.INCLUDE.value:
                return (EffectiveDecisionState.INCLUDE, latest_event, screen_res, False)
            elif status_str == EligibilityStatus.EXCLUDE.value:
                return (EffectiveDecisionState.EXCLUDE, latest_event, screen_res, False)
            elif status_str == EligibilityStatus.MAYBE.value:
                return (EffectiveDecisionState.MAYBE, latest_event, screen_res, False)
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse review event payload: %s", e)

    # 5. Fallback to machine suggestion
    if screen_res:
        if screen_res.status == EligibilityStatus.INCLUDE:
            return (EffectiveDecisionState.INCLUDE, None, screen_res, False)
        elif screen_res.status == EligibilityStatus.EXCLUDE:
            return (EffectiveDecisionState.EXCLUDE, None, screen_res, False)
        elif screen_res.status == EligibilityStatus.MAYBE:
            return (EffectiveDecisionState.MAYBE, None, screen_res, False)

    return (EffectiveDecisionState.UNSCREENED, None, screen_res, False)


def process_corpus(
    db: Session,
    workspace_id: str,
    criteria_version_id: str | None = None,
) -> CorpusRevisionResponse:
    """Gather records, run deterministic dedup, screen representatives, extract PICO, and publish corpus snapshot."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workspace '{workspace_id}' not found")

    # 1. Resolve criteria version
    if criteria_version_id:
        crit_model = db.query(CriteriaVersionModel).filter_by(id=criteria_version_id, workspace_id=workspace_id).first()
        if not crit_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Criteria version '{criteria_version_id}' not found")
    else:
        crit_model = (
            db.query(CriteriaVersionModel)
            .filter_by(workspace_id=workspace_id)
            .order_by(CriteriaVersionModel.sequence.desc())
            .first()
        )
        if not crit_model:
            # Create initial default criteria version
            default_crit = get_default_criteria_version(workspace_id=workspace_id)
            crit_model = CriteriaVersionModel(
                id=default_crit.id,
                workspace_id=workspace_id,
                sequence=1,
                question=default_crit.question,
                pico_json=json.dumps(default_crit.pico),
                criteria_json=json.dumps([c.model_dump() for c in default_crit.criteria]),
                content_hash=default_crit.content_hash,
                created_at=utc_now(),
            )
            db.add(crit_model)
            db.flush()

    # 2. Gather all query executions in this workspace
    search_execs = (
        db.query(SearchExecutionModel)
        .join(SearchExecutionModel.query_version)
        .filter(SearchExecutionModel.query_version.has(workspace_id=workspace_id))
        .all()
    )
    search_exec_ids = [se.id for se in search_execs]

    # 3. Gather query memberships to find all imported record revisions
    memberships = (
        db.query(QueryMembershipModel)
        .filter(QueryMembershipModel.search_execution_id.in_(search_exec_ids))
        .all()
    ) if search_exec_ids else []

    # Map records uniquely by source_record_id -> (RecordRevisionModel, SourceRecordModel)
    unique_records_map: dict[str, tuple[RecordRevisionModel, SourceRecordModel]] = {}
    for m in memberships:
        if m.source_record_id not in unique_records_map:
            rec_rev = db.query(RecordRevisionModel).filter_by(id=m.record_revision_id).first()
            src_rec = db.query(SourceRecordModel).filter_by(id=m.source_record_id).first()
            if rec_rev and src_rec:
                unique_records_map[m.source_record_id] = (rec_rev, src_rec)

    domain_records: list[RecordRevisionResponse] = [
        model_to_record_revision_response(rev, src)
        for rev, src in unique_records_map.values()
    ]

    # 4. Deterministic Deduplication
    dedup_engine = DeduplicationEngine()
    dedup_version = "dedup:v1.0.0"

    # Query existing confirmed and rejected edges in this workspace
    existing_edges = db.query(DedupEdgeModel).filter_by(workspace_id=workspace_id).all()
    confirmed_proposals = []
    cannot_link_pairs: set[tuple[str, str]] = set()
    src_to_rev = {src_id: rev_m.id for src_id, (rev_m, _) in unique_records_map.items()}

    for edge in existing_edges:
        rec_a = src_to_rev.get(edge.record_id_a, edge.record_id_a)
        rec_b = src_to_rev.get(edge.record_id_b, edge.record_id_b)

        if edge.status == DedupEdgeStatus.CONFIRMED.value:
            try:
                ev = json.loads(edge.evidence_json)
            except (json.JSONDecodeError, TypeError, ValueError):
                ev = {}
            from app.contracts.models import DedupProposal
            confirmed_proposals.append(
                DedupProposal(
                    record_id_a=rec_a,
                    record_id_b=rec_b,
                    score=edge.score,
                    method_version=edge.method_version,
                    evidence=ev,
                    status=DedupEdgeStatus.CONFIRMED,
                )
            )
        elif edge.status == DedupEdgeStatus.REJECTED.value:
            cannot_link_pairs.add((rec_a, rec_b))
            cannot_link_pairs.add((rec_b, rec_a))
            cannot_link_pairs.add((edge.record_id_a, edge.record_id_b))
            cannot_link_pairs.add((edge.record_id_b, edge.record_id_a))

    # Find candidates
    new_candidates = dedup_engine.find_candidate_pairs(domain_records)
    for cand in new_candidates:
        pair_key = (cand.record_id_a, cand.record_id_b)
        rev_pair_key = (cand.record_id_b, cand.record_id_a)
        if pair_key in cannot_link_pairs or rev_pair_key in cannot_link_pairs:
            continue
        # Persist proposed edge if not existing
        existing = (
            db.query(DedupEdgeModel)
            .filter_by(workspace_id=workspace_id, record_id_a=cand.record_id_a, record_id_b=cand.record_id_b)
            .first()
        )
        if not existing:
            db.add(
                DedupEdgeModel(
                    id=str(uuid4()),
                    workspace_id=workspace_id,
                    record_id_a=cand.record_id_a,
                    record_id_b=cand.record_id_b,
                    score=cand.score,
                    method_version=cand.method_version,
                    evidence_json=json.dumps(cand.evidence),
                    status=DedupEdgeStatus.PROPOSED.value,
                    created_at=utc_now(),
                )
            )
            if cand.score >= 0.85:
                confirmed_proposals.append(cand)

    db.flush()

    # Partition groups
    partitioned = dedup_engine.partition_groups(
        records=domain_records,
        accepted_edges=confirmed_proposals,
        cannot_link_pairs=cannot_link_pairs,
    )

    # 5. Create CorpusRevisionModel
    revision_id = str(uuid4())
    corpus_fingerprint = hashlib.sha256(
        f"{workspace_id}:{crit_model.content_hash}:{len(domain_records)}:{len(partitioned)}".encode()
    ).hexdigest()

    corpus_rev = CorpusRevisionModel(
        id=revision_id,
        workspace_id=workspace_id,
        parent_id=ws.current_revision_id,
        criteria_version_id=crit_model.id,
        dedup_version=dedup_version,
        state=CorpusRevisionState.BUILDING.value,
        published_at=None,
        fingerprint=corpus_fingerprint,
        group_count=len(partitioned),
        record_count=len(domain_records),
        created_at=utc_now(),
    )
    db.add(corpus_rev)
    db.flush()

    # Link corpus queries
    for se_id in search_exec_ids:
        db.add(CorpusQueryModel(corpus_revision_id=revision_id, search_execution_id=se_id))

    # Link corpus members
    for src_id, (rev_m, src_m) in unique_records_map.items():
        db.add(
            CorpusMemberModel(
                corpus_revision_id=revision_id,
                source_record_id=src_id,
                record_revision_id=rev_m.id,
            )
        )

    # 6. Persist Paper Groups, Screen Representatives, and Extract PICO
    screening_engine = ScreeningEngine()
    pico_extractor = RuleBasedPicoExtractor()
    from app.contracts.models import CriteriaVersionResponse, CriterionDefinition
    crit_dto = CriteriaVersionResponse(
        id=crit_model.id,
        workspace_id=crit_model.workspace_id,
        sequence=crit_model.sequence,
        question=crit_model.question,
        pico_description=json.loads(crit_model.pico_json),
        criteria=[CriterionDefinition(**c) for c in json.loads(crit_model.criteria_json)],
        content_hash=crit_model.content_hash,
        created_at=crit_model.created_at,
    )

    for group_data in partitioned:
        rep: RecordRevisionResponse = group_data["representative"]
        member_ids: list[str] = group_data["member_ids"]
        sorted_mids_str = ",".join(sorted(member_ids))
        group_membership_hash = hashlib.sha256(sorted_mids_str.encode("utf-8")).hexdigest()

        # Check if paper_group already exists for this exact membership
        existing_group = (
            db.query(PaperGroupModel)
            .filter_by(workspace_id=workspace_id, membership_fingerprint=group_membership_hash)
            .first()
        )
        if not existing_group:
            existing_group = PaperGroupModel(
                id=f"grp-{uuid4().hex[:12]}",
                workspace_id=workspace_id,
                membership_fingerprint=group_membership_hash,
                row_version=1,
                created_at=utc_now(),
            )
            db.add(existing_group)
            db.flush()

            # Record initial group members
            for m_rec in group_data["members"]:
                db.add(GroupMemberModel(group_id=existing_group.id, source_record_id=m_rec.source_record_id))

        # Snapshot mapping for this revision
        db.add(
            GroupSnapshotModel(
                corpus_revision_id=revision_id,
                group_id=existing_group.id,
                representative_revision_id=rep.id,
                created_at=utc_now(),
            )
        )

        # 7. Screen representative record
        screen_res = screening_engine.screen_record(rep, crit_dto)
        screen_fp = hashlib.sha256(
            f"{rep.id}:{rep.content_hash}:{crit_dto.content_hash}:{screen_res.method_version}".encode()
        ).hexdigest()

        db.add(
            MachineResultModel(
                id=str(uuid4()),
                corpus_revision_id=revision_id,
                group_id=existing_group.id,
                record_revision_id=rep.id,
                stage="screening",
                input_fingerprint=screen_fp,
                method_version=screen_res.method_version,
                output_json=screen_res.model_dump_json(),
                created_at=utc_now(),
            )
        )

        # 8. Extract PICO spans for representative record
        pico_res = pico_extractor.extract_pico_spans(rep)
        pico_fp = hashlib.sha256(f"{rep.id}:{rep.content_hash}:{pico_res.method_version}".encode()).hexdigest()

        db.add(
            MachineResultModel(
                id=str(uuid4()),
                corpus_revision_id=revision_id,
                group_id=existing_group.id,
                record_revision_id=rep.id,
                stage="pico",
                input_fingerprint=pico_fp,
                method_version=pico_res.method_version,
                output_json=pico_res.model_dump_json(),
                created_at=utc_now(),
            )
        )

        # Persist baseline PICO annotations
        for span in pico_res.spans:
            db.add(
                PicoAnnotationModel(
                    id=str(uuid4()),
                    event_id=None,
                    record_revision_id=rep.id,
                    label=span.label.value,
                    start_cp=span.start_cp,
                    end_cp=span.end_cp,
                    quote=span.quote,
                    provenance=span.provenance,
                    created_at=utc_now(),
                )
            )

    # 9. Project decision lineage and mark CorpusRevisionModel as PUBLISHED
    try:
        db.flush()
        if corpus_rev.parent_id:
            from app.services.snapshots import project_decision_lineage
            project_decision_lineage(
                db=db,
                corpus_revision_id=corpus_rev.id,
                parent_revision_id=corpus_rev.parent_id,
            )

        corpus_rev.state = CorpusRevisionState.PUBLISHED.value
        corpus_rev.published_at = utc_now()
        ws.current_revision_id = corpus_rev.id
        ws.row_version += 1
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to publish corpus revision %s", corpus_rev.id)
        raise

    return CorpusRevisionResponse(
        id=corpus_rev.id,
        workspace_id=corpus_rev.workspace_id,
        parent_id=corpus_rev.parent_id,
        criteria_version_id=corpus_rev.criteria_version_id,
        dedup_version=corpus_rev.dedup_version,
        state=CorpusRevisionState.PUBLISHED,
        published_at=corpus_rev.published_at,
        decision_seq_cutoff=None,
        fingerprint=corpus_rev.fingerprint,
        group_count=corpus_rev.group_count,
        record_count=corpus_rev.record_count,
    )


def list_paper_groups_in_revision(
    db: Session,
    revision_id: str,
    status_filter: EffectiveDecisionState | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PaperGroupSummary]:
    """List deduplicated paper groups in a corpus revision with projected effective decisions."""
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

    summaries: list[PaperGroupSummary] = []
    for snap in snapshots:
        group_id = snap.group_id
        rep_rev = db.query(RecordRevisionModel).filter_by(id=snap.representative_revision_id).first()
        if not rep_rev:
            continue
        src_rec = db.query(SourceRecordModel).filter_by(id=rep_rev.source_record_id).first()
        if not src_rec:
            continue

        rep_dto = model_to_record_revision_response(rep_rev, src_rec)
        member_count = db.query(GroupMemberModel).filter_by(group_id=group_id).count()

        effective_status, human_event, _screen_res, has_conflict = project_effective_group_decision(
            db=db,
            group_id=group_id,
            revision_id=revision_id,
        )

        if status_filter and effective_status != status_filter:
            continue

        summaries.append(
            PaperGroupSummary(
                id=group_id,
                workspace_id=corpus_rev.workspace_id,
                representative_revision=rep_dto,
                member_count=max(1, member_count),
                effective_status=effective_status,
                has_conflict=has_conflict,
                has_human_decision=human_event is not None,
                last_decision_at=human_event.created_at if human_event else None,
            )
        )

    # Sort deterministically by group ID
    sorted_summaries = sorted(summaries, key=lambda s: s.id)
    return sorted_summaries[offset : offset + limit]


def get_paper_group_detail(
    db: Session,
    group_id: str,
    revision_id: str | None = None,
) -> PaperGroupDetail:
    """Retrieve full group detail, member revisions, screening evidence, PICO annotations, and review history."""
    group = db.query(PaperGroupModel).filter_by(id=group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Paper group '{group_id}' not found")

    # Find snapshot in revision
    rep_rev: RecordRevisionModel | None = None
    if revision_id:
        snap = db.query(GroupSnapshotModel).filter_by(corpus_revision_id=revision_id, group_id=group_id).first()
        if snap:
            rep_rev = db.query(RecordRevisionModel).filter_by(id=snap.representative_revision_id).first()

    if not rep_rev:
        # Fallback to first member
        first_member = db.query(GroupMemberModel).filter_by(group_id=group_id).first()
        if first_member:
            rep_rev = (
                db.query(RecordRevisionModel)
                .filter_by(source_record_id=first_member.source_record_id)
                .order_by(RecordRevisionModel.fetched_at.desc())
                .first()
            )

    if not rep_rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No representative revision found for group")

    src_rec = db.query(SourceRecordModel).filter_by(id=rep_rev.source_record_id).first()
    if not src_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source record identity missing")

    rep_dto = model_to_record_revision_response(rep_rev, src_rec)

    # Member revisions
    member_models = db.query(GroupMemberModel).filter_by(group_id=group_id).all()
    member_dtos: list[RecordRevisionResponse] = []
    for mm in member_models:
        rev_m = (
            db.query(RecordRevisionModel)
            .filter_by(source_record_id=mm.source_record_id)
            .order_by(RecordRevisionModel.fetched_at.desc())
            .first()
        )
        src_m = db.query(SourceRecordModel).filter_by(id=mm.source_record_id).first()
        if rev_m and src_m:
            member_dtos.append(model_to_record_revision_response(rev_m, src_m))

    # Projection
    effective_status, human_event, screen_res, has_conflict = project_effective_group_decision(
        db=db,
        group_id=group_id,
        revision_id=revision_id,
    )

    summary = PaperGroupSummary(
        id=group.id,
        workspace_id=group.workspace_id,
        representative_revision=rep_dto,
        member_count=len(member_dtos),
        effective_status=effective_status,
        has_conflict=has_conflict,
        has_human_decision=human_event is not None,
        last_decision_at=human_event.created_at if human_event else None,
    )

    # PICO result
    pico_res: PicoResult | None = None
    pico_row = (
        db.query(MachineResultModel)
        .filter_by(group_id=group_id, stage="pico")
        .order_by(MachineResultModel.created_at.desc())
        .first()
    )
    if pico_row:
        try:
            pico_res = PicoResult(**json.loads(pico_row.output_json))
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            logger.warning("Failed to deserialize pico_result for group %s: %s", group_id, e)

    # Audit events
    events = (
        db.query(ReviewEventModel)
        .filter_by(group_id=group_id)
        .order_by(ReviewEventModel.sequence.asc())
        .all()
    )
    event_dtos = [
        ReviewEventResponse(
            id=ev.id,
            sequence=ev.sequence,
            workspace_id=ev.workspace_id,
            group_id=ev.group_id,
            event_type=DecisionEventType(ev.event_type),
            payload=json.loads(ev.payload_json),
            actor_id=ev.actor_id,
            reason=ev.reason,
            supersedes_event_id=ev.supersedes_event_id,
            created_at=ev.created_at,
        )
        for ev in events
    ]

    # Conflicts
    conflicts = db.query(ReviewConflictModel).filter_by(group_id=group_id).all()
    conflict_dtos = [
        ReviewConflictResponse(
            id=cf.id,
            revision_id=cf.corpus_revision_id,
            group_id=cf.group_id,
            conflicting_event_ids=json.loads(cf.conflicting_event_ids_json),
            kind=cf.kind,
            resolution_event_id=cf.resolution_event_id,
            created_at=cf.created_at,
        )
        for cf in conflicts
    ]

    return PaperGroupDetail(
        group=summary,
        members=member_dtos,
        screen_result=screen_res,
        pico_result=pico_res,
        events=event_dtos,
        conflicts=conflict_dtos,
    )
