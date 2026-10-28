"""Unit tests for Duplicate Genealogy & Decision Reconciliation domain service."""
import hashlib
import json
import pytest
from sqlalchemy.orm import Session
from uuid import uuid4

from app.contracts.enums import (
    DecisionEventType,
    DedupEdgeStatus,
    DuplicateConflictClassification,
    DuplicateMergeOperation,
    DuplicateRelationshipStatus,
    EffectiveDecisionState,
    EligibilityStatus,
    SourceNamespace,
)
from app.contracts.models import (
    DuplicateReconcileRequest,
    DuplicateReverseMergeRequest,
    DuplicateSplitRequest,
)
from app.db.models import (
    CorpusRevisionModel,
    CriteriaVersionModel,
    DedupEdgeModel,
    DuplicateMergeEventModel,
    GroupMemberModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewConflictModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.genealogy import (
    _get_next_event_sequence,
    get_duplicate_group_genealogy,
    get_workspace_duplicate_overview,
    reconcile_duplicate_conflict,
    reverse_merge_event,
    split_duplicate_group,
)


@pytest.fixture
def genealogy_test_setup(db_session: Session):
    """Seed workspace, criteria version, and corpus revision."""
    ws = WorkspaceModel(id="ws-genealogy-unit", title="Genealogy Unit Review", created_by="reviewer-1")
    crit = CriteriaVersionModel(
        id="crit-gen-1",
        workspace_id=ws.id,
        sequence=1,
        question="Clinical trial review question",
        pico_json=json.dumps({"p": "patients", "i": "intervention", "c": "comparator", "o": "outcome"}),
        criteria_json=json.dumps({"inclusion": ["human trials"], "exclusion": []}),
        content_hash="crit-hash-gen",
    )
    db_session.add_all([ws, crit])
    db_session.flush()

    corpus_rev = CorpusRevisionModel(
        id="crev-gen-1",
        workspace_id=ws.id,
        criteria_version_id=crit.id,
        dedup_version="v1",
        state="published",
        fingerprint="fp-corpus-1",
    )
    db_session.add(corpus_rev)
    db_session.commit()
    return ws, crit, corpus_rev


def _seed_duplicate_group(
    db: Session,
    workspace_id: str,
    group_id: str,
    corpus_revision_id: str = "crev-gen-1",
    record_a_decision: str = "include",
    record_b_decision: str = "exclude",
) -> tuple[PaperGroupModel, SourceRecordModel, SourceRecordModel]:
    """Helper to seed a 2-record duplicate paper group with specified decisions."""
    title_a = "Metformin efficacy in type 2 diabetes mellitus: multicenter study"
    doi = "10.1001/jama.2023.01"
    hash_a = hashlib.sha256(title_a.encode()).hexdigest()

    rec_a = SourceRecordModel(
        workspace_id=workspace_id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id=f"PMID-{group_id}-a",
    )
    db.add(rec_a)
    db.flush()

    rev_a = RecordRevisionModel(
        source_record_id=rec_a.id,
        content_hash=hash_a,
        title=title_a,
        authors_json=json.dumps(["Miller AB", "Chen L"]),
        year=2023,
        doi=doi,
        journal="JAMA",
        abstract_text="Study on oral metformin versus control.",
    )
    db.add(rev_a)
    db.flush()

    # Europe PMC duplicate
    title_b = "Metformin efficacy in type 2 diabetes mellitus: multicenter study."
    hash_b = hashlib.sha256(title_b.encode()).hexdigest()

    rec_b = SourceRecordModel(
        workspace_id=workspace_id,
        source=SourceNamespace.EUROPEPMC.value,
        source_namespace=SourceNamespace.EUROPEPMC.value,
        external_id=f"PMC-{group_id}-b",
    )
    db.add(rec_b)
    db.flush()

    rev_b = RecordRevisionModel(
        source_record_id=rec_b.id,
        content_hash=hash_b,
        title=title_b,
        authors_json=json.dumps(["Miller A.B.", "Chen L."]),
        year=2023,
        doi=doi,
        journal="JAMA",
        abstract_text="Study on oral metformin versus control in diabetic cohort.",
    )
    db.add(rev_b)
    db.flush()

    # Paper Group
    grp = PaperGroupModel(
        id=group_id,
        workspace_id=workspace_id,
        membership_fingerprint=hash_a[:32],
        row_version=1,
    )
    db.add(grp)
    db.flush()

    mem_a = GroupMemberModel(group_id=grp.id, source_record_id=rec_a.id)
    mem_b = GroupMemberModel(group_id=grp.id, source_record_id=rec_b.id)
    db.add_all([mem_a, mem_b])
    db.flush()

    # Dedup Edge with exact DOI match evidence
    edge = DedupEdgeModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        record_id_a=rec_a.id,
        record_id_b=rec_b.id,
        score=1.0,
        method_version="exact_doi:v1.0",
        status=DedupEdgeStatus.CONFIRMED.value,
        evidence_json=json.dumps({
            "doi_match": True,
            "exact_doi": doi,
            "title_similarity": 0.98,
        }),
    )
    db.add(edge)

    # Initial Merge Event
    merge_event = DuplicateMergeEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=grp.id,
        canonical_record_id=rec_a.id,
        operation=DuplicateMergeOperation.MERGE.value,
        affected_source_ids_json=json.dumps([rec_a.id, rec_b.id]),
        match_evidence_json=json.dumps({"doi": doi, "score": 1.0}),
        pre_operation_state_json=json.dumps({
            "groups": [
                {"group_id": "grp-pre-a", "members": [rec_a.id]},
                {"group_id": "grp-pre-b", "members": [rec_b.id]},
            ]
        }),
        actor_id="system",
        reason="Exact DOI match automated deduplication pass",
        status="active",
    )
    db.add(merge_event)

    # Review events for individual decisions
    seq_1 = _get_next_event_sequence(db, workspace_id)
    ev_a = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        sequence=seq_1,
        event_type=DecisionEventType.SCREEN_DECISION.value,
        group_id=grp.id,
        actor_id="reviewer-a",
        reason="Meets RCT criteria",
        payload_json=json.dumps({"status": record_a_decision, "source_record_id": rec_a.id, "actor_type": "human"}),
    )
    db.add(ev_a)
    db.flush()

    seq_2 = _get_next_event_sequence(db, workspace_id)
    ev_b = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        sequence=seq_2,
        event_type=DecisionEventType.SCREEN_DECISION.value,
        group_id=grp.id,
        actor_id="ml-classifier",
        reason="No explicit comparator found",
        payload_json=json.dumps({"status": record_b_decision, "source_record_id": rec_b.id, "actor_type": "automated"}),
    )
    db.add(ev_b)
    db.flush()

    # Review Conflict if diverging
    if record_a_decision != record_b_decision:
        conflict = ReviewConflictModel(
            id=str(uuid4()),
            corpus_revision_id=corpus_revision_id,
            group_id=grp.id,
            kind=DuplicateConflictClassification.DECISION_DIVERGENCE.value,
            conflicting_event_ids_json=json.dumps([ev_a.id, ev_b.id]),
        )
        db.add(conflict)

    db.commit()
    return grp, rec_a, rec_b


def test_get_duplicate_group_genealogy(db_session: Session, genealogy_test_setup):
    """Verify detailed genealogy retrieval: member details, canonical record, and matching signals."""
    ws, _, corpus_rev = genealogy_test_setup
    grp, rec_a, rec_b = _seed_duplicate_group(
        db_session, ws.id, "grp-test-genealogy", corpus_revision_id=corpus_rev.id, record_a_decision="include", record_b_decision="exclude"
    )

    genealogy = get_duplicate_group_genealogy(db_session, ws.id, grp.id)

    assert genealogy.workspace_id == ws.id
    assert genealogy.group_id == grp.id
    assert genealogy.canonical_record_id == rec_a.id
    assert len(genealogy.members) == 2

    # Canonical member checks
    canonical_members = [m for m in genealogy.members if m.is_canonical]
    assert len(canonical_members) == 1
    assert canonical_members[0].source_record_id == rec_a.id
    assert canonical_members[0].individual_decision == "include"

    # Non-canonical member checks
    non_canonical = [m for m in genealogy.members if not m.is_canonical][0]
    assert non_canonical.source_record_id == rec_b.id
    assert non_canonical.individual_decision == "exclude"

    # Pairwise matching signals
    assert len(genealogy.pairwise_signals) >= 1
    assert genealogy.pairwise_signals[0].score == 1.0
    assert any("exact doi" in s.lower() for s in genealogy.pairwise_signals[0].signals)

    # Active conflict detection
    assert len(genealogy.active_conflicts) == 1
    assert genealogy.active_conflicts[0].classification == DuplicateConflictClassification.DECISION_DIVERGENCE
    assert genealogy.active_conflicts[0].is_resolved is False

    # Field provenance
    title_prov = next(f for f in genealogy.field_provenance if f.field_name.lower() == "title")
    assert title_prov.canonical_source == SourceNamespace.PUBMED.value
    assert title_prov.has_discrepancy is True


def test_get_workspace_duplicate_overview(db_session: Session, genealogy_test_setup):
    """Verify workspace summary counts and filtering."""
    ws, _, corpus_rev = genealogy_test_setup
    _seed_duplicate_group(db_session, ws.id, "grp-ov-1", corpus_revision_id=corpus_rev.id, record_a_decision="include", record_b_decision="exclude")
    _seed_duplicate_group(db_session, ws.id, "grp-ov-2", corpus_revision_id=corpus_rev.id, record_a_decision="include", record_b_decision="include")

    overview = get_workspace_duplicate_overview(db_session, ws.id)
    assert overview.total_duplicate_groups == 2
    assert overview.total_duplicate_records == 4
    assert overview.groups_with_conflicts == 1

    # Conflict filter
    conflict_only = get_workspace_duplicate_overview(db_session, ws.id, conflict_only=True)
    assert len(conflict_only.groups) == 1
    assert conflict_only.groups[0].group_id == "grp-ov-1"


def test_reconcile_duplicate_conflict(db_session: Session, genealogy_test_setup):
    """Verify safe conflict reconciliation with human attribution and audit event."""
    ws, _, corpus_rev = genealogy_test_setup
    grp, rec_a, rec_b = _seed_duplicate_group(
        db_session, ws.id, "grp-reconcile-1", corpus_revision_id=corpus_rev.id, record_a_decision="include", record_b_decision="exclude"
    )

    reconcile_req = DuplicateReconcileRequest(
        chosen_decision=EligibilityStatus.INCLUDE,
        reason="Audited full-text methodology confirms RCT inclusion criteria satisfied",
        actor_id="senior-methodologist",
        apply_to_all_members=True,
        expected_version=1,
    )

    updated_genealogy = reconcile_duplicate_conflict(db_session, ws.id, grp.id, reconcile_req)

    assert updated_genealogy.effective_decision == "include"
    assert len(updated_genealogy.active_conflicts) == 0
    assert updated_genealogy.row_version == 2

    # Verify both records received the decision
    for mem in updated_genealogy.members:
        assert mem.individual_decision == "include"

    # Verify audit trail event
    rev_events = (
        db_session.query(ReviewEventModel)
        .filter(ReviewEventModel.group_id == grp.id, ReviewEventModel.event_type == DecisionEventType.CONFLICT_RESOLUTION.value)
        .all()
    )
    assert len(rev_events) == 1
    assert rev_events[0].actor_id == "senior-methodologist"

    # Verify merge event was logged
    merge_evs = (
        db_session.query(DuplicateMergeEventModel)
        .filter(
            DuplicateMergeEventModel.group_id == grp.id,
            DuplicateMergeEventModel.operation == DuplicateMergeOperation.RECONCILIATION.value,
        )
        .all()
    )
    assert len(merge_evs) == 1
    assert merge_evs[0].actor_id == "senior-methodologist"


def test_split_duplicate_group_enforces_cannot_link(db_session: Session, genealogy_test_setup):
    """Verify safe split separating records, creating a new group, and enforcing cannot-link."""
    ws, _, corpus_rev = genealogy_test_setup
    grp, rec_a, rec_b = _seed_duplicate_group(
        db_session, ws.id, "grp-split-1", corpus_revision_id=corpus_rev.id, record_a_decision="include", record_b_decision="exclude"
    )

    split_req = DuplicateSplitRequest(
        source_record_ids_to_split=[rec_b.id],
        reason="Companion study phase with distinct patient cohort and separate clinical outcomes",
        mark_as_cannot_link=True,
        actor_id="lead-investigator",
        expected_version=1,
    )

    updated_genealogy = split_duplicate_group(db_session, ws.id, grp.id, split_req)

    # Original group should now only contain record A
    assert len(updated_genealogy.members) == 1
    assert updated_genealogy.members[0].source_record_id == rec_a.id
    assert updated_genealogy.row_version == 2

    # Check newly created group for record B
    mem_b_link = db_session.query(GroupMemberModel).filter(GroupMemberModel.source_record_id == rec_b.id).first()
    assert mem_b_link is not None
    assert mem_b_link.group_id != grp.id

    new_grp = db_session.query(PaperGroupModel).filter(PaperGroupModel.id == mem_b_link.group_id).first()
    assert new_grp is not None

    # Check permanent cannot-link edge constraint
    cannot_link_edge = (
        db_session.query(DedupEdgeModel)
        .filter(
            (
                (DedupEdgeModel.record_id_a == rec_a.id) & (DedupEdgeModel.record_id_b == rec_b.id)
            )
            | (
                (DedupEdgeModel.record_id_a == rec_b.id) & (DedupEdgeModel.record_id_b == rec_a.id)
            ),
            DedupEdgeModel.status == DedupEdgeStatus.REJECTED.value,
        )
        .first()
    )
    assert cannot_link_edge is not None
    assert "cannot_link" in cannot_link_edge.evidence_json


def test_reverse_merge_event(db_session: Session, genealogy_test_setup):
    """Verify safe reversal of merge event when no downstream conflicts block reversal."""
    ws, _, corpus_rev = genealogy_test_setup
    grp, rec_a, rec_b = _seed_duplicate_group(
        db_session, ws.id, "grp-reverse-1", corpus_revision_id=corpus_rev.id, record_a_decision="include", record_b_decision="include"
    )

    # Find the initial merge event
    initial_merge = (
        db_session.query(DuplicateMergeEventModel)
        .filter(DuplicateMergeEventModel.group_id == grp.id)
        .first()
    )
    assert initial_merge is not None

    reverse_req = DuplicateReverseMergeRequest(
        merge_event_id=initial_merge.id,
        reason="Automated title match error on companion paper",
        actor_id="qa-auditor",
        expected_version=1,
    )

    updated_genealogy = reverse_merge_event(db_session, ws.id, grp.id, reverse_req)

    # The group should have split back into pre-merge state (1 member remaining in original)
    assert len(updated_genealogy.members) == 1

    # Initial merge event should be marked reversed
    db_session.refresh(initial_merge)
    assert initial_merge.status == "reversed"
    assert initial_merge.reversal_event_id is not None
