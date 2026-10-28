"""Integration and REST API tests for Devil's Advocate Reviewer."""
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    ChallengeDisposition,
    ChallengeRecommendation,
    DecisionEventType,
    EffectiveDecisionState,
    SourceNamespace,
)
from app.db.models import (
    CriteriaVersionModel,
    GroupMemberModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)


@pytest.fixture
def api_devils_fixture(db_session: Session):
    """Seed test workspace and study group with excluded status."""
    ws = WorkspaceModel(created_by="api-screener", id="ws-devils-api", title="Devils Advocate API Review")
    crit = CriteriaVersionModel(
        id="crit-devils-api",
        workspace_id=ws.id,
        sequence=1,
        question="Clinical trial review question",
        pico_json=json.dumps({"p": "patients", "i": "drug", "c": "control", "o": "remission"}),
        criteria_json=json.dumps({"inclusion": ["human trials"], "exclusion": []}),
        content_hash="crit-devils-api-hash",
    )
    db_session.add_all([ws, crit])
    db_session.flush()

    abstract = (
        "Phase 3 clinical trial in 150 patients with relapsed leukemia. "
        "Intervention group received immunotherapy compared to standard control chemotherapy. "
        "Primary outcome was complete remission rate."
    )
    content_hash = hashlib.sha256(abstract.encode()).hexdigest()

    rec = SourceRecordModel(
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id="PMID_DEVILS_999",
    )
    db_session.add(rec)
    db_session.flush()

    rev = RecordRevisionModel(
        source_record_id=rec.id,
        content_hash=content_hash,
        title="Phase 3 Immunotherapy in Leukemia",
        abstract_text=abstract,
        authors_json=json.dumps(["Dr. Clark", "Dr. Vance"]),
        year=2024,
        journal="New England Journal of Medicine",
        pmid="PMID_DEVILS_999",
    )
    db_session.add(rev)
    db_session.flush()

    group = PaperGroupModel(
        workspace_id=ws.id,
        membership_fingerprint="fp-devils-999",
    )
    db_session.add(group)
    db_session.flush()

    member = GroupMemberModel(
        group_id=group.id,
        source_record_id=rec.id,
    )
    db_session.add(member)

    seq = (
        db_session.query(func.max(ReviewEventModel.sequence))
        .filter_by(workspace_id=ws.id)
        .scalar()
        or 0
    ) + 1

    event = ReviewEventModel(
        workspace_id=ws.id,
        group_id=group.id,
        sequence=seq,
        actor_id="screener",
        event_type=DecisionEventType.SCREEN_DECISION.value,
        payload_json=json.dumps({
            "status": "exclude",
            "decision": "exclude",
            "reason": "Single arm without control",
        }),
        reason="Single arm without control",
    )
    db_session.add(event)
    db_session.commit()

    return ws, group


def test_get_devils_advocate_challenge_endpoint(client: TestClient, api_devils_fixture):
    """Test GET /api/v1/workspaces/{ws_id}/groups/{grp_id}/devils-advocate."""
    ws, group = api_devils_fixture

    resp = client.get(f"/api/v1/workspaces/{ws.id}/groups/{group.id}/devils-advocate")
    assert resp.status_code == 200
    data = resp.json()

    assert data["workspace_id"] == ws.id
    assert data["group_id"] == group.id
    assert data["proposed_decision"] == "exclude"
    assert data["recommendation"] == "reconsider_exclusion"
    assert data["vulnerability_score"] >= 0.60
    assert data["disposition"] == "pending"
    assert len(data["counter_arguments"]) >= 1


def test_generate_fresh_challenge_endpoint(client: TestClient, api_devils_fixture):
    """Test POST /api/v1/workspaces/{ws_id}/groups/{grp_id}/devils-advocate/generate."""
    ws, group = api_devils_fixture

    resp = client.post(
        f"/api/v1/workspaces/{ws.id}/groups/{group.id}/devils-advocate/generate",
        json={
            "force_refresh": True,
            "proposed_decision": "exclude",
            "exclusion_reason": "No control group",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["original_exclusion_reason"] == "No control group"
    assert data["recommendation"] == "reconsider_exclusion"


def test_record_challenge_disposition_concede_endpoint(client: TestClient, api_devils_fixture):
    """Test POST /api/v1/workspaces/{ws_id}/groups/{grp_id}/devils-advocate/disposition to concede."""
    ws, group = api_devils_fixture

    resp = client.post(
        f"/api/v1/workspaces/{ws.id}/groups/{group.id}/devils-advocate/disposition",
        json={
            "disposition": "conceded",
            "notes": "Standard control chemotherapy confirmed in abstract.",
            "actor_id": "lead-screener",
            "conceded_decision": "include",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["disposition"] == "conceded"
    assert data["disposition_by"] == "lead-screener"
    assert "Standard control chemotherapy" in data["disposition_notes"]


def test_workspace_devils_advocate_dashboard_endpoint(client: TestClient, api_devils_fixture):
    """Test GET /api/v1/workspaces/{ws_id}/devils-advocate."""
    ws, group = api_devils_fixture

    # Trigger challenge creation
    client.get(f"/api/v1/workspaces/{ws.id}/groups/{group.id}/devils-advocate")

    resp = client.get(f"/api/v1/workspaces/{ws.id}/devils-advocate")
    assert resp.status_code == 200
    data = resp.json()

    assert data["workspace_id"] == ws.id
    assert data["total_challenged"] >= 1
    assert data["pending_challenges"] >= 1
    assert len(data["challenges"]) >= 1
    assert data["challenges"][0]["group_id"] == group.id
