"""Contract and schema integration tests for Evidra backend foundation."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.contracts.enums import (
    PicoLabel,
    SourceNamespace,
)
from app.contracts.models import (
    PicoSpan,
    QueryASTNode,
    QueryVersionCreate,
    RecordRevisionResponse,
)
from app.db.models import (
    JobModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.main import app
from tests.fixtures.synthetic_records import (
    ALL_SYNTHETIC_RECORDS,
    RECORD_UNICODE_SPANS,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_synthetic_fixtures_conformance():
    """Verify all 16 synthetic records validate against the RecordRevisionResponse contract."""
    assert len(ALL_SYNTHETIC_RECORDS) == 16
    for item in ALL_SYNTHETIC_RECORDS:
        record = RecordRevisionResponse.model_validate(item)
        assert record.id is not None
        assert record.content_hash is not None
        assert record.source in (SourceNamespace.PUBMED, SourceNamespace.EUROPEPMC)


def test_pico_span_code_point_validation():
    """Verify half-open Unicode code-point offsets and strict validation."""
    abstract = RECORD_UNICODE_SPANS["abstract_text"]
    assert abstract is not None

    # Valid span
    quote = "metformin"
    start = abstract.index(quote)
    end = start + len(quote)
    span = PicoSpan(
        label=PicoLabel.I,
        start_cp=start,
        end_cp=end,
        quote=quote,
        provenance="rule:test",
    )
    assert abstract[span.start_cp : span.end_cp] == span.quote

    # Invalid: start >= end
    with pytest.raises(ValidationError):
        PicoSpan(
            label=PicoLabel.I,
            start_cp=10,
            end_cp=10,
            quote="bad",
            provenance="rule:test",
        )

    with pytest.raises(ValidationError):
        PicoSpan(
            label=PicoLabel.I,
            start_cp=10,
            end_cp=5,
            quote="bad",
            provenance="rule:test",
        )


def test_query_version_date_validation():
    """Verify date formatting regex enforcement in query contracts."""
    ast = QueryASTNode(term="metformin")
    valid = QueryVersionCreate(
        ast=ast,
        start_date="2020-01-01",
        end_date="2024-12-31",
        sources=[SourceNamespace.PUBMED],
        criteria_version_id="crit-1",
    )
    assert valid.start_date == "2020-01-01"

    # Year only is valid
    valid_year = QueryVersionCreate(
        ast=ast,
        start_date="2020",
        end_date="2024",
        sources=[SourceNamespace.PUBMED],
        criteria_version_id="crit-1",
    )
    assert valid_year.start_date == "2020"

    # Malformed date strings fail validation
    with pytest.raises(ValidationError):
        QueryVersionCreate(
            ast=ast,
            start_date="01/01/2020",
            sources=[SourceNamespace.PUBMED],
            criteria_version_id="crit-1",
        )


def test_health_live_endpoint(client: TestClient):
    """Liveness probe must return status 200 with application metadata."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_ready_endpoint(client: TestClient):
    """Readiness probe must return 200 when database responds to queries."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_workspace_creation_and_persistence(client: TestClient, db_session: Session):
    """POST /api/v1/workspaces must persist workspace and return 201."""
    payload = {"title": "Type 2 Diabetes Metformin Review", "description": "Systematic evaluation of HbA1c"}
    response = client.post("/api/v1/workspaces", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["row_version"] == 1
    assert data["id"] is not None

    # Check persistence in database
    row = db_session.query(WorkspaceModel).filter_by(id=data["id"]).first()
    assert row is not None
    assert row.title == payload["title"]


def test_declared_route_stubs_return_501(client: TestClient):
    """Unimplemented /api/v1 operations must return structured 501 instead of unhandled crashes."""
    response = client.post(
        "/api/v1/workspaces/ws-test-1/criteria",
        json={
            "question": "What is the effect of metformin?",
            "pico_description": {"population": "Adults"},
            "criteria": [
                {
                    "id": "c1",
                    "name": "Human adults",
                    "category": "population",
                    "is_inclusion": True,
                    "rationale": "Must be human",
                }
            ],
        },
    )
    assert response.status_code == 501
    error = response.json()
    assert error["code"] == "NOT_IMPLEMENTED"
    assert "create_criteria_version" in error["message"]


def test_db_source_record_unique_constraint(db_session: Session):
    """Database must enforce unique source identities (workspace + source + namespace + external_id)."""
    ws = WorkspaceModel(title="Test WS", created_by="tester")
    db_session.add(ws)
    db_session.commit()

    rec1 = SourceRecordModel(
        workspace_id=ws.id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="12345678",
    )
    db_session.add(rec1)
    db_session.commit()

    # Repeat of exact same identity must raise IntegrityError
    rec2 = SourceRecordModel(
        workspace_id=ws.id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="12345678",
    )
    db_session.add(rec2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_job_request_key_idempotency(db_session: Session):
    """Database must reject duplicate job requests for same workspace and request key."""
    ws = WorkspaceModel(title="Job WS", created_by="tester")
    db_session.add(ws)
    db_session.commit()

    job1 = JobModel(
        workspace_id=ws.id,
        kind="import_records",
        request_key="req-idemp-123",
        payload_hash="hash1",
        state="queued",
    )
    db_session.add(job1)
    db_session.commit()

    job2 = JobModel(
        workspace_id=ws.id,
        kind="import_records",
        request_key="req-idemp-123",
        payload_hash="hash2",
        state="queued",
    )
    db_session.add(job2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_openapi_json_is_up_to_date():
    """Verify repo root contracts/openapi.json matches the generated FastAPI schema."""
    target_path = REPO_ROOT / "contracts" / "openapi.json"
    assert target_path.exists(), "contracts/openapi.json must exist at repo root"

    committed_spec = json.loads(target_path.read_text(encoding="utf-8"))
    current_spec = app.openapi()

    # Compare paths and components
    assert set(committed_spec["paths"].keys()) == set(current_spec["paths"].keys())
    assert "/api/v1/workspaces" in current_spec["paths"]
    assert "/api/v1/workspaces/{workspace_id}/criteria" in current_spec["paths"]
    assert "/api/v1/workspaces/{workspace_id}/queries" in current_spec["paths"]
    assert "/health/ready" in current_spec["paths"]
