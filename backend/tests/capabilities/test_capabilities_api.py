"""Tests for /api/v1/capabilities endpoint and feature flags."""

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.contracts.models import CapabilitiesResponse
from app.settings import settings


def test_capabilities_flags_off_by_default(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """When LLM and RAG are disabled, flags reflect false with no sensitive fields."""
    monkeypatch.setattr(settings, "auth_mode", "local")
    monkeypatch.setattr(settings, "llm_enabled", False)
    monkeypatch.setattr(settings, "rag_enabled", False)

    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200

    data = response.json()
    assert data == {"llm_enabled": False, "rag_enabled": False}

    # Strict contract: no secrets, provider names or credentials exposed
    assert set(data.keys()) == {"llm_enabled", "rag_enabled"}
    validated = CapabilitiesResponse.model_validate(data)
    assert validated.llm_enabled is False
    assert validated.rag_enabled is False


def test_capabilities_flags_on(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """When LLM and RAG are enabled in settings, flags accurately reflect true."""
    monkeypatch.setattr(settings, "auth_mode", "local")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "rag_enabled", True)

    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200

    data = response.json()
    assert data == {"llm_enabled": True, "rag_enabled": True}
    validated = CapabilitiesResponse.model_validate(data)
    assert validated.llm_enabled is True
    assert validated.rag_enabled is True


def test_capabilities_requires_sign_in(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """When AUTH_MODE=accounts, /api/v1/capabilities requires a signed-in user like other /api routes."""
    password = "test-secret-password-123"
    monkeypatch.setattr(settings, "auth_mode", "accounts")
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    auth.reset_failed_attempts()

    try:
        # Unauthenticated request must be blocked
        blocked = client.get("/api/v1/capabilities")
        assert blocked.status_code == 401
        assert blocked.json()["code"] == "AUTH_REQUIRED"

        # Login to obtain session
        signup = client.post(
            "/api/v1/auth/signup",
            json={"name": "Asha", "email": "asha@example.com", "password": password},
        )
        assert signup.status_code == 201

        # Authenticated request succeeds
        allowed = client.get("/api/v1/capabilities")
        assert allowed.status_code == 200
        assert "llm_enabled" in allowed.json()
    finally:
        auth.reset_failed_attempts()
        client.cookies.clear()
