"""Shared-password gate for hosted demos (AUTH_MODE=password).

When enabled, every API route (and the interactive API docs) requires a signed
session cookie obtained by posting the site password to ``/api/v1/auth/login``.
The SPA shell, its static assets and the health probes stay public: they carry no
review data, and hosting platforms need the health probes.

This is deliberately small: one shared password, an HMAC-signed expiring cookie,
constant-time comparison and a per-client limit on failed attempts. It is not a
user-account system; actor attribution still follows ``AUTH_MODE`` semantics.
"""
from __future__ import annotations

import hashlib
import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.contracts.models import ErrorEnvelope
from app.settings import settings

COOKIE_NAME = "evidra_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
_TOKEN_VERSION = "v1"

# Failed-login throttling: at most MAX_FAILED attempts per client per WINDOW seconds
MAX_FAILED = 10
WINDOW_SECONDS = 5 * 60
_failed_attempts: dict[str, deque[float]] = defaultdict(deque)
_failed_lock = threading.Lock()

PUBLIC_API_PREFIX = "/api/v1/auth/"
PROTECTED_DOC_PATHS = {"/docs", "/redoc", "/openapi.json"}


def password_gate_enabled() -> bool:
    return settings.auth_mode == "password"


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def _password_fingerprint() -> str:
    """Binds sessions to the current password, so changing it signs everyone out."""
    return hashlib.sha256((settings.site_password or "").encode()).hexdigest()[:16]


def _sign(payload: str) -> str:
    return hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_session_token(now: float | None = None) -> str:
    expires = int((now if now is not None else time.time()) + SESSION_TTL_SECONDS)
    payload = f"{_TOKEN_VERSION}.{expires}.{_password_fingerprint()}"
    return f"{_TOKEN_VERSION}.{expires}.{_sign(payload)}"


def verify_session_token(token: str | None, now: float | None = None) -> bool:
    if not token:
        return False
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != _TOKEN_VERSION:
        return False
    try:
        expires = int(parts[1])
    except ValueError:
        return False
    if expires < (now if now is not None else time.time()):
        return False
    expected = _sign(f"{_TOKEN_VERSION}.{expires}.{_password_fingerprint()}")
    return hmac.compare_digest(expected, parts[2])


def _cookie_secure() -> bool:
    if settings.session_cookie_secure is not None:
        return settings.session_cookie_secure
    return settings.app_env == "production"


def _client_key(request: Request) -> str:
    # Behind Render's proxy the first X-Forwarded-For hop is the client
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many_failures(key: str, now: float) -> bool:
    with _failed_lock:
        attempts = _failed_attempts[key]
        while attempts and now - attempts[0] > WINDOW_SECONDS:
            attempts.popleft()
        return len(attempts) >= MAX_FAILED


def _record_failure(key: str, now: float) -> None:
    with _failed_lock:
        _failed_attempts[key].append(now)


def reset_failed_attempts() -> None:
    """Test helper: clear the in-memory throttle."""
    with _failed_lock:
        _failed_attempts.clear()


def _error(status_code: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    envelope = ErrorEnvelope(code=code, message=message, retryable=retryable, details=None)
    return JSONResponse(status_code=status_code, content=envelope.model_dump())


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class PasswordGateMiddleware(BaseHTTPMiddleware):
    """Rejects API and docs requests without a valid session when AUTH_MODE=password."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not password_gate_enabled() or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        protected = (path.startswith("/api/") and not path.startswith(PUBLIC_API_PREFIX)) or path in PROTECTED_DOC_PATHS
        if protected and not verify_session_token(request.cookies.get(COOKIE_NAME)):
            return _error(
                status.HTTP_401_UNAUTHORIZED,
                "AUTH_REQUIRED",
                "Enter the site password to continue.",
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class AuthLoginRequest(BaseModel):
    """Shared site password submitted from the login screen."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=256)


class AuthSessionResponse(BaseModel):
    """Whether this deployment requires the site password, and whether the caller has it."""

    auth_required: bool
    authenticated: bool


auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.get("/session", response_model=AuthSessionResponse)
def get_auth_session(request: Request) -> AuthSessionResponse:
    """Report whether a password is required and whether this browser is signed in."""
    if not password_gate_enabled():
        return AuthSessionResponse(auth_required=False, authenticated=True)
    return AuthSessionResponse(
        auth_required=True,
        authenticated=verify_session_token(request.cookies.get(COOKIE_NAME)),
    )


@auth_router.post(
    "/login",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorEnvelope, "description": "Wrong password"},
        429: {"model": ErrorEnvelope, "description": "Too many failed attempts"},
    },
)
def login(payload: AuthLoginRequest, request: Request) -> Response:
    """Exchange the shared site password for a signed, expiring session cookie."""
    if not password_gate_enabled():
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    now = time.time()
    key = _client_key(request)
    if _too_many_failures(key, now):
        return _error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "TOO_MANY_ATTEMPTS",
            "Too many wrong passwords. Wait a few minutes, then try again.",
            retryable=True,
        )

    expected = (settings.site_password or "").encode()
    if not expected or not hmac.compare_digest(payload.password.encode(), expected):
        _record_failure(key, now)
        return _error(status.HTTP_401_UNAUTHORIZED, "INVALID_PASSWORD", "That password isn't right. Try again.")

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.set_cookie(
        COOKIE_NAME,
        issue_session_token(now),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    return response


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    """Clear the session cookie."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=_cookie_secure(), samesite="lax")
    return response
