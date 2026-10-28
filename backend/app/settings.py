"""Application settings and environment configuration."""
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration validated through pydantic-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
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

    auth_mode: Literal["local", "production"] = "local"
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
    llm_max_budget_cents: int = Field(default=500, description="Spend limit in cents")
    langsmith_tracing: bool = False

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
                    "AUTH_MODE='local' is not permitted in production. "
                    "Configure an authenticated identity provider."
                )
        return self


settings = Settings()
