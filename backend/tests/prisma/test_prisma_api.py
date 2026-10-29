"""Integration tests for PRISMA 2020 reporting REST API endpoints."""
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import (
    SourceNamespace,
)
from app.db.models import (
    CorpusRevisionModel,
    CriteriaVersionModel,
    GroupMemberModel,
    PaperGroupModel,
    QueryVersionModel,
    RecordRevisionModel,
    ReviewEventModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)


@pytest.fixture
def prisma_api_setup(db_session: Session):
    ws = WorkspaceModel(id="ws-api-prisma", title="PRISMA REST API Review", created_by="reviewer-api")
    crit = CriteriaVersionModel(
        id="crit-api-prisma",
        workspace_id=ws.id,
        sequence=1,
        question="Clinical trial review question",
        pico_json=json.dumps({"p": "patients"}),
        criteria_json=json.dumps({"inclusion": ["human trials"], "exclusion": []}),
        content_hash="crit-hash-prisma",
    )
    qv = QueryVersionModel(
        id="qv-api-prisma",
        workspace_id=ws.id,
        sequence=1,
        ast_json="{}",
        sources_json=json.dumps(["PubMed"]),
        criteria_version_id=crit.id,
        content_hash="qvh-api-prisma",
    )
    db_session.add_all([ws, crit, qv])
    db_session.flush()

    corpus_rev = CorpusRevisionModel(
        id="crev-api-prisma",
        workspace_id=ws.id,
        criteria_version_id=crit.id,
        dedup_version="v1",
        state="published",
        fingerprint="fp-corpus-prisma-1",
    )
    db_session.add(corpus_rev)
    db_session.flush()

    se = SearchExecutionModel(
        id=str(uuid4()),
        query_version_id=qv.id,
        source=SourceNamespace.PUBMED.value,
        exact_query="trial search",
        hit_count=2,
        status="completed",
    )
    db_session.add(se)
    db_session.flush()

    sr1 = SourceRecordModel(
        id="sr-api-1",
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace="PubMed",
        external_id="30001",
    )
    sr2 = SourceRecordModel(
        id="sr-api-2",
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace="PubMed",
        external_id="30002",
    )
    db_session.add_all([sr1, sr2])
    db_session.flush()

    rr1 = RecordRevisionModel(id="rr-api-1", source_record_id=sr1.id, title="First Included Trial", content_hash="h-api-1", doi="10.1001/jama.001")
    rr2 = RecordRevisionModel(id="rr-api-2", source_record_id=sr2.id, title="Second Excluded Trial", content_hash="h-api-2")
    db_session.add_all([rr1, rr2])
    db_session.flush()

    grp1 = PaperGroupModel(
        id="grp-api-1",
        workspace_id=ws.id,
        membership_fingerprint="mfp-api-1",
        row_version=2,
    )
    grp2 = PaperGroupModel(
        id="grp-api-2",
        workspace_id=ws.id,
        membership_fingerprint="mfp-api-2",
        row_version=2,
    )
    db_session.add_all([grp1, grp2])
    db_session.flush()

    gm1 = GroupMemberModel(group_id=grp1.id, source_record_id=sr1.id)
    gm2 = GroupMemberModel(group_id=grp2.id, source_record_id=sr2.id)
    ev1 = ReviewEventModel(
        id="ev-api-1",
        workspace_id=ws.id,
        group_id=grp1.id,
        sequence=1,
        event_type="screen_decision",
        actor_id="reviewer",
        payload_json=json.dumps({"status": "include"}),
    )
    ev2 = ReviewEventModel(
        id="ev-api-2",
        workspace_id=ws.id,
        group_id=grp2.id,
        sequence=2,
        event_type="screen_decision",
        actor_id="reviewer",
        reason="Wrong comparator",
        payload_json=json.dumps({"status": "exclude"}),
    )
    db_session.add_all([gm1, gm2, ev1, ev2])
    db_session.commit()
    return ws


def test_get_prisma_flow_endpoint(client: TestClient, prisma_api_setup):
    ws = prisma_api_setup
    resp = client.get(f"/api/v1/workspaces/{ws.id}/prisma")
    assert resp.status_code == 200
    data = resp.json()

    assert data["workspace_id"] == ws.id
    assert data["is_live"] is True
    assert data["stages"]["identification"]["total_identified"] == 2
    assert data["stages"]["pre_screening"]["records_eligible_for_screening"] == 2
    assert data["stages"]["screening"]["records_screened"] == 2
    assert data["stages"]["screening"]["records_excluded"] == 1
    assert data["stages"]["included"]["studies_included"] == 1
    assert data["reconciliation"]["is_reconciled"] is True


def test_get_prisma_stage_records_endpoint(client: TestClient, prisma_api_setup):
    ws = prisma_api_setup
    resp = client.get(
        f"/api/v1/workspaces/{ws.id}/prisma/records",
        params={"stage": "included", "limit": 10, "offset": 0},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_count"] == 1
    assert len(data["records"]) == 1
    rec = data["records"][0]
    assert rec["title"] == "First Included Trial"
    assert rec["decision"] == "include"
    assert rec["doi"] == "10.1001/jama.001"


def test_export_prisma_csv_endpoint(client: TestClient, prisma_api_setup):
    ws = prisma_api_setup
    resp = client.get(f"/api/v1/workspaces/{ws.id}/prisma/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment; filename=" in resp.headers["content-disposition"]
    content = resp.text
    assert "PRISMA 2020 Flow Report" in content
    assert "Total records identified before screening" in content
    assert "Wrong comparator" in content


def test_snapshot_endpoints(client: TestClient, prisma_api_setup):
    ws = prisma_api_setup

    # 1. Create snapshot
    create_resp = client.post(
        f"/api/v1/workspaces/{ws.id}/prisma/snapshots",
        json={
            "name": "Audit Baseline 2026",
            "notes": "Verified dual review",
            "actor_id": "auditor_1",
        },
    )
    assert create_resp.status_code == 201
    snap = create_resp.json()
    snapshot_id = snap["snapshot_id"]
    assert snapshot_id is not None
    assert snap["name"] == "Audit Baseline 2026"

    # 2. List snapshots
    list_resp = client.get(f"/api/v1/workspaces/{ws.id}/prisma/snapshots")
    assert list_resp.status_code == 200
    summaries = list_resp.json()
    assert len(summaries) >= 1
    assert any(s["snapshot_id"] == snapshot_id for s in summaries)

    # 3. Get single snapshot
    get_resp = client.get(f"/api/v1/workspaces/{ws.id}/prisma/snapshots/{snapshot_id}")
    assert get_resp.status_code == 200
    snap_data = get_resp.json()
    assert snap_data["snapshot_id"] == snapshot_id
    assert snap_data["workspace_id"] == ws.id
