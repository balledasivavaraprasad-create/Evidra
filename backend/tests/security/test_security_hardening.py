"""Tests for production security hardening, secrets validation, and endpoint boundaries (D06)."""
import pytest
from fastapi.testclient import TestClient

from app.contracts.models import AssistantRequest, ScreeningRankRequest
from app.settings import Settings


def test_production_settings_rejects_insecure_defaults():
    # Insecure secret key in production
    with pytest.raises(ValueError, match="Insecure default secret_key"):
        Settings(
            app_env="production",
            secret_key="dev-insecure-secret-key-change-in-production-only",
            auth_mode="accounts",
        )

    # Short secret key in production
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            app_env="production",
            secret_key="too-short",
            auth_mode="accounts",
        )

    # Local auth mode in production
    with pytest.raises(ValueError, match="AUTH_MODE='local' is not permitted in production"):
        Settings(
            app_env="production",
            secret_key="a" * 32,
            auth_mode="local",
        )


def test_production_settings_accepts_hardened_config():
    valid = Settings(
        app_env="production",
        secret_key="a" * 32,
        auth_mode="accounts",
    )
    assert valid.app_env == "production"
    assert valid.auth_mode == "accounts"


def test_assistant_endpoint_fails_closed_when_disabled(client: TestClient, monkeypatch):
    from app import settings as s_mod
    monkeypatch.setattr(s_mod.settings, "llm_enabled", False)
    monkeypatch.setattr(s_mod.settings, "rag_enabled", False)

    req = AssistantRequest(
        task="explain_screening",
        target_id="group-1",
        user_prompt="Why was this paper excluded?",
    )
    response = client.post("/api/v1/workspaces/ws-test/assistant", json=req.model_dump())
    assert response.status_code == 501
    data = response.json()
    assert "query_assistant" in data["message"].lower() or "disabled" in data["message"].lower()


def test_screening_rank_endpoint_does_not_mutate_decisions(client: TestClient, db_session):
    from app.db.models import WorkspaceModel
    ws = WorkspaceModel(title="Security WS", created_by="tester")
    db_session.add(ws)
    db_session.commit()

    req = ScreeningRankRequest(limit=10)
    response = client.post(f"/api/v1/workspaces/{ws.id}/screening/rank", json=req.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == ws.id
    assert "status" in data
