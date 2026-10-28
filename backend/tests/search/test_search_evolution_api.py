"""Integration and REST API tests for Search Evolution Time Machine."""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import SourceNamespace
from app.db.models import (
    CriteriaVersionModel,
    QueryMembershipModel,
    QueryVersionModel,
    RecordRevisionModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)


@pytest.fixture
def api_test_data(db_session: Session):
    """Seed test workspace, criteria, and query versions with search executions."""
    ws = WorkspaceModel(created_by="test-researcher", id="ws-api-test", title="API Search Evolution Review")
    crit = CriteriaVersionModel(
        id="crit-api-1",
        workspace_id=ws.id,
        sequence=1,
        question="Clinical outcomes of cell therapy",
        pico_json=json.dumps({"p": "patients", "i": "cell therapy", "c": "placebo", "o": "remission"}),
        criteria_json=json.dumps({"inclusion": ["RCTs"], "exclusion": []}),
        content_hash="crit-hash-api",
    )
    db_session.add_all([ws, crit])
    db_session.flush()

    # Create source record and revision
    rec1 = SourceRecordModel(
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id="PMID_API_1",
    )
    db_session.add(rec1)
    db_session.flush()

    rev1 = RecordRevisionModel(
        source_record_id=rec1.id,
        content_hash="hash-rev-1",
        title="CAR-T cell therapy in lymphoma",
        abstract_text="Phase 2 multicenter study",
        authors_json=json.dumps(["Doe J", "Smith A"]),
        year=2023,
        journal="Blood",
        pmid="PMID_API_1",
    )
    db_session.add(rev1)
    db_session.flush()

    # Query Version 1
    qv1 = QueryVersionModel(
        workspace_id=ws.id,
        sequence=1,
        ast_json=json.dumps({"term": "CAR-T"}, sort_keys=True),
        sources_json=json.dumps([SourceNamespace.PUBMED.value]),
        criteria_version_id=crit.id,
        content_hash="qv-hash-1",
        change_description="Initial strategy",
    )
    db_session.add(qv1)
    db_session.flush()

    ex1 = SearchExecutionModel(
        query_version_id=qv1.id,
        source=SourceNamespace.PUBMED.value,
        exact_query="CAR-T",
        hit_count=1,
        status="succeeded",
    )
    db_session.add(ex1)
    db_session.flush()

    m1 = QueryMembershipModel(
        search_execution_id=ex1.id,
        source_record_id=rec1.id,
        record_revision_id=rev1.id,
    )
    db_session.add(m1)

    # Query Version 2: Add MeSH expansion
    rec2 = SourceRecordModel(
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id="PMID_API_2",
    )
    db_session.add(rec2)
    db_session.flush()

    rev2 = RecordRevisionModel(
        source_record_id=rec2.id,
        content_hash="hash-rev-2",
        title="Bispecific T-cell engager in lymphoma",
        abstract_text="Comparative cohort study",
        authors_json=json.dumps(["Johnson B"]),
        year=2024,
        journal="Lancet Oncology",
        pmid="PMID_API_2",
    )
    db_session.add(rev2)
    db_session.flush()

    qv2 = QueryVersionModel(
        workspace_id=ws.id,
        sequence=2,
        parent_id=qv1.id,
        ast_json=json.dumps({"term": "CAR-T OR BiTE"}, sort_keys=True),
        sources_json=json.dumps([SourceNamespace.PUBMED.value]),
        criteria_version_id=crit.id,
        content_hash="qv-hash-2",
        change_description="Added BiTE therapies",
    )
    db_session.add(qv2)
    db_session.flush()

    ex2 = SearchExecutionModel(
        query_version_id=qv2.id,
        source=SourceNamespace.PUBMED.value,
        exact_query="CAR-T OR BiTE",
        hit_count=2,
        status="succeeded",
    )
    db_session.add(ex2)
    db_session.flush()

    m2_1 = QueryMembershipModel(
        search_execution_id=ex2.id,
        source_record_id=rec1.id,
        record_revision_id=rev1.id,
    )
    m2_2 = QueryMembershipModel(
        search_execution_id=ex2.id,
        source_record_id=rec2.id,
        record_revision_id=rev2.id,
    )
    db_session.add_all([m2_1, m2_2])
    db_session.commit()

    return ws, qv1, qv2


def test_list_search_versions_endpoint(client: TestClient, api_test_data):
    """Test GET /api/v1/workspaces/{workspace_id}/search-versions returns ordered timeline."""
    ws, qv1, qv2 = api_test_data

    resp = client.get(f"/api/v1/workspaces/{ws.id}/search-versions")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    # Ordered descending by sequence
    assert data[0]["sequence"] == 2
    assert data[0]["total_records"] == 2
    assert data[0]["new_records_count"] == 1
    assert data[0]["repeated_records_count"] == 1
    assert data[0]["change_description"] == "Added BiTE therapies"

    assert data[1]["sequence"] == 1
    assert data[1]["total_records"] == 1
    assert data[1]["new_records_count"] == 1


def test_get_search_version_detail_endpoint(client: TestClient, api_test_data):
    """Test GET /api/v1/workspaces/{workspace_id}/search-versions/{version_id}."""
    ws, qv1, _ = api_test_data

    resp = client.get(f"/api/v1/workspaces/{ws.id}/search-versions/{qv1.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == qv1.id
    assert data["sequence"] == 1
    assert len(data["executions"]) == 1
    assert data["executions"][0]["exact_query"] == "CAR-T"


def test_search_evolution_diff_endpoint(client: TestClient, api_test_data):
    """Test GET /api/v1/workspaces/{workspace_id}/search-versions/{target_version_id}/diff."""
    ws, qv1, qv2 = api_test_data

    # Diff against default predecessor (which is qv1)
    resp = client.get(f"/api/v1/workspaces/{ws.id}/search-versions/{qv2.id}/diff")
    assert resp.status_code == 200
    data = resp.json()

    summary = data["summary"]
    assert summary["base_sequence"] == 1
    assert summary["target_sequence"] == 2
    assert summary["total_base_records"] == 1
    assert summary["total_target_records"] == 2
    assert summary["newly_discovered_count"] == 1
    assert summary["repeated_count"] == 1
    assert summary["missing_from_newer_count"] == 0

    records = data["records"]
    assert len(records) == 2

    # Check newly discovered
    new_rec = next(r for r in records if r["category"] == "newly_discovered")
    assert new_rec["external_id"] == "PMID_API_2"
    assert new_rec["title"] == "Bispecific T-cell engager in lymphoma"

    # Check repeated
    rep_rec = next(r for r in records if r["category"] == "repeated")
    assert rep_rec["external_id"] == "PMID_API_1"


def test_restore_search_version_endpoint(client: TestClient, api_test_data):
    """Test POST /api/v1/workspaces/{workspace_id}/search-versions/{version_id}/restore."""
    ws, qv1, _ = api_test_data

    payload = {
        "reason": "Reverting back to simple CAR-T focus",
        "actor_id": "lead-reviewer",
    }
    resp = client.post(
        f"/api/v1/workspaces/{ws.id}/search-versions/{qv1.id}/restore",
        json=payload,
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["restored_from_version_id"] == qv1.id
    restored_q = data["restored_query"]
    assert restored_q["sequence"] == 3
    assert restored_q["parent_id"] == qv1.id
    assert restored_q["restored_from_version_id"] == qv1.id
    assert "Reverting back to simple CAR-T focus" in restored_q["change_description"]


def test_workspace_isolation_guards(client: TestClient, api_test_data):
    """Test that search evolution endpoints reject requests with wrong workspace_id."""
    ws, qv1, _ = api_test_data

    # Nonexistent workspace
    resp = client.get("/api/v1/workspaces/ws-unknown/search-versions")
    assert resp.status_code == 404

    # Version belonging to ws but requested under another workspace
    resp = client.get(f"/api/v1/workspaces/ws-other/search-versions/{qv1.id}")
    assert resp.status_code == 404
