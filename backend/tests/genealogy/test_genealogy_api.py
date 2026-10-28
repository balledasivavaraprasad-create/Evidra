"""Integration tests for Duplicate Genealogy & Reconciliation REST API endpoints."""
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.contracts.enums import (
    DecisionEventType,
    DedupEdgeStatus,
    DuplicateConflictClassification,
    DuplicateMergeOperation,
    SourceNamespace,
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


@pytest.fixture
def genealogy_api_setup(db_session: Session):
    """Seed test workspace, criteria, and duplicate records for API testing."""
    ws = WorkspaceModel(id="ws-api-genealogy", title="API Genealogy Review", created_by="reviewer-api")
    crit = CriteriaVersionModel(
        id="crit-api-gen",
        workspace_id=ws.id,
        sequence=1,
        question="Clinical trial review question",
        pico_json=json.dumps({"p": "patients", "i": "intervention", "c": "comparator", "o": "outcome"}),
        criteria_json=json.dumps({"inclusion": ["human trials"], "exclusion": []}),
        content_hash="crit-hash-api-gen",
    )
    db_session.add_all([ws, crit])
    db_session.flush()

    corpus_rev = CorpusRevisionModel(
        id="crev-api-gen",
        workspace_id=ws.id,
        criteria_version_id=crit.id,
        dedup_version="v1",
        state="published",
        fingerprint="fp-corpus-api-1",
    )
    db_session.add(corpus_rev)
    db_session.flush()

    # Create 2 records
    title = "SGLT2 inhibitors and cardiovascular outcomes"
    doi = "10.1001/dc.2023.99"
    hash_val = hashlib.sha256(title.encode()).hexdigest()

    rec_a = SourceRecordModel(
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id="PMID-39000001",
    )
    db_session.add(rec_a)
    db_session.flush()

    rev_a = RecordRevisionModel(
        source_record_id=rec_a.id,
        title=title,
        authors_json=json.dumps(["Anderson P", "Brown T"]),
        year=2023,
        doi=doi,
        content_hash=hash_val,
    )
    db_session.add(rev_a)
    db_session.flush()

    rec_b = SourceRecordModel(
        workspace_id=ws.id,
        source=SourceNamespace.EUROPEPMC.value,
        source_namespace=SourceNamespace.EUROPEPMC.value,
        external_id="PMC-990002",
    )
    db_session.add(rec_b)
    db_session.flush()

    rev_b = RecordRevisionModel(
        source_record_id=rec_b.id,
        title=title + " [Clinical Report]",
        authors_json=json.dumps(["Anderson P.", "Brown T."]),
        year=2023,
        doi=doi,
        content_hash=hash_val,
    )
    db_session.add(rev_b)
    db_session.flush()

    grp = PaperGroupModel(
        id="grp-api-test-1",
        workspace_id=ws.id,
        membership_fingerprint=hash_val[:32],
        row_version=1,
    )
    db_session.add(grp)
    db_session.flush()

    mem_a = GroupMemberModel(group_id=grp.id, source_record_id=rec_a.id)
    mem_b = GroupMemberModel(group_id=grp.id, source_record_id=rec_b.id)
    db_session.add_all([mem_a, mem_b])

    edge = DedupEdgeModel(
        id=str(uuid4()),
        workspace_id=ws.id,
        record_id_a=rec_a.id,
        record_id_b=rec_b.id,
        score=1.0,
        method_version="exact_doi:v1.0",
        status=DedupEdgeStatus.CONFIRMED.value,
        evidence_json=json.dumps({"exact_doi": doi, "score": 1.0}),
    )
    db_session.add(edge)

    merge_ev = DuplicateMergeEventModel(
        id=str(uuid4()),
        workspace_id=ws.id,
        group_id=grp.id,
        canonical_record_id=rec_a.id,
        operation=DuplicateMergeOperation.MERGE.value,
        affected_source_ids_json=json.dumps([rec_a.id, rec_b.id]),
        match_evidence_json=json.dumps({"exact_doi": doi}),
        pre_operation_state_json=json.dumps({"groups": [{"group_id": "grp-pre-1", "members": [rec_a.id]}]}),
        actor_id="system",
        reason="Automated DOI merge pass",
        status="active",
    )
    db_session.add(merge_ev)

    ev_a = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=ws.id,
        sequence=1,
        event_type=DecisionEventType.SCREEN_DECISION.value,
        group_id=grp.id,
        actor_id="rev-user-1",
        reason="RCT meets criteria",
        payload_json=json.dumps({"status": "include", "source_record_id": rec_a.id, "actor_type": "human"}),
    )
    db_session.add(ev_a)
    db_session.flush()

    ev_b = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=ws.id,
        sequence=2,
        event_type=DecisionEventType.SCREEN_DECISION.value,
        group_id=grp.id,
        actor_id="ai-bot",
        reason="Excluded by automated pass",
        payload_json=json.dumps({"status": "exclude", "source_record_id": rec_b.id, "actor_type": "automated"}),
    )
    db_session.add(ev_b)
    db_session.flush()

    conflict = ReviewConflictModel(
        id=str(uuid4()),
        corpus_revision_id=corpus_rev.id,
        group_id=grp.id,
        kind=DuplicateConflictClassification.DECISION_DIVERGENCE.value,
        conflicting_event_ids_json=json.dumps([ev_a.id, ev_b.id]),
    )
    db_session.add(conflict)

    db_session.commit()
    return ws, grp, rec_a, rec_b, merge_ev


def test_api_workspace_duplicates_overview(client: TestClient, genealogy_api_setup):
    """Test GET /api/v1/workspaces/{workspace_id}/duplicates endpoint."""
    ws, grp, _, _, _ = genealogy_api_setup
    resp = client.get(f"/api/v1/workspaces/{ws.id}/duplicates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == ws.id
    assert data["total_duplicate_groups"] == 1
    assert data["groups_with_conflicts"] == 1
    assert len(data["groups"]) == 1
    assert data["groups"][0]["group_id"] == grp.id
    assert data["groups"][0]["has_unresolved_conflict"] is True


def test_api_group_genealogy_details(client: TestClient, genealogy_api_setup):
    """Test GET /api/v1/workspaces/{workspace_id}/groups/{group_id}/genealogy endpoint."""
    ws, grp, rec_a, _, _ = genealogy_api_setup
    resp = client.get(f"/api/v1/workspaces/{ws.id}/groups/{grp.id}/genealogy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_id"] == grp.id
    assert data["canonical_record_id"] == rec_a.id
    assert len(data["members"]) == 2
    assert len(data["active_conflicts"]) == 1
    assert len(data["pairwise_signals"]) >= 1
    assert len(data["field_provenance"]) > 0


def test_api_reconcile_conflict(client: TestClient, genealogy_api_setup):
    """Test POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/reconcile endpoint."""
    ws, grp, _, _, _ = genealogy_api_setup
    payload = {
        "chosen_decision": "include",
        "reason": "Expert methodology review confirmed clinical trial eligibility",
        "actor_id": "api-reviewer",
        "apply_to_all_members": True,
        "expected_version": 1,
    }
    resp = client.post(f"/api/v1/workspaces/{ws.id}/groups/{grp.id}/reconcile", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["effective_decision"] == "include"
    assert len(data["active_conflicts"]) == 0
    assert data["row_version"] == 2


def test_api_reconcile_conflict_concurrency_error(client: TestClient, genealogy_api_setup):
    """Test optimistic concurrency error (HTTP 409) on stale expected_version."""
    ws, grp, _, _, _ = genealogy_api_setup
    payload = {
        "chosen_decision": "include",
        "reason": "Test stale version error",
        "actor_id": "api-reviewer",
        "apply_to_all_members": True,
        "expected_version": 999,  # Wrong version
    }
    resp = client.post(f"/api/v1/workspaces/{ws.id}/groups/{grp.id}/reconcile", json=payload)
    assert resp.status_code == 409
    err_msg = (resp.json().get("detail") or resp.json().get("message", "")).lower()
    assert "version" in err_msg or "conflict" in err_msg


def test_api_split_duplicate_group(client: TestClient, genealogy_api_setup):
    """Test POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/split endpoint."""
    ws, grp, _, rec_b, _ = genealogy_api_setup
    payload = {
        "source_record_ids_to_split": [rec_b.id],
        "reason": "Distinct clinical trial endpoints between publications",
        "mark_as_cannot_link": True,
        "actor_id": "split-tester",
        "expected_version": 1,
    }
    resp = client.post(f"/api/v1/workspaces/{ws.id}/groups/{grp.id}/split", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["members"]) == 1
    assert data["row_version"] == 2


def test_api_reverse_merge_event(client: TestClient, genealogy_api_setup):
    """Test POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/reverse-merge endpoint."""
    ws, grp, _, _, merge_ev = genealogy_api_setup
    payload = {
        "merge_event_id": merge_ev.id,
        "reason": "Safe reversal of automated duplicate group merge",
        "actor_id": "reversal-tester",
        "expected_version": 1,
    }
    resp = client.post(f"/api/v1/workspaces/{ws.id}/groups/{grp.id}/reverse-merge", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["members"]) == 1
