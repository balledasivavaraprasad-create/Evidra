"""CI-only integration test server for Evidra Level 1 Systematic Literature Review.

Strictly refuses to start unless APP_ENV=test and SOURCE_MODE=fixture.
Creates an isolated disposable SQLite database, seeds synthetic SLR benchmark records,
and serves the API on 127.0.0.1:8000 with background worker daemon.
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import tempfile
import threading
from pathlib import Path

import uvicorn
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


# 1. Enforce strict environment guards
def verify_test_environment() -> None:
    app_env = os.environ.get("APP_ENV", "").lower()
    source_mode = os.environ.get("SOURCE_MODE", "").lower()

    if app_env != "test":
        sys.stderr.write(
            f"FATAL: backend/app/testing/serve.py refuses to start with APP_ENV='{app_env}'. "
            "Must be strictly 'test'.\n"
        )
        sys.exit(1)

    if source_mode != "fixture":
        sys.stderr.write(
            f"FATAL: backend/app/testing/serve.py refuses to start with SOURCE_MODE='{source_mode}'. "
            "Must be strictly 'fixture'.\n"
        )
        sys.exit(1)


verify_test_environment()

backend_root = Path(__file__).resolve().parents[2]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.models import Base
from app.db.session import get_db
from app.demo_data import seed_synthetic_slr_workspace
from app.main import app
from app.settings import settings

logger = logging.getLogger("app.testing.serve")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def run_test_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Launch the disposable test environment, API server, and worker daemon."""
    tmp_dir = tempfile.mkdtemp(prefix="evidra-e2e-")
    db_file = Path(tmp_dir) / "test_review.sqlite"
    db_url = f"sqlite:///{db_file}"
    logger.info("Disposable SQLite database initialized at: %s", db_file)

    settings.database_url = db_url
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Seed initial test data
    with TestingSession() as seed_session:
        seed_synthetic_slr_workspace(seed_session)

    # Start background worker thread
    stop_worker_event = threading.Event()

    def worker_thread():
        logger.info("Test worker daemon running...")
        while not stop_worker_event.is_set():
            try:
                with TestingSession() as worker_session:
                    from app.worker import poll_and_execute_next
                    poll_and_execute_next("e2e-worker", db=worker_session)
            except Exception as e:  # noqa: BLE001
                logger.error("Error in test worker: %s", e)
            stop_worker_event.wait(0.5)

    t_worker = threading.Thread(target=worker_thread, daemon=True)
    t_worker.start()

    # Configure and start uvicorn
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)

    def handle_exit(sig, frame):
        logger.info("Shutdown signal received (%s), terminating test server...", sig)
        stop_worker_event.set()
        server.should_exit = True

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    logger.info("Evidra test server listening at http://%s:%d", host, port)
    server.run()
    logger.info("Evidra test server exited cleanly.")


if __name__ == "__main__":
    run_test_server()
