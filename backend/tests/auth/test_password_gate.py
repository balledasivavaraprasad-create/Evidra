"""Shared-password gate (AUTH_MODE=password) used for hosted demos."""

import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.settings import Settings, settings

PASSWORD = "correct-horse-battery"


@pytest.fixture
def gated(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_mode", "password")
    monkeypatch.setattr(settings, "site_password", PASSWORD)
    monkeypatch.setattr(settings, "session_cookie_secure", False)  # TestClient talks plain http
    auth.reset_failed_attempts()
    yield
    auth.reset_failed_attempts()


def _login(client: TestClient, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"password": password})


def test_gate_is_off_by_default(client: TestClient):
    assert client.get("/api/v1/auth/session").json() == {"auth_required": False, "authenticated": True}
    assert client.get("/api/v1/workspaces/ws-x/revisions").status_code != 401


def test_api_requires_login_but_health_stays_public(client: TestClient, gated):
    blocked = client.get("/api/v1/workspaces/ws-x/revisions")
    assert blocked.status_code == 401
    assert blocked.json()["code"] == "AUTH_REQUIRED"

    assert client.get("/health/live").status_code == 200
    assert client.get("/openapi.json").status_code == 401
    assert client.get("/api/v1/auth/session").json() == {"auth_required": True, "authenticated": False}


def test_wrong_password_is_rejected(client: TestClient, gated):
    res = _login(client, "nope-nope-nope")
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_PASSWORD"
    assert auth.COOKIE_NAME not in res.cookies


def test_login_unlocks_api_and_logout_locks_it_again(client: TestClient, gated):
    res = _login(client)
    assert res.status_code == 204
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie

    assert client.get("/api/v1/auth/session").json()["authenticated"] is True
    assert client.get("/api/v1/workspaces/ws-x/revisions").status_code != 401

    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.get("/api/v1/workspaces/ws-x/revisions").status_code == 401


def test_repeated_failures_are_throttled(client: TestClient, gated):
    for _ in range(auth.MAX_FAILED):
        assert _login(client, "wrong-password").status_code == 401
    throttled = _login(client)  # even the right password waits out the window
    assert throttled.status_code == 429
    assert throttled.json()["code"] == "TOO_MANY_ATTEMPTS"


def test_tokens_expire_and_are_tied_to_the_password(monkeypatch: pytest.MonkeyPatch, gated):
    now = time.time()
    token = auth.issue_session_token(now)
    assert auth.verify_session_token(token, now)
    assert not auth.verify_session_token(token, now + auth.SESSION_TTL_SECONDS + 1)
    assert not auth.verify_session_token(token[:-1] + ("0" if token[-1] != "0" else "1"), now)

    monkeypatch.setattr(settings, "site_password", "a-brand-new-password")
    assert not auth.verify_session_token(token, now)


def test_settings_require_a_real_password():
    with pytest.raises(ValueError, match="SITE_PASSWORD"):
        Settings(auth_mode="password", site_password="short")
    ok = Settings(
        app_env="production",
        auth_mode="password",
        site_password="long-enough-password",
        secret_key="x" * 40,
    )
    assert ok.auth_mode == "password"
    with pytest.raises(ValueError, match="AUTH_MODE='local'"):
        Settings(app_env="production", auth_mode="local", secret_key="x" * 40)
