"""Application settings and environment configuration."""
import os
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Neon env vars are pulled by `neon checkout` / `neon deploy` into the repo root. Tests never
# read them, so a test run cannot reach the hosted database.
_ENV_FILES: tuple[Path, ...] = (
    ()
    if os.environ.get("APP_ENV") == "test"
    else (Path(__file__).resolve().parents[2] / ".env.local", Path(".env"))
)


class Settings(BaseSettings):
    """Central configuration validated through pydantic-settings."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_title: str = "Evidra Systematic Literature Review Engine"
    app_version: str = "0.1.0"

    database_url: str = Field(default="sqlite:///./review.sqlite", description="SQLite WAL business database URL")
    checkpoint_database_url: str = Field(
        default="sqlite:///./checkpoints.sqlite",
        description="SQLite database URL for LangGraph checkpoints",
    )

    # local: no sign-in, everyone is the built-in local user (development and tests).
    # accounts: people sign up and sign in; each user sees only their own reviews.
    auth_mode: Literal["local", "accounts"] = "local"
    google_client_id: str | None = Field(
        default=None,
        description="Google OAuth Web client ID; enables 'Continue with Google' when set",
    )
    session_cookie_secure: bool | None = Field(
        default=None,
        description="Override the session cookie Secure flag (defaults to True in production)",
    )
    secret_key: str = Field(
        default="dev-insecure-secret-key-change-in-production-only",
        description="Session signing and encryption secret key",
    )
    data_dir: Path = Field(default=Path("./data"), description="Artifact and cache storage directory")

    ci_offline: bool = False
    source_mode: Literal["live", "fixture"] = "live"
    source_rate_limit_per_second: float = Field(
        default=3.0,
        description="Maximum outbound literature source requests per second",
    )

    llm_enabled: bool = False
    rag_enabled: bool = False
    llm_provider: str = Field(default="mock", description="LLM provider: mock, openai, anthropic")
    llm_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="OpenAI-compatible endpoint (default: Gemini)",
    )
    llm_api_key: str | None = Field(default=None, description="Provider API key. Server-side only; never logged or sent to the browser")
    # gemini-2.5-flash is allowed too, but Google no longer serves it to new keys (it points to gemini-3.8-flash)
    llm_model_alias: str = Field(default="gemini-3.8-flash", description="Approved model name used for requests")
    llm_max_budget_cents: int = Field(default=500, description="Spend limit in cents")
    langsmith_tracing: bool = False

    run_worker_in_process: bool | None = Field(
        default=None,
        description="Run background job worker in-process inside FastAPI lifespan",
    )

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Fail closed if insecure local development configurations are used in production."""
        if self.app_env == "production":
            if (
                self.secret_key == "dev-insecure-secret-key-change-in-production-only"
                or len(self.secret_key) < 32
            ):
                raise ValueError(
                    "Insecure default secret_key is not permitted in production. "
                    "Set SECRET_KEY with at least 32 characters."
                )
            if self.auth_mode == "local":
                raise ValueError(
                    "AUTH_MODE='local' is not permitted in production. Use AUTH_MODE=accounts."
                )
        if self.google_client_id is not None and not self.google_client_id.strip():
            self.google_client_id = None
        if self.run_worker_in_process is None:
            self.run_worker_in_process = (self.app_env == "production")
        return self


settings = Settings()
