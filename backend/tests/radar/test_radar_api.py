"""Integration and REST API tests for Missing-Evidence Radar."""
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    EffectiveDecisionState,
    RadarEvidenceStatus,
    RadarHumanReviewStatus,
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
def api_radar_fixture(db_session: Session):
    """Seed test workspace and study group with abstract text."""
    ws = WorkspaceModel(created_by="api-researcher", id="ws-radar-api", title="Radar API Review")
    crit = CriteriaVersionModel(
        id="crit-radar-api",
        workspace_id=ws.id,
        sequence=1,
        question="Clinical radar question",
        pico_json=json.dumps({"p": "patients", "i": "drug", "c": "control", "o": "remission"}),
        criteria_json=json.dumps({"inclusion": ["human trials"], "exclusion": []}),
        content_hash="crit-radar-api-hash",
    )
    db_session.add_all([ws, crit])
    db_session.flush()

    abstract = (
        "Phase 3 clinical trial in 120 patients with acute leukemia. "
        "Intervention group received targeted therapy. "
        "Comparator group received standard chemotherapy. "
        "Primary outcome was complete remission rate."
    )
    content_hash = hashlib.sha256(abstract.encode()).hexdigest()

    rec = SourceRecordModel(
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id="PMID_RADAR_999",
    )
    db_session.add(rec)
    db_session.flush()

    rev = RecordRevisionModel(
        source_record_id=rec.id,
        content_hash=content_hash,
        title="Phase 3 Targeted Therapy in Acute Leukemia",
        abstract_text=abstract,
        authors_json=json.dumps(["Dr. Smith", "Dr. Jones"]),
        year=2024,
        journal="Journal of Hematology",
        pmid="PMID_RADAR_999",
    )
    db_session.add(rev)
    db_session.flush()

    group = PaperGroupModel(
        workspace_id=ws.id,
        membership_fingerprint="fp-radar-999",
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
        payload_json=json.dumps({"status": "include", "decision": "include", "notes": "Criteria fully satisfied"}),
    )
    db_session.add(event)
    db_session.commit()

    return ws, group


def test_get_article_radar_endpoint(client: TestClient, api_radar_fixture):
    """Test GET /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar."""
    ws, group = api_radar_fixture

    resp = client.get(f"/api/v1/workspaces/{ws.id}/groups/{group.id}/pico-radar")
    assert resp.status_code == 200
    data = resp.json()

    assert data["workspace_id"] == ws.id
    assert data["group_id"] == group.id
    assert data["effective_decision"] == "include"
    assert data["has_source_text"] is True

    pico = data["pico"]
    assert "population" in pico
    assert "intervention" in pico
    assert "comparator" in pico
    assert "outcome" in pico
    assert pico["population"]["field_label"] == "Population"


def test_get_review_level_radar_endpoint(client: TestClient, api_radar_fixture):
    """Test GET /api/v1/workspaces/{workspace_id}/pico-radar."""
    ws, _ = api_radar_fixture

    resp = client.get(f"/api/v1/workspaces/{ws.id}/pico-radar")
    assert resp.status_code == 200
    data = resp.json()

    assert data["workspace_id"] == ws.id
    assert data["total_articles"] == 1
    assert data["articles_with_source_text"] == 1
    assert len(data["rows"]) == 1
    assert data["rows"][0]["title"] == "Phase 3 Targeted Therapy in Acute Leukemia"


def test_confirm_pico_radar_field_endpoint(client: TestClient, api_radar_fixture):
    """Test POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field}/confirm."""
    ws, group = api_radar_fixture

    resp = client.post(
        f"/api/v1/workspaces/{ws.id}/groups/{group.id}/pico-radar/population/confirm",
        json={"actor_id": "dr-reviewer", "notes": "Adult leukemia population verified"},
    )
    assert resp.status_code == 200
    data = resp.json()

    pop = data["pico"]["population"]
    assert pop["human_review_status"] == "confirmed"
    assert pop["radar_status"] == "supported"


def test_correct_pico_radar_field_endpoint(client: TestClient, api_radar_fixture):
    """Test POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field}/correct."""
    ws, group = api_radar_fixture

    payload = {
        "claim_value": "Relapsed/refractory acute myeloid leukemia",
        "reason": "Subtype AML explicitly stated in baseline table",
        "actor_id": "dr-reviewer",
    }
    resp = client.post(
        f"/api/v1/workspaces/{ws.id}/groups/{group.id}/pico-radar/population/correct",
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()

    pop = data["pico"]["population"]
    assert pop["human_review_status"] == "corrected"
    assert pop["claim_value"] == "Relapsed/refractory acute myeloid leukemia"
    assert pop["reviewer_correction_reason"] == "Subtype AML explicitly stated in baseline table"


def test_flag_uncertain_and_conflict_endpoints(client: TestClient, api_radar_fixture):
    """Test flagging uncertainty and conflicting evidence."""
    ws, group = api_radar_fixture

    # Flag uncertain
    resp1 = client.post(
        f"/api/v1/workspaces/{ws.id}/groups/{group.id}/pico-radar/outcome/flag-uncertain",
        json={"uncertainty_note": "Unclear whether survival or toxicity was primary", "actor_id": "reviewer"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["pico"]["outcome"]["radar_status"] == "uncertain"

    # Flag conflict
    resp2 = client.post(
        f"/api/v1/workspaces/{ws.id}/groups/{group.id}/pico-radar/comparator/flag-conflict",
        json={"conflict_explanation": "Contradictory comparator definitions in abstract", "actor_id": "reviewer"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["pico"]["comparator"]["radar_status"] == "conflicting"


def test_cross_workspace_isolation_guards(client: TestClient, api_radar_fixture):
    """Verify cross-workspace unauthorized requests are strictly rejected with 404."""
    ws, group = api_radar_fixture

    # Wrong workspace for overview
    resp = client.get("/api/v1/workspaces/ws-nonexistent/pico-radar")
    assert resp.status_code == 404

    # Group belonging to ws requested under another workspace
    resp2 = client.get(f"/api/v1/workspaces/ws-other/groups/{group.id}/pico-radar")
    assert resp2.status_code == 404
