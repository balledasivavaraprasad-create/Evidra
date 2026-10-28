import os
import socket
import sys
from collections.abc import Generator
from pathlib import Path

# Ensure test flags are set immediately
os.environ["APP_ENV"] = "test"
os.environ["CI_OFFLINE"] = "true"
os.environ["SOURCE_MODE"] = "fixture"

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.settings import settings

settings.app_env = "test"
settings.ci_offline = True
settings.source_mode = "fixture"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import *
from app.db.session import Base, get_db
from app.main import app


# Default offline guard: block external network access during tests
@pytest.fixture(autouse=True, scope="session")
def enforce_offline_testing():
    """Ensure tests run strictly offline without leaking external HTTP requests."""
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0]
        # Allow loopback connections only
        if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
            return orig_connect(self, address)
        raise RuntimeError(f"Network access blocked in test suite: attempted connection to {host}")

    socket.socket.connect = guarded_connect
    yield
    socket.socket.connect = orig_connect


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
_pg_engine = None


def _postgres_engine():
    """One shared Postgres engine per test run; schema is rebuilt once, rows truncated per test."""
    global _pg_engine
    if _pg_engine is None:
        _pg_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        Base.metadata.drop_all(bind=_pg_engine)
        Base.metadata.create_all(bind=_pg_engine)
    return _pg_engine


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a fresh database session: in-memory SQLite by default, Postgres if TEST_DATABASE_URL is set."""
    if TEST_DATABASE_URL.startswith("postgresql"):
        engine = _postgres_engine()
        session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        try:
            yield session
        finally:
            session.rollback()
            session.close()
            tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            with engine.begin() as conn:
                conn.exec_driver_sql(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")
        return

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client wired to isolated in-memory test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
