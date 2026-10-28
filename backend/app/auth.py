"""User accounts and sessions (AUTH_MODE=accounts).

People sign up with email + password or with Google. A successful sign-in sets an
HMAC-signed, expiring, httponly session cookie that carries the user id. Every API
route except ``/api/v1/auth/*`` requires that cookie; the SPA shell, static assets
and health probes stay public because they carry no review data.

AUTH_MODE=local (development and tests) turns all of this off: every request acts as
the built-in local user and ownership is not enforced.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.contracts.models import ErrorEnvelope
from app.db.models import UserModel
from app.db.session import get_db
from app.settings import settings

COOKIE_NAME = "evidra_session"
SESSION_TTL_SECONDS = 14 * 24 * 60 * 60
_TOKEN_VERSION = "v2"
LOCAL_USER_ID = "user-local"

# Failed sign-in throttling: at most MAX_FAILED attempts per client per WINDOW seconds
MAX_FAILED = 10
WINDOW_SECONDS = 5 * 60
_failed_attempts: dict[str, deque[float]] = defaultdict(deque)
_failed_lock = threading.Lock()

PUBLIC_API_PREFIX = "/api/v1/auth/"
PROTECTED_DOC_PATHS = {"/docs", "/redoc", "/openapi.json"}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_hasher = PasswordHasher()


def accounts_enabled() -> bool:
    return settings.auth_mode == "accounts"


# ---------------------------------------------------------------------------
# Session tokens: v2.<user_id>.<expires>.<signature>
# ---------------------------------------------------------------------------


def _sign(payload: str) -> str:
    return hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_session_token(user_id: str, now: float | None = None) -> str:
    expires = int((now if now is not None else time.time()) + SESSION_TTL_SECONDS)
    payload = f"{_TOKEN_VERSION}.{user_id}.{expires}"
    return f"{payload}.{_sign(payload)}"


def read_session_token(token: str | None, now: float | None = None) -> str | None:
    """Return the user id inside a valid, unexpired token, else None."""
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != _TOKEN_VERSION or not parts[1]:
        return None
    try:
        expires = int(parts[2])
    except ValueError:
        return None
    if expires < (now if now is not None else time.time()):
        return None
    expected = _sign(f"{parts[0]}.{parts[1]}.{parts[2]}")
    if not hmac.compare_digest(expected, parts[3]):
        return None
    return parts[1]


def current_user_id(request: Request) -> str | None:
    """User id the middleware attached to this request (LOCAL_USER_ID in local mode)."""
    return getattr(request.state, "user_id", None)


def _cookie_secure() -> bool:
    if settings.session_cookie_secure is not None:
        return settings.session_cookie_secure
    return settings.app_env == "production"


def _set_session_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        issue_session_token(user_id),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


# ---------------------------------------------------------------------------
# Throttling
# ---------------------------------------------------------------------------


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


class SessionAuthMiddleware(BaseHTTPMiddleware):
    """Attach the signed-in user to the request and reject protected calls without one."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not accounts_enabled():
            request.state.user_id = LOCAL_USER_ID
            return await call_next(request)

        request.state.user_id = read_session_token(request.cookies.get(COOKIE_NAME))
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        protected = (
            path.startswith("/api/")
            and not path.startswith(PUBLIC_API_PREFIX)
        ) or path in PROTECTED_DOC_PATHS
        if protected and not request.state.user_id:
            return _error(status.HTTP_401_UNAUTHORIZED, "AUTH_REQUIRED", "Sign in to continue.")
        return await call_next(request)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SignUpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class GoogleSignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential: str = Field(min_length=10, max_length=8192, description="Google Identity Services ID token")


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    has_password: bool
    has_google: bool


class AuthSessionResponse(BaseModel):
    """Whether this deployment requires sign-in, who is signed in, and which sign-in methods exist."""

    auth_required: bool
    authenticated: bool
    user: UserResponse | None = None
    google_client_id: str | None = None


def _user_response(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        has_password=bool(user.password_hash),
        has_google=bool(user.google_sub),
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_or_create_local_user(db: Session) -> UserModel:
    user = db.get(UserModel, LOCAL_USER_ID)
    if user is None:
        user = UserModel(id=LOCAL_USER_ID, email="local@evidra.dev", name="Local reviewer")
        db.add(user)
        db.commit()
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.get("/session", response_model=AuthSessionResponse)
def get_auth_session(request: Request, db: Session = Depends(get_db)) -> AuthSessionResponse:  # noqa: B008
    """Report whether sign-in is required and who (if anyone) is signed in."""
    if not accounts_enabled():
        return AuthSessionResponse(
            auth_required=False,
            authenticated=True,
            user=_user_response(get_or_create_local_user(db)),
        )
    user_id = current_user_id(request)
    user = db.get(UserModel, user_id) if user_id else None
    return AuthSessionResponse(
        auth_required=True,
        authenticated=user is not None,
        user=_user_response(user) if user else None,
        google_client_id=settings.google_client_id,
    )


@auth_router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}},
)
def sign_up(payload: SignUpRequest, response: Response, db: Session = Depends(get_db)):  # noqa: B008
    """Create an account with email and password, and sign in."""
    email = _normalize_email(payload.email)
    if not _EMAIL_RE.match(email):
        return _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_EMAIL", "Enter a valid email address.")
    if db.query(UserModel).filter_by(email=email).first():
        return _error(
            status.HTTP_409_CONFLICT,
            "EMAIL_TAKEN",
            "An account with this email already exists. Sign in instead.",
        )
    user = UserModel(
        id=str(uuid4()),
        email=email,
        name=payload.name.strip(),
        password_hash=_hasher.hash(payload.password),
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    _set_session_cookie(response, user.id)
    return _user_response(user)


@auth_router.post(
    "/login",
    response_model=UserResponse,
    responses={401: {"model": ErrorEnvelope}, 429: {"model": ErrorEnvelope}},
)
def sign_in(payload: SignInRequest, request: Request, response: Response, db: Session = Depends(get_db)):  # noqa: B008
    """Sign in with email and password."""
    now = time.time()
    key = _client_key(request)
    if _too_many_failures(key, now):
        return _error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "TOO_MANY_ATTEMPTS",
            "Too many failed sign-ins. Wait a few minutes, then try again.",
            retryable=True,
        )

    user = db.query(UserModel).filter_by(email=_normalize_email(payload.email)).first()
    valid = False
    if user and user.password_hash:
        try:
            valid = _hasher.verify(user.password_hash, payload.password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            valid = False
    if not valid:
        _record_failure(key, now)
        if user and not user.password_hash and user.google_sub:
            return _error(
                status.HTTP_401_UNAUTHORIZED,
                "USE_GOOGLE",
                "This account signs in with Google. Use 'Continue with Google'.",
            )
        return _error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Wrong email or password.")

    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(payload.password)
    user.last_login_at = datetime.now(UTC)
    db.commit()
    _set_session_cookie(response, user.id)
    return _user_response(user)


def verify_google_credential(credential: str) -> dict:
    """Verify a Google ID token and return its claims. Raises ValueError if invalid."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    claims = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.google_client_id)
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("Wrong issuer")
    if not claims.get("email") or not claims.get("email_verified"):
        raise ValueError("Google account email is not verified")
    return claims


@auth_router.post(
    "/google",
    response_model=UserResponse,
    responses={401: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}},
)
def sign_in_with_google(payload: GoogleSignInRequest, response: Response, db: Session = Depends(get_db)):  # noqa: B008
    """Sign in (creating the account on first use) with a Google Identity Services ID token."""
    if not settings.google_client_id:
        return _error(status.HTTP_503_SERVICE_UNAVAILABLE, "GOOGLE_DISABLED", "Google sign-in isn't set up here.")
    try:
        claims = verify_google_credential(payload.credential)
    except ValueError:
        return _error(status.HTTP_401_UNAUTHORIZED, "INVALID_GOOGLE_TOKEN", "Google sign-in failed. Try again.")

    sub = str(claims["sub"])
    email = _normalize_email(claims["email"])
    user = db.query(UserModel).filter_by(google_sub=sub).first()
    if user is None:
        # Link to an existing email/password account with the same verified address
        user = db.query(UserModel).filter_by(email=email).first()
        if user is None:
            user = UserModel(id=str(uuid4()), email=email, name=claims.get("name") or email.split("@")[0])
            db.add(user)
        user.google_sub = sub
    user.last_login_at = datetime.now(UTC)
    db.commit()
    _set_session_cookie(response, user.id)
    return _user_response(user)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    """Clear the session cookie."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=_cookie_secure(), samesite="lax")
    return response
