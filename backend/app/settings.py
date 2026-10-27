"""Application settings and environment configuration."""
from pathlib import Path
from typing import Literal

from pydantic import Field
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
    data_dir: Path = Field(default=Path("./data"), description="Artifact and cache storage directory")

    ci_offline: bool = False
    source_mode: Literal["live", "fixture"] = "live"
    llm_enabled: bool = False
    rag_enabled: bool = False
    langsmith_tracing: bool = False

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]


settings = Settings()
