"""Pick the database URL Alembic migrates."""
from collections.abc import Mapping
from pathlib import Path

from app.db.session import normalize_database_url


def read_env_local_unpooled(env_local: Path) -> str | None:
    """Read DATABASE_URL_UNPOOLED from the repo-root .env.local written by the Neon CLI."""
    if env_local.exists():
        for line in env_local.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL_UNPOOLED="):
                return line.split("=", 1)[1].strip().strip("\"'") or None
    return None


def resolve_migration_url(environ: Mapping[str, str], env_local: Path, default_url: str) -> str:
    """An explicitly set DATABASE_URL always wins.

    Only when it is not set does a Neon unpooled (direct) URL get used, from the environment or
    .env.local, because pooled connections are not suited to migrations. Tests (APP_ENV=test)
    never use the unpooled URL, so a test run cannot migrate the hosted database.
    """
    url = environ.get("DATABASE_URL")
    if not url and environ.get("APP_ENV") != "test":
        url = environ.get("DATABASE_URL_UNPOOLED") or read_env_local_unpooled(env_local)
    return normalize_database_url(url or default_url)
