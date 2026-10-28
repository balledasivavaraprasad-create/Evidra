"""SQLAlchemy engine and session management for Evidra business database."""
import contextlib
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.settings import settings

Base = declarative_base()


def get_engine(url: str | None = None) -> Engine:
    """Create configured SQLAlchemy engine with SQLite pragmas."""
    db_url = normalize_database_url(url or settings.database_url)
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 5.0})

    # Postgres (e.g. Neon): small pool, verify connections that may have been dropped while idle.
    return create_engine(
        db_url,
        # Neon's pooled endpoint is PgBouncer in transaction mode: don't rely on server-side prepared statements
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=300,
    )


def normalize_database_url(url: str) -> str:
    """Map plain postgres:// URLs (as Neon and Render print them) to the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode, foreign keys, and busy timeout for SQLite connections."""
    import sqlite3

    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    with contextlib.suppress(Exception):
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for scoped transactional database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
