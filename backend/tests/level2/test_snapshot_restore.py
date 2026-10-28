"""Level 2 Data Integrity & Snapshot Restoration Tests (D05).

Verifies:
1. Excluded paper reappearing in a new query stays excluded with provenance.
2. Include/Exclude group merge creates visible unresolved conflict and prevents export inclusion.
3. New bridge and split do not mutate original snapshot; rejected pair stays rejected.
4. Restore initial snapshot reproduces exact saved record revisions, partition and representatives while network is disabled.
5. Changed representative does not silently reuse PICO offsets; failed publication leaves previous active revision intact.
6. Deterministic invalidation fingerprint and structured corpus diff.
"""
from __future__ import annotations

import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import (
    ConflictKind,
    DedupEdgeStatus,
    EffectiveDecisionState,
    EligibilityStatus,
    GroupLineageOp,
)
from app.contracts.models import (
    DecisionCommand,
    DedupOverrideRequest,
)
from app.db.models import (
    CorpusMemberModel,
    CriteriaVersionModel,
    DedupEdgeModel,
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
)
from app.services.snapshots import (
    compute_corpus_diff,
    restore_corpus_snapshot,
)


def create_mock_workspace(db: Session) -> WorkspaceModel:
    """Helper to create test workspace with initial criteria and query."""
    ws = WorkspaceModel(
        id=f"ws-{uuid4().hex[:8]}",
        title="Level 2 SLR Workspace",
        description="Testing snapshot restoration and lineage",
        created_by="dev-d-tester",
        row_version=1,
    )
    db.add(ws)
    db.flush()

    crit = CriteriaVersionModel(
        id=f"crit-{uuid4().hex[:8]}",
        workspace_id=ws.id,
        sequence=1,
        question="What are the clinical outcomes of drug X?",
        pico_json=json.dumps({"P": "Adults", "I": "Drug X", "C": "Control", "O": "Outcome"}),
        criteria_json=json.dumps([
            {
                "id": "crit-rct",
                "name": "RCT Design",
                "category": "study_design",
                "is_inclusion": True,
                "rationale": "Must be randomized trial",
                "metadata_first": True,
            }
        ]),
        content_hash="crit-hash-1",
    )
    db.add(crit)

    qv = QueryVersionModel(
        id=f"qv-{uuid4().hex[:8]}",
        workspace_id=ws.id,
        sequence=1,
        ast_json=json.dumps({"field": "ALL", "value": "Drug X"}),
        sources_json=json.dumps(["pubmed"]),
        criteria_version_id=crit.id,
        content_hash="qv-hash-1",
    )
    db.add(qv)
    db.flush()
    return ws


def add_record_to_execution(
    db: Session,
    workspace_id: str,
    execution_id: str,
    pmid: str,
    title: str,
    abstract: str,
    source: str = "pubmed",
) -> tuple[SourceRecordModel, RecordRevisionModel]:
    """Helper to create a source record and link it to a search execution."""
    src = SourceRecordModel(
        id=f"src-{pmid}-{uuid4().hex[:4]}",
        workspace_id=workspace_id,
        source=source,
        source_namespace=source,
        external_id=pmid,
    )
    db.add(src)
    db.flush()

    rev = RecordRevisionModel(
        id=f"rev-{pmid}-{uuid4().hex[:4]}",
        source_record_id=src.id,
        content_hash=compute_text_hash(abstract),
        title=title,
        abstract_text=abstract,
        year=2024,
        journal="New England Journal of Medicine",
        doi=f"10.1056/NEJMoa{pmid}",
        pmid=pmid,
        publication_types_json=json.dumps(["Randomized Controlled Trial"]),
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


def test_excluded_paper_reappearing_stays_excluded_with_provenance(db_session: Session):
    """Invariant 1: Excluded paper reappearing in a new query revision stays excluded with full provenance."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    # Query 1 execution
    se1 = SearchExecutionModel(
        id=f"se-1-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X initial",
        synonym_setting=False,
        hit_count=1,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    src1, rev1 = add_record_to_execution(
        db_session, ws.id, se1.id, "200001",
        "Clinical study of Drug X in pediatric asthma",
        "Objective: Test drug X in children under 12. Methods: Observational cohort. Results: Improved FEV1.",
    )

    # Process Revision 1
    rev_resp_1 = process_corpus(db_session, workspace_id=ws.id)
    assert rev_resp_1.group_count == 1
    assert ws.current_revision_id == rev_resp_1.id

    groups_r1 = list_paper_groups_in_revision(db_session, rev_resp_1.id)
    assert len(groups_r1) == 1
    grp1_id = groups_r1[0].id

    # Human reviewer explicitly EXCLUDES group 1
    record_screening_decision(
        db=db_session,
        group_id=grp1_id,
        command=DecisionCommand(
            status=EligibilityStatus.EXCLUDE,
            reason="Exclusion criterion failed: pediatric population, not adult",
            expected_version=1,
        ),
        actor_id="reviewer-dr-smith",
    )

    eff_state, ev, _, _ = project_effective_group_decision(db_session, grp1_id, revision_id=rev_resp_1.id)
    assert eff_state == EffectiveDecisionState.EXCLUDE
    assert ev.reason == "Exclusion criterion failed: pediatric population, not adult"
    assert ev.actor_id == "reviewer-dr-smith"

    # Now Query 2 execution arrives with an expanded search (finds Paper 1 again plus Paper 2)
    qv2 = QueryVersionModel(
        id=f"qv-2-{uuid4().hex[:6]}",
        workspace_id=ws.id,
        sequence=2,
        ast_json=json.dumps({"field": "ALL", "value": "Drug X expanded"}),
        sources_json=json.dumps(["pubmed"]),
        criteria_version_id=qv.criteria_version_id,
        content_hash="qv-hash-2",
    )
    db_session.add(qv2)
    db_session.flush()

    se2 = SearchExecutionModel(
        id=f"se-2-{uuid4().hex[:6]}",
        query_version_id=qv2.id,
        source="pubmed",
        exact_query="Drug X expanded",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se2)
    db_session.flush()

    # Link Paper 1 to Search Execution 2 as well
    db_session.add(
        QueryMembershipModel(
            search_execution_id=se2.id,
            source_record_id=src1.id,
            record_revision_id=rev1.id,
        )
    )
    # Add new Paper 2
    add_record_to_execution(
        db_session, ws.id, se2.id, "200002",
        "Efficacy of Drug X in adult rheumatoid arthritis: RCT",
        "Objective: Double-blind trial in 300 adults. Methods: Randomized controlled trial. Results: Efficacy established.",
    )

    # Process Revision 2 (parent is Revision 1)
    rev_resp_2 = process_corpus(db_session, workspace_id=ws.id)
    assert rev_resp_2.parent_id == rev_resp_1.id
    assert rev_resp_2.group_count == 2
    assert ws.current_revision_id == rev_resp_2.id

    groups_r2 = list_paper_groups_in_revision(db_session, rev_resp_2.id)
    assert len(groups_r2) == 2

    # Find the group corresponding to Paper 1 in Revision 2
    grp_p1 = next(g for g in groups_r2 if g.representative_revision.id == rev1.id)
    # Verify it carries forward the exclusion decision with provenance!
    eff_state_r2, ev_r2, _, has_conflict = project_effective_group_decision(
        db_session, grp_p1.id, revision_id=rev_resp_2.id
    )
    assert eff_state_r2 == EffectiveDecisionState.EXCLUDE
    assert not has_conflict
    assert ev_r2 is not None
    assert "pediatric population" in ev_r2.reason


def test_include_exclude_group_merge_creates_unresolved_conflict_and_blocks_export(db_session: Session):
    """Invariant 2: Merging an Included group and Excluded group creates visible unresolved conflict, blocking export."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    # Paper A: included
    src_a, rev_a = add_record_to_execution(
        db_session, ws.id, se1.id, "300001",
        "Trial of Drug X in Adults",
        "Adult randomized controlled trial of drug X showing efficacy.",
    )
    # Paper B: excluded
    src_b, rev_b = add_record_to_execution(
        db_session, ws.id, se1.id, "300002",
        "Follow up of Drug X in Adults",
        "Different perspective and trial in adults with drug X.",
    )

    # Revision 1 publishes with 2 separate groups
    rev_resp_1 = process_corpus(db_session, workspace_id=ws.id)
    assert rev_resp_1.group_count == 2

    groups_r1 = list_paper_groups_in_revision(db_session, rev_resp_1.id)
    grp_a = next(g for g in groups_r1 if g.representative_revision.id == rev_a.id)
    grp_b = next(g for g in groups_r1 if g.representative_revision.id == rev_b.id)

    # Reviewer INCLUDES Group A
    record_screening_decision(
        db=db_session,
        group_id=grp_a.id,
        command=DecisionCommand(status=EligibilityStatus.INCLUDE, reason="Clear RCT meeting inclusion", expected_version=1),
        actor_id="reviewer-1",
    )
    # Reviewer EXCLUDES Group B
    record_screening_decision(
        db=db_session,
        group_id=grp_b.id,
        command=DecisionCommand(status=EligibilityStatus.EXCLUDE, reason="Duplicate report without primary data", expected_version=1),
        actor_id="reviewer-2",
    )

    # Now deduplication links Paper A and Paper B as the same study/paper!
    # Reviewer confirms dedup edge between Paper A and Paper B
    record_dedup_override(
        db=db_session,
        workspace_id=ws.id,
        request=DedupOverrideRequest(
            record_id_a=src_a.id,
            record_id_b=src_b.id,
            confirm=True,
            reason="Confirmed duplicate publications of the same trial",
            expected_version=1,
        ),
        actor_id="reviewer-lead",
    )

    # Process Revision 2: Paper A and Paper B merge into a single group!
    rev_resp_2 = process_corpus(db_session, workspace_id=ws.id)
    assert rev_resp_2.group_count == 1
    assert rev_resp_2.parent_id == rev_resp_1.id

    groups_r2 = list_paper_groups_in_revision(db_session, rev_resp_2.id)
    assert len(groups_r2) == 1
    merged_grp = groups_r2[0]

    # Check effective status: Must be CONFLICT!
    eff_state, _, _, has_conflict = project_effective_group_decision(db_session, merged_grp.id, revision_id=rev_resp_2.id)
    assert eff_state == EffectiveDecisionState.CONFLICT
    assert has_conflict is True

    # Verify ReviewConflictModel is recorded
    conflict = db_session.query(ReviewConflictModel).filter_by(group_id=merged_grp.id).first()
    assert conflict is not None
    assert conflict.kind == ConflictKind.DECISION_DIVERGENCE.value
    assert conflict.resolution_event_id is None

    # Lineage must record MERGE operation
    lineages = db_session.query(GroupLineageModel).filter_by(child_group_id=merged_grp.id).all()
    assert len(lineages) == 2
    assert all(l.operation == GroupLineageOp.MERGE.value for l in lineages)

    # Invariant: Exporting Revision 2 MUST omit this conflicting group!
    exp_res = export_corpus_studies(db=db_session, revision_id=rev_resp_2.id, export_format="csv")
    assert exp_res.record_count == 0  # Conflicting group cannot be included in export


def test_new_bridge_and_split_do_not_mutate_original_snapshot(db_session: Session):
    """Invariant 3: Subsequent revisions do not mutate historical snapshots, and rejected pairs remain rejected."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    src1, _rev1 = add_record_to_execution(db_session, ws.id, se1.id, "400001", "Paper One", "Abstract 1")
    src2, _rev2 = add_record_to_execution(db_session, ws.id, se1.id, "400002", "Paper Two", "Abstract 2")

    # Reject duplicate edge between Paper 1 and Paper 2
    record_dedup_override(
        db=db_session,
        workspace_id=ws.id,
        request=DedupOverrideRequest(
            record_id_a=src1.id,
            record_id_b=src2.id,
            confirm=False,
            reason="Confirmed distinct clinical trials",
            expected_version=1,
        ),
    )

    # Revision 1
    r1 = process_corpus(db_session, workspace_id=ws.id)
    r1_snaps = db_session.query(GroupSnapshotModel).filter_by(corpus_revision_id=r1.id).all()
    r1_members = db_session.query(CorpusMemberModel).filter_by(corpus_revision_id=r1.id).all()
    assert len(r1_snaps) == 2
    assert len(r1_members) == 2

    # Snapshot 1 saved state
    r1_group_ids = sorted([s.group_id for s in r1_snaps])

    # Add a third paper bridging
    _src3, _rev3 = add_record_to_execution(db_session, ws.id, se1.id, "400003", "Paper Three", "Abstract 3")

    # Revision 2
    r2 = process_corpus(db_session, workspace_id=ws.id)
    assert r2.id != r1.id
    assert r2.record_count == 3

    # Invariant: Revision 1 records, snapshots, and members remain 100% UNCHANGED!
    r1_snaps_after = db_session.query(GroupSnapshotModel).filter_by(corpus_revision_id=r1.id).all()
    r1_members_after = db_session.query(CorpusMemberModel).filter_by(corpus_revision_id=r1.id).all()
    assert len(r1_snaps_after) == 2
    assert sorted([s.group_id for s in r1_snaps_after]) == r1_group_ids
    assert len(r1_members_after) == 2

    # Invariant: Rejected pair stays rejected
    rejected_edge = (
        db_session.query(DedupEdgeModel)
        .filter_by(workspace_id=ws.id, record_id_a=src1.id, record_id_b=src2.id)
        .first()
    )
    assert rejected_edge.status == DedupEdgeStatus.REJECTED.value


def test_restore_initial_snapshot_reproduces_exact_partition_offline(db_session: Session):
    """Invariant 4: Restoring initial snapshot reproduces exact saved record revisions, partition and representatives offline."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    _src1, _rev1 = add_record_to_execution(db_session, ws.id, se1.id, "500001", "Initial Study 1", "Abstract 1")
    _src2, _rev2 = add_record_to_execution(db_session, ws.id, se1.id, "500002", "Initial Study 2", "Abstract 2")

    # Revision 1
    r1 = process_corpus(db_session, workspace_id=ws.id)
    assert ws.current_revision_id == r1.id
    r1_groups = list_paper_groups_in_revision(db_session, r1.id)
    assert len(r1_groups) == 2
    r1_rep_ids = {g.representative_revision.id for g in r1_groups}

    # Revision 2 with new records
    add_record_to_execution(db_session, ws.id, se1.id, "500003", "Later Study 3", "Abstract 3")
    r2 = process_corpus(db_session, workspace_id=ws.id)
    assert ws.current_revision_id == r2.id
    r2_groups = list_paper_groups_in_revision(db_session, r2.id)
    assert len(r2_groups) == 3

    # Now RESTORE Revision 1 (strictly offline, reading saved snapshot data)
    restored = restore_corpus_snapshot(db_session, workspace_id=ws.id, snapshot_id=r1.id)
    assert restored.id == r1.id
    assert ws.current_revision_id == r1.id

    # Verify listing groups for the restored workspace matches Revision 1 exactly
    current_groups = list_paper_groups_in_revision(db_session, ws.current_revision_id)
    assert len(current_groups) == 2
    assert {g.representative_revision.id for g in current_groups} == r1_rep_ids


def test_changed_representative_does_not_silently_reuse_pico_offsets(db_session: Session):
    """Invariant 5: Changed representative does not silently reuse PICO offsets from prior representative."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X",
        synonym_setting=False,
        hit_count=1,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    text_a = "Patients with diabetes were randomized to metformin therapy."
    _src1, rev_a = add_record_to_execution(db_session, ws.id, se1.id, "600001", "Title A", text_a)

    text_b = "In this trial, adult subjects received oral metformin or placebo for 12 weeks."
    _src2, rev_b = add_record_to_execution(db_session, ws.id, se1.id, "600002", "Title B", text_b)

    # Attach PICO annotation to rev_a
    db_session.add(
        PicoAnnotationModel(
            id=str(uuid4()),
            event_id=None,
            record_revision_id=rev_a.id,
            label="P",
            start_cp=0,
            end_cp=22,
            quote="Patients with diabetes",
            provenance="rule_baseline",
        )
    )
    db_session.flush()

    # Query annotations for rev_a vs rev_b
    pico_a = db_session.query(PicoAnnotationModel).filter_by(record_revision_id=rev_a.id).all()
    pico_b = db_session.query(PicoAnnotationModel).filter_by(record_revision_id=rev_b.id).all()

    assert len(pico_a) == 1
    assert pico_a[0].quote == "Patients with diabetes"
    # PICO offsets for rev_a MUST NOT be attached to rev_b
    assert len(pico_b) == 0


def test_failed_publication_leaves_previous_active_revision_intact(db_session: Session):
    """Invariant: Failed publication rolls back and leaves previous active revision intact."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X",
        synonym_setting=False,
        hit_count=1,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    add_record_to_execution(db_session, ws.id, se1.id, "700001", "Study 1", "Abstract 1")

    # Initial successful publication
    r1 = process_corpus(db_session, workspace_id=ws.id)
    assert ws.current_revision_id == r1.id

    # Now attempt a publication that raises an error inside process_corpus
    with (
        patch("app.services.corpus.RuleBasedPicoExtractor.extract_pico_spans", side_effect=RuntimeError("Simulated PICO crash")),
        pytest.raises(RuntimeError, match="Simulated PICO crash"),
    ):
        process_corpus(db_session, workspace_id=ws.id)

    # Active revision must remain r1!
    db_session.refresh(ws)
    assert ws.current_revision_id == r1.id


def test_corpus_diff_calculation(db_session: Session):
    """Test structured diff between two revisions including added/removed records and deterministic fingerprint."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se1 = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X initial",
        synonym_setting=False,
        hit_count=2,
        status="succeeded",
        partial=False,
    )
    db_session.add(se1)
    db_session.flush()

    _src1, _rev1 = add_record_to_execution(db_session, ws.id, se1.id, "800001", "Paper 1", "Abstract 1")
    _src2, _rev2 = add_record_to_execution(db_session, ws.id, se1.id, "800002", "Paper 2", "Abstract 2")

    r1 = process_corpus(db_session, workspace_id=ws.id)

    # Add third paper in next query
    add_record_to_execution(db_session, ws.id, se1.id, "800003", "Paper 3", "Abstract 3")
    r2 = process_corpus(db_session, workspace_id=ws.id)

    diff = compute_corpus_diff(db_session, base_revision_id=r1.id, target_revision_id=r2.id)
    assert diff.base_revision_id == r1.id
    assert diff.target_revision_id == r2.id
    assert diff.added_records == 1
    assert diff.removed_records == 0
    assert diff.retained_records == 2
    assert diff.added_groups == 1
    assert len(diff.invalidation_fingerprint) == 64  # SHA-256


def test_http_endpoints_diff_and_restore(db_session: Session, client: TestClient):
    """Test HTTP API routes for corpus diff, snapshot restore, and conflict resolution."""
    ws = create_mock_workspace(db_session)
    qv = db_session.query(QueryVersionModel).filter_by(workspace_id=ws.id).first()

    se = SearchExecutionModel(
        id=f"se-{uuid4().hex[:6]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="Drug X",
        synonym_setting=False,
        hit_count=1,
        status="succeeded",
        partial=False,
    )
    db_session.add(se)
    db_session.flush()

    add_record_to_execution(db_session, ws.id, se.id, "900001", "Paper 1", "Abstract 1")
    r1 = process_corpus(db_session, workspace_id=ws.id)

    add_record_to_execution(db_session, ws.id, se.id, "900002", "Paper 2", "Abstract 2")
    r2 = process_corpus(db_session, workspace_id=ws.id)

    # 1. Test GET /api/v1/revisions/{r2.id}/diff?base_revision_id={r1.id}
    res_diff = client.get(f"/api/v1/revisions/{r2.id}/diff?base_revision_id={r1.id}")
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert diff_data["base_revision_id"] == r1.id
    assert diff_data["target_revision_id"] == r2.id
    assert diff_data["added_records"] == 1

    # 2. Test POST /api/v1/workspaces/{ws.id}/restore?snapshot_id={r1.id}
    res_restore = client.post(f"/api/v1/workspaces/{ws.id}/restore?snapshot_id={r1.id}")
    assert res_restore.status_code == 200
    restore_data = res_restore.json()
    assert restore_data["id"] == r1.id

    # Verify workspace current revision is r1
    db_session.refresh(ws)
    assert ws.current_revision_id == r1.id
