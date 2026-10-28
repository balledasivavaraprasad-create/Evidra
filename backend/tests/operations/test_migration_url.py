"""Which database Alembic migrates: an explicit DATABASE_URL always wins."""
from pathlib import Path

from app.db.migration_url import resolve_migration_url

POOLED = "postgresql://u:p@ep-pooler.neon.tech/db"
UNPOOLED = "postgresql://u:p@ep-direct.neon.tech/db"
DEFAULT = "sqlite:///./review.sqlite"


def env_local(tmp_path: Path, body: str) -> Path:
    path = tmp_path / ".env.local"
    path.write_text(body, encoding="utf-8")
    return path


def test_explicit_database_url_wins_over_unpooled_in_env_and_file(tmp_path):
    f = env_local(tmp_path, f'DATABASE_URL_UNPOOLED="{UNPOOLED}"\n')
    url = resolve_migration_url({"DATABASE_URL": POOLED, "DATABASE_URL_UNPOOLED": UNPOOLED}, f, DEFAULT)
    assert url == "postgresql+psycopg://u:p@ep-pooler.neon.tech/db"


def test_unpooled_env_var_used_only_when_database_url_is_not_set(tmp_path):
    f = env_local(tmp_path, "")
    assert resolve_migration_url({"DATABASE_URL_UNPOOLED": UNPOOLED}, f, DEFAULT).endswith("ep-direct.neon.tech/db")


def test_unpooled_from_env_local_when_database_url_is_not_set(tmp_path):
    f = env_local(tmp_path, f'DATABASE_URL="{POOLED}"\nDATABASE_URL_UNPOOLED="{UNPOOLED}"\nNEON_BRANCH=dev\n')
    # .env.local's pooled DATABASE_URL is not "set in the process environment", so unpooled is used
    assert resolve_migration_url({}, f, DEFAULT).endswith("ep-direct.neon.tech/db")


def test_falls_back_to_the_settings_url(tmp_path):
    assert resolve_migration_url({}, tmp_path / "missing", DEFAULT) == DEFAULT
    assert resolve_migration_url({"DATABASE_URL": ""}, tmp_path / "missing", DEFAULT) == DEFAULT


def test_tests_never_use_the_unpooled_url(tmp_path):
    f = env_local(tmp_path, f'DATABASE_URL_UNPOOLED="{UNPOOLED}"\n')
    env = {"APP_ENV": "test", "DATABASE_URL_UNPOOLED": UNPOOLED}
    assert resolve_migration_url(env, f, DEFAULT) == DEFAULT
