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
    db_url = url or settings.database_url
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False, "timeout": 5.0}

    engine = create_engine(db_url, connect_args=connect_args)
    return engine


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode, foreign keys, and busy timeout for SQLite connections."""
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
