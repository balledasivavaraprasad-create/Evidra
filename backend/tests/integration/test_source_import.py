"""Integration tests for the question -> query -> search -> import -> persistence pipeline."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    QueryMembershipModel,
    RecordRevisionModel,
    SourceRecordModel,
)
from app.worker import process_single_job


def test_full_source_import_pipeline(client: TestClient, db_session: Session):
    """End-to-end integration: workspace -> criteria -> query -> count -> import -> worker persistence."""
    # 1. Create Workspace
    ws_resp = client.post("/api/v1/workspaces", json={"title": "Metformin Review", "description": "Type 2 diabetes HbA1c"})
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    # 2. Save Criteria Version
    crit_payload = {
        "question": "In adults with type 2 diabetes, how does metformin affect HbA1c?",
        "pico_description": {
            "population": "Adults with type 2 diabetes",
            "intervention": "Metformin",
            "comparator": "Placebo or active comparator",
            "outcome": "Change in HbA1c",
        },
        "criteria": [
            {
                "id": "crit_adults",
                "name": "Adult human participants",
                "category": "population",
                "is_inclusion": True,
                "rationale": "Focus on adult diabetes",
            },
            {
                "id": "crit_animal_exclude",
                "name": "Animal studies",
                "category": "species",
                "is_inclusion": False,
                "rationale": "Exclude rodent and in vitro studies",
            },
        ],
    }
    crit_resp = client.post(f"/api/v1/workspaces/{ws_id}/criteria", json=crit_payload)
    assert crit_resp.status_code == 201
    crit_id = crit_resp.json()["id"]
    assert crit_resp.json()["sequence"] == 1

    # 3. Save Query Version
    query_payload = {
        "ast": {
            "operator": "AND",
            "children": [
                {"term": "metformin"},
                {"term": "type 2 diabetes"},
            ],
        },
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "sources": ["pubmed", "europepmc"],
        "criteria_version_id": crit_id,
    }
    query_resp = client.post(f"/api/v1/workspaces/{ws_id}/queries", json=query_payload)
    assert query_resp.status_code == 201
    q_id = query_resp.json()["id"]
    assert query_resp.json()["sequence"] == 1

    # 4. Execute Search Count (PubMed)
    search_pubmed_resp = client.post(
        f"/api/v1/queries/{q_id}/searches",
        json={"source": "pubmed", "synonym_expansion": False, "cap": 50},
    )
    assert search_pubmed_resp.status_code == 202
    pubmed_exec_id = search_pubmed_resp.json()["id"]
    assert search_pubmed_resp.json()["hit_count"] > 0

    # 5. Execute Search Count (Europe PMC)
    search_epmc_resp = client.post(
        f"/api/v1/queries/{q_id}/searches",
        json={"source": "europepmc", "synonym_expansion": True, "cap": 50},
    )
    assert search_epmc_resp.status_code == 202
    epmc_exec_id = search_epmc_resp.json()["id"]
    assert search_epmc_resp.json()["hit_count"] > 0

    # 6. Trigger Approved Record Import Job
    import_payload = {
        "search_execution_ids": [pubmed_exec_id, epmc_exec_id],
        "cap": 20,
        "idempotency_key": "import-batch-20261027-test1",
    }
    import_resp = client.post(f"/api/v1/workspaces/{ws_id}/imports", json=import_payload)
    assert import_resp.status_code == 202
    job_id = import_resp.json()["id"]
    assert import_resp.json()["state"] == "queued"

    # 7. Execute Job via Worker
    process_single_job(job_id)

    # 8. Verify Job Status via API
    job_status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert job_status_resp.status_code == 200
    job_data = job_status_resp.json()
    assert job_data["state"] == "succeeded"
    assert job_data["progress"] == 1.0
    assert job_data["processed_items"] > 0

    # 9. Verify Database Persistence
    stored_sources = db_session.query(SourceRecordModel).filter_by(workspace_id=ws_id).all()
    assert len(stored_sources) > 0

    stored_revisions = db_session.query(RecordRevisionModel).all()
    assert len(stored_revisions) >= len(stored_sources)

    stored_memberships = db_session.query(QueryMembershipModel).all()
    assert len(stored_memberships) > 0


def test_import_job_idempotency_and_conflict(client: TestClient, db_session: Session):
    """Verify repeated requests with identical key return same job; changed payload raises conflict."""
    # Setup workspace, criteria, and query
    ws = client.post("/api/v1/workspaces", json={"title": "Idempotency WS"}).json()
    ws_id = ws["id"]
    crit = client.post(
        f"/api/v1/workspaces/{ws_id}/criteria",
        json={"question": "Q?", "pico_description": {}, "criteria": [{"id": "c1", "name": "C1", "category": "pop", "is_inclusion": True, "rationale": "r"}]},
    ).json()
    q = client.post(
        f"/api/v1/workspaces/{ws_id}/queries",
        json={"ast": {"term": "metformin"}, "sources": ["pubmed"], "criteria_version_id": crit["id"]},
    ).json()
    search = client.post(f"/api/v1/queries/{q['id']}/searches", json={"source": "pubmed"}).json()

    key = "unique-key-xyz-123"
    payload1 = {"search_execution_ids": [search["id"]], "cap": 10, "idempotency_key": key}

    # Initial submission
    res1 = client.post(f"/api/v1/workspaces/{ws_id}/imports", json=payload1)
    assert res1.status_code == 202
    job1_id = res1.json()["id"]

    # Re-submission with identical parameters returns same job
    res2 = client.post(f"/api/v1/workspaces/{ws_id}/imports", json=payload1)
    assert res2.status_code == 202
    assert res2.json()["id"] == job1_id

    # Submission with same key but changed parameters raises 409 Conflict
    payload_conflict = {"search_execution_ids": [search["id"]], "cap": 50, "idempotency_key": key}
    res3 = client.post(f"/api/v1/workspaces/{ws_id}/imports", json=payload_conflict)
    assert res3.status_code == 409
    assert res3.json()["code"] == "STALE_VERSION_CONFLICT"


def test_cross_workspace_import_authorization(client: TestClient):
    """Users cannot approve or import search executions from another workspace."""
    ws_a = client.post("/api/v1/workspaces", json={"title": "Workspace A"}).json()["id"]
    ws_b = client.post("/api/v1/workspaces", json={"title": "Workspace B"}).json()["id"]

    crit_b = client.post(
        f"/api/v1/workspaces/{ws_b}/criteria",
        json={"question": "Q?", "pico_description": {}, "criteria": [{"id": "c", "name": "C", "category": "p", "is_inclusion": True, "rationale": "r"}]},
    ).json()["id"]
    q_b = client.post(
        f"/api/v1/workspaces/{ws_b}/queries",
        json={"ast": {"term": "test"}, "sources": ["pubmed"], "criteria_version_id": crit_b},
    ).json()["id"]
    search_b = client.post(f"/api/v1/queries/{q_b}/searches", json={"source": "pubmed"}).json()["id"]

    # Workspace A attempts to import search belonging to Workspace B -> 403 Forbidden
    payload = {"search_execution_ids": [search_b], "cap": 10, "idempotency_key": "key-cross-ws"}
    res = client.post(f"/api/v1/workspaces/{ws_a}/imports", json=payload)
    assert res.status_code == 403


def test_job_cancellation(client: TestClient, db_session: Session):
    """Verify job can be cancelled prior to or during processing."""
    ws_id = client.post("/api/v1/workspaces", json={"title": "Cancel WS"}).json()["id"]
    crit_id = client.post(
        f"/api/v1/workspaces/{ws_id}/criteria",
        json={"question": "Q?", "pico_description": {}, "criteria": [{"id": "c", "name": "C", "category": "p", "is_inclusion": True, "rationale": "r"}]},
    ).json()["id"]
    q_id = client.post(
        f"/api/v1/workspaces/{ws_id}/queries",
        json={"ast": {"term": "test"}, "sources": ["pubmed"], "criteria_version_id": crit_id},
    ).json()["id"]
    search_id = client.post(f"/api/v1/queries/{q_id}/searches", json={"source": "pubmed"}).json()["id"]

    job = client.post(
        f"/api/v1/workspaces/{ws_id}/imports",
        json={"search_execution_ids": [search_id], "cap": 10, "idempotency_key": "cancel-key-1"},
    ).json()

    # Cancel job
    cancel_res = client.post(f"/api/v1/jobs/{job['id']}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["state"] == "cancelled"
