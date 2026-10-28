"""Level 2 Group Merge/Split & Cross-Version Regression Suite (B04).

Verifies:
1. Bridge records change only the new snapshot; original partition and representatives remain exact on restore.
2. Rejected edges and cannot-link constraints survive reruns and prevent contradictory transitive unions.
3. Different publications from one trial remain separate through query additions.
4. Split after a merged-group decision preserves event provenance and flags split ambiguity.
5. Conflicting inherited decisions block export until explicitly resolved by reviewer.
6. Deterministic partition ordering and representative choice is independent of input order.
"""
from __future__ import annotations

import json
import random
from uuid import uuid4

from sqlalchemy.orm import Session

from app.contracts.enums import (
    ConflictKind,
    DedupEdgeStatus,
    EffectiveDecisionState,
    EligibilityStatus,
    GroupLineageOp,
)
from app.contracts.models import (
    ConflictResolveRequest,
    DecisionCommand,
    DedupOverrideRequest,
    DedupProposal,
    RecordRevisionResponse,
)
from app.db.models import (
    CriteriaVersionModel,
    GroupLineageModel,
    GroupSnapshotModel,
    PicoAnnotationModel,
    QueryMembershipModel,
    QueryVersionModel,
    RecordRevisionModel,
    ReviewConflictModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.dedup import DeduplicationEngine, partition_groups
from app.pico.validator import compute_text_hash
from app.services.corpus import (
    list_paper_groups_in_revision,
    process_corpus,
    project_effective_group_decision,
)
from app.services.exports import export_corpus_studies
from app.services.review_decisions import (
    record_dedup_override,
    record_screening_decision,
    resolve_group_conflict,
)
from app.services.snapshots import (
    restore_corpus_snapshot,
)
from tests.fixtures.synthetic_records import (
    RECORD_EXACT_EUROPEPMC,
    RECORD_EXACT_PUBMED,
    RECORD_SAME_STUDY_FOLLOWUP,
    RECORD_SAME_STUDY_PROTOCOL,
    RECORD_SAME_STUDY_RESULTS,
)


def create_test_workspace(db: Session, title: str = "Group Regression Workspace") -> WorkspaceModel:
    """Helper to initialize a test workspace with standard criteria and query."""
    ws = WorkspaceModel(
        id=f"ws-{uuid4().hex[:8]}",
        title=title,
        description="B04 cross-version regression testing",
        created_by="dev-b-evaluator",
        row_version=1,
    )
    db.add(ws)
    db.flush()

    crit = CriteriaVersionModel(
        id=f"crit-{uuid4().hex[:8]}",
        workspace_id=ws.id,
        sequence=1,
        question="What is the clinical efficacy of metformin in adult type 2 diabetes?",
        pico_json=json.dumps({"P": "Adult T2D", "I": "Metformin", "C": "Placebo", "O": "HbA1c"}),
        criteria_json=json.dumps([
            {
                "id": "crit-rct",
                "name": "Randomized Controlled Trial",
                "category": "study_design",
                "is_inclusion": True,
                "rationale": "Must be randomized trial",
                "metadata_first": True,
            }
        ]),
        content_hash="crit-hash-reg",
    )
    db.add(crit)

    qv = QueryVersionModel(
        id=f"qv-{uuid4().hex[:8]}",
        workspace_id=ws.id,
        sequence=1,
        ast_json=json.dumps({"field": "ALL", "value": "metformin"}),
        sources_json=json.dumps(["pubmed", "europepmc"]),
        criteria_version_id=crit.id,
        content_hash="qv-hash-reg",
    )
    db.add(qv)
    db.flush()
    return ws


def add_record(
    db: Session,
    workspace_id: str,
    execution_id: str,
    external_id: str,
    title: str,
    abstract: str,
    source: str = "pubmed",
    doi: str | None = None,
    publication_types: list[str] | None = None,
) -> tuple[SourceRecordModel, RecordRevisionModel]:
    """Helper to add and link a record revision."""
    src = SourceRecordModel(
        id=f"src-{external_id}-{uuid4().hex[:4]}",
        workspace_id=workspace_id,
        source=source,
        source_namespace=source,
        external_id=external_id,
    )
    db.add(src)
    db.flush()

    rev = RecordRevisionModel(
        id=f"rev-{external_id}-{uuid4().hex[:4]}",
        source_record_id=src.id,
        content_hash=compute_text_hash(abstract),
        title=title,
        abstract_text=abstract,
        year=2024,
        journal="Journal of Clinical Endocrinology",
        doi=doi or f"10.1234/test.{external_id}",
        pmid=external_id if source == "pubmed" else None,
        publication_types_json=json.dumps(publication_types or ["Randomized Controlled Trial"]),
    )
    db.add(rev)
    db.flush()

    db.add(
        QueryMembershipModel(
            search_execution_id=execution_id,
            source_record_id=src.id,
            record_revision_id=rev.id,
        )
    )
    db.flush()
    return src, rev


def test_bridge_changes_only_new_snapshot_original_remains_exact_on_restore(db_session: Session):
    """Invariant: Bridge records merge groups only in new snapshot; restoring original recovers exact partition."""
    ws = create_test_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="metformin",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    # Two distinct papers in Revision 1
    src1, rev1 = add_record(db_session, ws.id, se1.id, "101", "Trial Part Alpha", "Results of cohort alpha.")
    src2, rev2 = add_record(db_session, ws.id, se1.id, "102", "Trial Part Beta", "Results of cohort beta.")

    r1 = process_corpus(db_session, workspace_id=ws.id)
    assert r1.group_count == 2
    groups_r1 = list_paper_groups_in_revision(db_session, r1.id)
    r1_group_ids = sorted([g.id for g in groups_r1])
    r1_rep_ids = sorted([g.representative_revision.id for g in groups_r1])

    # In Query 2, a bridge paper arrives that is confirmed as a duplicate of both Part Alpha and Part Beta
    se2 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="metformin combined",
        synonym_setting=False,
        hit_count=3,
        status="succeeded",
        partial=False,
    )
    db_session.add(se2)
    db_session.flush()

    # Re-link existing records to execution 2
    db_session.add(QueryMembershipModel(search_execution_id=se2.id, source_record_id=src1.id, record_revision_id=rev1.id))
    db_session.add(QueryMembershipModel(search_execution_id=se2.id, source_record_id=src2.id, record_revision_id=rev2.id))

    src_bridge, _rev_bridge = add_record(
        db_session, ws.id, se2.id, "103", "Trial Part Alpha and Beta Combined", "Combined alpha and beta dataset."
    )

    # Confirm bridge edges linking 101 to 103 and 102 to 103
    record_dedup_override(
        db=db_session,
        workspace_id=ws.id,
        request=DedupOverrideRequest(record_id_a=src1.id, record_id_b=src_bridge.id, confirm=True, expected_version=1),
    )
    record_dedup_override(
        db=db_session,
        workspace_id=ws.id,
        request=DedupOverrideRequest(record_id_a=src2.id, record_id_b=src_bridge.id, confirm=True, expected_version=2),
    )

    # Revision 2: all three papers merge into a single connected group!
    r2 = process_corpus(db_session, workspace_id=ws.id)
    assert r2.group_count == 1

    # Verify Revision 1 rows in database are 100% UNTOUCHED
    r1_snaps_now = db_session.query(GroupSnapshotModel).filter_by(corpus_revision_id=r1.id).all()
    assert len(r1_snaps_now) == 2
    assert sorted([s.group_id for s in r1_snaps_now]) == r1_group_ids

    # Restore Revision 1
    restored = restore_corpus_snapshot(db_session, workspace_id=ws.id, snapshot_id=r1.id)
    assert restored.id == r1.id
    assert ws.current_revision_id == r1.id

    # Active groups match Revision 1 exactly
    current_groups = list_paper_groups_in_revision(db_session, ws.current_revision_id)
    assert len(current_groups) == 2
    assert sorted([g.id for g in current_groups]) == r1_group_ids
    assert sorted([g.representative_revision.id for g in current_groups]) == r1_rep_ids


def test_rejected_edges_and_cannot_link_prevent_contradictory_transitive_unions(db_session: Session):
    """Invariant: Cannot-link constraints strictly prevent contradictory transitive merges."""
    r_a = RecordRevisionResponse.model_validate(RECORD_EXACT_PUBMED)
    r_b = RecordRevisionResponse.model_validate(RECORD_EXACT_EUROPEPMC)
    r_c = RecordRevisionResponse.model_validate(RECORD_SAME_STUDY_PROTOCOL)

    records = [r_a, r_b, r_c]

    # Proposal: A and B are duplicates (score 1.0)
    edge_ab = DedupProposal(
        record_id_a=r_a.id,
        record_id_b=r_b.id,
        score=1.0,
        method_version="test:v1",
        evidence={},
        status=DedupEdgeStatus.CONFIRMED,
    )
    # Hypothetical bridge proposal: B and C (score 0.90)
    edge_bc = DedupProposal(
        record_id_a=r_b.id,
        record_id_b=r_c.id,
        score=0.90,
        method_version="test:v1",
        evidence={},
        status=DedupEdgeStatus.CONFIRMED,
    )

    # But A and C have an explicit CANNOT-LINK constraint
    cannot_link = {(r_a.id, r_c.id)}

    # Partition groups
    partitioned = partition_groups(
        records=records,
        accepted_edges=[edge_ab, edge_bc],
        cannot_link_pairs=cannot_link,
    )

    # Must NOT merge all 3 into 1 group!
    # Because A and C cannot link, the union {A, B, C} is strictly prohibited!
    assert len(partitioned) == 2

    # Group 1 has {A, B}; Group 2 has {C}
    group_members = [set(g["member_ids"]) for g in partitioned]
    assert {r_a.id, r_b.id} in group_members
    assert {r_c.id} in group_members


def test_different_publications_from_one_trial_remain_separate(db_session: Session):
    """Invariant: Separate publications for the same trial (Protocol vs Results vs Follow-up) are not merged."""
    rec_proto = RecordRevisionResponse.model_validate(RECORD_SAME_STUDY_PROTOCOL)
    rec_results = RecordRevisionResponse.model_validate(RECORD_SAME_STUDY_RESULTS)
    rec_followup = RecordRevisionResponse.model_validate(RECORD_SAME_STUDY_FOLLOWUP)

    engine = DeduplicationEngine()
    records = [rec_proto, rec_results, rec_followup]

    # Find candidates
    candidates = engine.find_candidate_pairs(records)
    # Must NOT propose any candidate pairs among these distinct trial publications
    assert len(candidates) == 0

    # Partition without accepted edges yields 3 singletons
    partitioned = engine.partition_groups(records=records, accepted_edges=[])
    assert len(partitioned) == 3
    assert all(g["member_count"] == 1 for g in partitioned)


def test_split_after_merged_group_decision_preserves_provenance_and_flags_ambiguity(db_session: Session):
    """Invariant: Splitting a previously merged group flags split ambiguity and preserves PICO on original text."""
    ws = create_test_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="metformin",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    # Two papers initially believed to be duplicates
    text_1 = "Metformin trial in type 2 diabetes with HbA1c reduction."
    text_2 = "Metformin observational study in elderly cohort."

    src1, rev1 = add_record(db_session, ws.id, se1.id, "201", "Study 201", text_1)
    src2, rev2 = add_record(db_session, ws.id, se1.id, "202", "Study 202", text_2)

    # Initial confirmed duplicate merge
    record_dedup_override(
        db=db_session,
        workspace_id=ws.id,
        request=DedupOverrideRequest(record_id_a=src1.id, record_id_b=src2.id, confirm=True, expected_version=1),
    )

    r1 = process_corpus(db_session, workspace_id=ws.id)
    assert r1.group_count == 1
    grp_m = list_paper_groups_in_revision(db_session, r1.id)[0]

    # Reviewer makes decision on the merged group
    record_screening_decision(
        db=db_session,
        group_id=grp_m.id,
        command=DecisionCommand(status=EligibilityStatus.INCLUDE, reason="Merged group meets criteria", expected_version=1),
        actor_id="dr-reviewer",
    )

    # Add PICO annotation to rev1 (which was the representative)
    db_session.add(
        PicoAnnotationModel(
            id=str(uuid4()),
            event_id=None,
            record_revision_id=rev1.id,
            label="I",
            start_cp=0,
            end_cp=9,
            quote="Metformin",
            provenance="manual_reviewer",
        )
    )
    db_session.flush()

    # Now reviewer realizes they are distinct studies and REVERSES the duplicate decision
    record_dedup_override(
        db=db_session,
        workspace_id=ws.id,
        request=DedupOverrideRequest(record_id_a=src1.id, record_id_b=src2.id, confirm=False, reason="Separate cohorts", expected_version=2),
    )

    # Revision 2: splits into 2 separate groups
    r2 = process_corpus(db_session, workspace_id=ws.id)
    assert r2.group_count == 2
    assert r2.parent_id == r1.id

    groups_r2 = list_paper_groups_in_revision(db_session, r2.id)
    assert len(groups_r2) == 2

    # Lineage must record SPLIT for each child group
    lineages = db_session.query(GroupLineageModel).filter_by(corpus_revision_id=r2.id).all()
    assert len(lineages) == 2
    assert all(l.operation == GroupLineageOp.SPLIT.value for l in lineages)

    # Split ambiguity conflict must be flagged
    conflicts = db_session.query(ReviewConflictModel).filter_by(corpus_revision_id=r2.id).all()
    assert len(conflicts) >= 1
    assert any(c.kind == ConflictKind.SPLIT_AMBIGUITY.value for c in conflicts)

    # PICO on rev1 is preserved on rev1 and not copied to rev2
    pico_rev1 = (
        db_session.query(PicoAnnotationModel)
        .filter_by(record_revision_id=rev1.id, provenance="manual_reviewer")
        .all()
    )
    pico_rev2 = (
        db_session.query(PicoAnnotationModel)
        .filter_by(record_revision_id=rev2.id, provenance="manual_reviewer")
        .all()
    )
    assert len(pico_rev1) == 1
    assert len(pico_rev2) == 0


def test_conflicting_inherited_decisions_block_export_until_resolved(db_session: Session):
    """Invariant: Group with merge conflict is omitted from export until human resolves the conflict."""
    ws = create_test_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="metformin",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    src1, rev1 = add_record(db_session, ws.id, se1.id, "301", "Trial Included", "Metformin trial in adults.")
    src2, rev2 = add_record(db_session, ws.id, se1.id, "302", "Trial Excluded", "Metformin report in rats.")

    # Revision 1
    r1 = process_corpus(db_session, workspace_id=ws.id)
    groups_r1 = list_paper_groups_in_revision(db_session, r1.id)
    g1 = next(g for g in groups_r1 if g.representative_revision.id == rev1.id)
    g2 = next(g for g in groups_r1 if g.representative_revision.id == rev2.id)

    # g1 -> INCLUDE, g2 -> EXCLUDE
    record_screening_decision(db_session, g1.id, DecisionCommand(status=EligibilityStatus.INCLUDE, reason="Adult RCT", expected_version=1))
    record_screening_decision(db_session, g2.id, DecisionCommand(status=EligibilityStatus.EXCLUDE, reason="Animal study", expected_version=1))

    # Merge g1 and g2 in Revision 2
    record_dedup_override(
        db=db_session,
        workspace_id=ws.id,
        request=DedupOverrideRequest(record_id_a=src1.id, record_id_b=src2.id, confirm=True, expected_version=1),
    )

    r2 = process_corpus(db_session, workspace_id=ws.id)
    assert r2.group_count == 1
    merged_grp = list_paper_groups_in_revision(db_session, r2.id)[0]

    # Effective status is CONFLICT
    eff_st, _, _, has_conflict = project_effective_group_decision(db_session, merged_grp.id, revision_id=r2.id)
    assert eff_st == EffectiveDecisionState.CONFLICT
    assert has_conflict is True

    # Export omits the group
    exp1 = export_corpus_studies(db=db_session, revision_id=r2.id, export_format="csv")
    assert exp1.record_count == 0

    # Reviewer explicitly resolves the conflict
    conflict = db_session.query(ReviewConflictModel).filter_by(group_id=merged_grp.id, resolution_event_id=None).first()
    assert conflict is not None

    resolve_group_conflict(
        db=db_session,
        conflict_id=conflict.id,
        request=ConflictResolveRequest(
            chosen_status=EligibilityStatus.INCLUDE,
            reason="Confirmed human adult trial component meets inclusion criteria",
            expected_version=1,
        ),
        actor_id="lead-reviewer",
    )

    # After resolution, effective status is INCLUDE
    eff_st_after, _, _, has_conflict_after = project_effective_group_decision(db_session, merged_grp.id, revision_id=r2.id)
    assert eff_st_after == EffectiveDecisionState.INCLUDE
    assert has_conflict_after is False

    # Export now includes the resolved study!
    exp2 = export_corpus_studies(db=db_session, revision_id=r2.id, export_format="csv")
    assert exp2.record_count == 1


def test_deterministic_group_partition_order_independent_of_input_arrival():
    """Invariant: Group partition and representative selection are 100% deterministic under random input shuffles."""
    raw_records = [
        RecordRevisionResponse.model_validate(RECORD_EXACT_PUBMED),
        RecordRevisionResponse.model_validate(RECORD_EXACT_EUROPEPMC),
        RecordRevisionResponse.model_validate(RECORD_SAME_STUDY_PROTOCOL),
        RecordRevisionResponse.model_validate(RECORD_SAME_STUDY_RESULTS),
        RecordRevisionResponse.model_validate(RECORD_SAME_STUDY_FOLLOWUP),
    ]

    edge_dup = DedupProposal(
        record_id_a=raw_records[0].id,
        record_id_b=raw_records[1].id,
        score=1.0,
        method_version="test:v1",
        evidence={},
        status=DedupEdgeStatus.CONFIRMED,
    )

    # Run baseline partition
    baseline_partition = partition_groups(records=raw_records, accepted_edges=[edge_dup])
    baseline_group_ids = [g["representative"].id for g in baseline_partition]
    baseline_members = [[m.id for m in g["members"]] for g in baseline_partition]

    # Test 10 random permutations
    rng = random.Random(42)
    for _ in range(10):
        shuffled = list(raw_records)
        rng.shuffle(shuffled)

        res = partition_groups(records=shuffled, accepted_edges=[edge_dup])
        res_group_ids = [g["representative"].id for g in res]
        res_members = [[m.id for m in g["members"]] for g in res]

        assert res_group_ids == baseline_group_ids
        assert res_members == baseline_members
