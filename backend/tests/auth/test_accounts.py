"""User accounts (AUTH_MODE=accounts): sign-up, sign-in, Google, sessions and review ownership."""
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.db.models import PaperGroupModel, UserModel, WorkspaceModel
from app.settings import settings

PASSWORD = "correct horse battery"


@pytest.fixture
def accounts(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_mode", "accounts")
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    monkeypatch.setattr(settings, "google_client_id", "test-client.apps.googleusercontent.com")
    auth.reset_failed_attempts()
    yield
    auth.reset_failed_attempts()


def _signup(client: TestClient, email: str, name: str = "Reviewer"):
    return client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": PASSWORD})


def test_api_requires_sign_in(client, accounts):
    res = client.get("/api/v1/workspaces")
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"

    session = client.get("/api/v1/auth/session").json()
    assert session["auth_required"] is True
    assert session["authenticated"] is False
    assert session["google_client_id"] == "test-client.apps.googleusercontent.com"


def test_signup_signs_in_and_hashes_password(client, accounts, db_session):
    res = _signup(client, "Asha@Example.com", "Asha")
    assert res.status_code == 201
    assert res.json()["email"] == "asha@example.com"

    user = db_session.query(UserModel).filter_by(email="asha@example.com").one()
    assert user.password_hash and PASSWORD not in user.password_hash

    session = client.get("/api/v1/auth/session").json()
    assert session["authenticated"] is True
    assert session["user"]["name"] == "Asha"
    assert client.get("/api/v1/workspaces").status_code == 200


def test_signup_rejects_duplicate_email_and_bad_input(client, accounts):
    assert _signup(client, "dup@example.com").status_code == 201
    dup = _signup(client, "DUP@example.com")
    assert dup.status_code == 409
    assert dup.json()["code"] == "EMAIL_TAKEN"

    assert _signup(client, "not-an-email").status_code == 422
    short = client.post("/api/v1/auth/signup", json={"name": "A", "email": "a@b.co", "password": "short"})
    assert short.status_code == 422


def test_login_logout_and_wrong_password(client, accounts):
    _signup(client, "lee@example.com")
    client.post("/api/v1/auth/logout")
    client.cookies.clear()
    assert client.get("/api/v1/workspaces").status_code == 401

    wrong = client.post("/api/v1/auth/login", json={"email": "lee@example.com", "password": "nope-nope"})
    assert wrong.status_code == 401
    assert wrong.json()["code"] == "INVALID_CREDENTIALS"

    ok = client.post("/api/v1/auth/login", json={"email": "LEE@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert client.get("/api/v1/workspaces").status_code == 200


def test_login_throttles_repeated_failures(client, accounts):
    for _ in range(auth.MAX_FAILED):
        client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass"})
    res = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass"})
    assert res.status_code == 429


def test_tampered_or_expired_session_is_rejected(client, accounts):
    _signup(client, "t@example.com")
    token = client.cookies.get(auth.COOKIE_NAME)
    assert auth.read_session_token(token) is not None
    assert auth.read_session_token(token[:-1] + ("0" if token[-1] != "0" else "1")) is None
    assert auth.read_session_token(token, now=10**12) is None

    client.cookies.clear()
    client.cookies.set(auth.COOKIE_NAME, token.replace("v2.", "v2.someone-else", 1))
    assert client.get("/api/v1/workspaces").status_code == 401


def test_google_sign_in_creates_then_links_account(client, accounts, db_session, monkeypatch):
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "google-123",
        "email": "g@example.com",
        "email_verified": True,
        "name": "Gita",
    }
    monkeypatch.setattr(auth, "verify_google_credential", lambda credential: claims)

    res = client.post("/api/v1/auth/google", json={"credential": "x" * 40})
    assert res.status_code == 200
    assert res.json()["has_google"] is True
    assert db_session.query(UserModel).filter_by(google_sub="google-123").count() == 1

    # Same Google account again: same user, no duplicate
    client.cookies.clear()
    again = client.post("/api/v1/auth/google", json={"credential": "x" * 40})
    assert again.json()["id"] == res.json()["id"]

    # A password user with the same verified email gets Google linked, not a second account
    client.cookies.clear()
    _signup(client, "linked@example.com")
    client.cookies.clear()
    monkeypatch.setattr(
        auth, "verify_google_credential", lambda c: {**claims, "sub": "google-456", "email": "linked@example.com"}
    )
    linked = client.post("/api/v1/auth/google", json={"credential": "x" * 40})
    assert linked.json()["has_password"] is True and linked.json()["has_google"] is True


def test_google_sign_in_rejects_bad_token(client, accounts, monkeypatch):
    def boom(credential):
        raise ValueError("bad")

    monkeypatch.setattr(auth, "verify_google_credential", boom)
    res = client.post("/api/v1/auth/google", json={"credential": "x" * 40})
    assert res.status_code == 401


def test_each_user_sees_and_touches_only_their_own_reviews(client, accounts, db_session):
    _signup(client, "owner@example.com")
    created = client.post("/api/v1/workspaces", json={"title": "SGLT2i and HF hospitalization in T2D"})
    assert created.status_code == 201
    ws_id = created.json()["id"]
    group = PaperGroupModel(id="grp-owned", workspace_id=ws_id, membership_fingerprint="fp")
    db_session.add(group)
    db_session.commit()

    assert [w["id"] for w in client.get("/api/v1/workspaces").json()] == [ws_id]
    assert client.get(f"/api/v1/workspaces/{ws_id}/revisions").status_code == 200

    # Second user
    client.cookies.clear()
    _signup(client, "other@example.com")
    assert client.get("/api/v1/workspaces").json() == []
    assert client.get(f"/api/v1/workspaces/{ws_id}/revisions").status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_id}/criteria").status_code == 404
    assert client.get("/api/v1/groups/grp-owned").status_code == 404
    assert client.post(f"/api/v1/workspaces/{ws_id}/process-corpus").status_code == 404

    # Combining the other user's group with your own workspace id is rejected too
    mine = client.post("/api/v1/workspaces", json={"title": "Mine"}).json()["id"]
    assert client.get(f"/api/v1/workspaces/{mine}/groups/grp-owned/pico-radar").status_code == 404


def test_unowned_legacy_reviews_are_hidden(client, accounts, db_session):
    db_session.add(WorkspaceModel(id="ws-synth-001", title="Demo", created_by="reviewer-alice"))
    db_session.commit()
    _signup(client, "new@example.com")
    assert client.get("/api/v1/workspaces").json() == []
    assert client.get("/api/v1/workspaces/ws-synth-001/revisions").status_code == 404


def test_prisma_endpoints_enforce_user_review_ownership(client, accounts, db_session):
    """PRISMA endpoints must return 404 to a second signed-in user for another user's review."""
    _signup(client, "user1@example.com")
    res = client.post("/api/v1/workspaces", json={"title": "User 1 Review"})
    assert res.status_code == 201
    ws_id = res.json()["id"]

    # Owner can access PRISMA endpoints
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma").status_code == 200
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma/snapshots").status_code == 200

    snap_res = client.post(
        f"/api/v1/workspaces/{ws_id}/prisma/snapshots",
        json={"name": "Baseline Snapshot", "notes": "Initial snapshot"},
    )
    assert snap_res.status_code == 201
    snap_id = snap_res.json()["snapshot_id"]
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma/snapshots/{snap_id}").status_code == 200

    # Second user signs in
    client.cookies.clear()
    _signup(client, "user2@example.com")

    # Second user accessing User 1's PRISMA endpoints receives 404 (not 403 or 200)
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma").status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma/records?stage=screening").status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma/export/csv").status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma/snapshots").status_code == 404
    assert client.post(f"/api/v1/workspaces/{ws_id}/prisma/snapshots", json={"name": "Unauthorized"}).status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_id}/prisma/snapshots/{snap_id}").status_code == 404

    # User 2 combining their own workspace with User 1's snapshot_id is also rejected with 404
    user2_ws = client.post("/api/v1/workspaces", json={"title": "User 2 Review"}).json()["id"]
    assert client.get(f"/api/v1/workspaces/{user2_ws}/prisma/snapshots/{snap_id}").status_code == 404
