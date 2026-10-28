"""API and end-to-end integration tests for Evidence Passport endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import (
    EvidenceClaimType,
    EvidenceSemanticAssessment,
    EvidenceValidationStatus,
)
from app.db.models import (
    EvidencePassportModel,
    GroupMemberModel,
    PaperGroupModel,
    RecordRevisionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.pico.validator import compute_text_hash


@pytest.fixture
def api_test_data(db_session: Session):
    ws = WorkspaceModel(title="API Test Review", created_by="tester")
    db_session.add(ws)
    db_session.commit()

    src = SourceRecordModel(
        workspace_id=ws.id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="PMID999",
    )
    db_session.add(src)
    db_session.commit()

    abstract = (
        "Randomized controlled trial of liraglutide 3.0mg versus lifestyle intervention in obese adults. "
        "Mean weight loss was 8.4kg in the liraglutide arm versus 2.8kg with lifestyle alone. "
        "Nausea was the most common adverse event."
    )
    chash = compute_text_hash(abstract)

    rec = RecordRevisionModel(
        source_record_id=src.id,
        content_hash=chash,
        title="Liraglutide Weight Loss Trial",
        abstract_text=abstract,
    )
    db_session.add(rec)
    db_session.commit()

    grp = PaperGroupModel(
        workspace_id=ws.id,
        membership_fingerprint=f"mfp-{rec.id}",
    )
    db_session.add(grp)
    db_session.commit()

    db_session.add(GroupMemberModel(group_id=grp.id, source_record_id=src.id))
    db_session.commit()

    # Seed an evidence passport item
    quote = "liraglutide 3.0mg"
    s_cp = abstract.find(quote)
    e_cp = s_cp + len(quote)

    item = EvidencePassportModel(
        workspace_id=ws.id,
        paper_group_id=grp.id,
        record_revision_id=rec.id,
        claim_type=EvidenceClaimType.INTERVENTION.value,
        claim_value="Liraglutide 3.0mg",
        original_claim_value="Liraglutide 3.0mg",
        source_field="abstract",
        supporting_quote=quote,
        start_cp=s_cp,
        end_cp=e_cp,
        source_fingerprint=chash,
        provenance="rule:v1.0",
        validation_status=EvidenceValidationStatus.VERIFIED.value,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
    )
    db_session.add(item)
    db_session.commit()

    return {
        "workspace": ws,
        "group": grp,
        "record_revision": rec,
        "evidence_item": item,
        "abstract": abstract,
    }


def test_get_group_evidence_passport_api(client: TestClient, api_test_data):
    ws_id = api_test_data["workspace"].id
    grp_id = api_test_data["group"].id

    resp = client.get(f"/api/v1/workspaces/{ws_id}/groups/{grp_id}/evidence")
    assert resp.status_code == 200
    data = resp.json()

    assert data["workspace_id"] == ws_id
    assert data["group_id"] == grp_id
    assert len(data["items"]) >= 1
    assert data["summary"]["verified_quotes_count"] >= 1
    assert data["items"][0]["claim_value"] == "Liraglutide 3.0mg"


def test_correct_evidence_item_api(client: TestClient, api_test_data):
    ws_id = api_test_data["workspace"].id
    item_id = api_test_data["evidence_item"].id

    payload = {
        "claim_value": "High-dose liraglutide (3.0mg daily)",
        "supporting_quote": "liraglutide 3.0mg versus lifestyle intervention",
        "semantic_assessment": "supports",
        "reason": "Clarified daily dosing regimen",
        "actor_id": "dr_lead",
    }

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/evidence/{item_id}/correct",
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["claim_value"] == "High-dose liraglutide (3.0mg daily)"
    assert data["original_claim_value"] == "Liraglutide 3.0mg"
    assert data["provenance"] == "human_corrected"
    assert data["assessed_by"] == "human:dr_lead"
    assert data["validation_status"] == "verified"


def test_create_manual_evidence_item_api(client: TestClient, api_test_data):
    ws_id = api_test_data["workspace"].id
    grp_id = api_test_data["group"].id
    rec_id = api_test_data["record_revision"].id

    payload = {
        "record_revision_id": rec_id,
        "claim_type": "outcome",
        "claim_value": "Mean weight loss reduction of 8.4kg",
        "source_field": "abstract",
        "supporting_quote": "Mean weight loss was 8.4kg in the liraglutide arm",
        "semantic_assessment": "supports",
        "actor_id": "reviewer_2",
    }

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/groups/{grp_id}/evidence",
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["claim_type"] == "outcome"
    assert data["validation_status"] == "verified"
    assert data["start_cp"] is not None
    assert data["end_cp"] is not None


def test_revalidate_paper_evidence_api(client: TestClient, api_test_data):
    ws_id = api_test_data["workspace"].id
    grp_id = api_test_data["group"].id

    resp = client.post(f"/api/v1/workspaces/{ws_id}/groups/{grp_id}/evidence/revalidate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items_revalidated"] >= 1
    assert data["verified_count"] >= 1


def test_get_evidence_summary_api(client: TestClient, api_test_data):
    ws_id = api_test_data["workspace"].id

    resp = client.get(f"/api/v1/workspaces/{ws_id}/evidence/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["workspace_id"] == ws_id
    assert data["total_papers"] >= 1
    assert data["papers_with_verified_evidence"] >= 1
    assert data["verified_claims"] >= 1


def test_export_evidence_csv_api(client: TestClient, api_test_data):
    ws_id = api_test_data["workspace"].id

    resp = client.get(f"/api/v1/workspaces/{ws_id}/evidence/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "evidence_id,paper_group_id" in resp.text
    assert "Liraglutide 3.0mg" in resp.text


def test_cross_workspace_evidence_access_denied(client: TestClient, api_test_data):
    item_id = api_test_data["evidence_item"].id
    other_ws_id = "ws-other-unauthorized"

    payload = {
        "claim_value": "Hacked Claim",
        "reason": "Exploit attempt",
    }

    resp = client.post(
        f"/api/v1/workspaces/{other_ws_id}/evidence/{item_id}/correct",
        json=payload,
    )
    assert resp.status_code == 404
