"""CI-only integration test server for Evidra Level 1 Systematic Literature Review.

Strictly refuses to start unless APP_ENV=test and SOURCE_MODE=fixture.
Creates an isolated disposable SQLite database, seeds synthetic SLR benchmark records,
and serves the API on 127.0.0.1:8000 with background worker daemon.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import tempfile
import threading
from pathlib import Path

import uvicorn
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


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

from app.db.models import (
    Base,
    CriteriaVersionModel,
    QueryMembershipModel,
    QueryVersionModel,
    RecordRevisionModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.db.session import get_db
from app.main import app
from app.pico.validator import compute_text_hash
from app.services.corpus import process_corpus
from app.settings import settings

logger = logging.getLogger("app.testing.serve")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def seed_synthetic_slr_workspace(db: Session) -> str:
    """Seed synthetic Level 1 Systematic Literature Review benchmark into the test database."""
    ws_id = "ws-synth-001"
    logger.info("Seeding synthetic SLR workspace '%s'...", ws_id)

    ws = WorkspaceModel(
        id=ws_id,
        title="Type 2 Diabetes Metformin SLR",
        description="HbA1c review in adults comparing metformin against placebo",
        created_by="reviewer-alice",
        row_version=1,
    )
    db.add(ws)
    db.flush()

    crit = CriteriaVersionModel(
        id="crit-synth-001",
        workspace_id=ws_id,
        sequence=1,
        question="In adults with type 2 diabetes, how does metformin affect HbA1c?",
        pico_json=json.dumps({"P": "Adults with T2D", "I": "Metformin", "C": "Placebo", "O": "HbA1c"}),
        criteria_json=json.dumps(
            [
                {
                    "id": "crit-human",
                    "name": "Human adult population",
                    "category": "population",
                    "is_inclusion": True,
                    "rationale": "Must study human adults",
                    "metadata_first": True,
                },
                {
                    "id": "crit-animal",
                    "name": "Preclinical animal model",
                    "category": "population",
                    "is_inclusion": False,
                    "rationale": "Exclude rodent and non-human models",
                    "metadata_first": False,
                },
            ]
        ),
        content_hash="crit-hash-synth-001",
    )
    db.add(crit)
    db.flush()

    qv = QueryVersionModel(
        id="qv-synth-001",
        workspace_id=ws_id,
        sequence=1,
        ast_json=json.dumps({"field": "ALL", "value": "metformin"}),
        sources_json=json.dumps(["pubmed", "europepmc"]),
        criteria_version_id=crit.id,
        content_hash="query-hash-synth-001",
    )
    db.add(qv)
    db.flush()

    se = SearchExecutionModel(
        id="se-synth-001",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="metformin",
        synonym_setting=False,
        hit_count=3,
        status="succeeded",
        partial=False,
    )
    db.add(se)
    db.flush()

    # Record 1: Included RCT
    t1 = "Metformin improves glycemic control in adult patients with type 2 diabetes: a randomized controlled trial."
    a1 = (
        "Objective: Evaluate oral metformin versus placebo in adults with type 2 diabetes. "
        "Methods: 150 patients received metformin 1000mg daily. Results: HbA1c decreased significantly. "
        "Conclusion: Metformin is effective."
    )
    src1 = SourceRecordModel(
        id="src-synth-001",
        workspace_id=ws_id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="38100001",
    )
    db.add(src1)
    db.flush()
    rev1 = RecordRevisionModel(
        id="rev-synth-001",
        source_record_id=src1.id,
        content_hash=compute_text_hash(a1),
        title=t1,
        abstract_text=a1,
        year=2023,
        journal="Diabetes Care",
        doi="10.1001/dc.2023.01",
        pmid="38100001",
        publication_types_json=json.dumps(["Randomized Controlled Trial"]),
    )
    db.add(rev1)
    db.flush()

    # Record 2: Duplicate of Record 1 (same paper from Europe PMC with matching DOI)
    src2 = SourceRecordModel(
        id="src-synth-002",
        workspace_id=ws_id,
        source="europepmc",
        source_namespace="europepmc",
        external_id="PMC1099901",
    )
    db.add(src2)
    db.flush()
    rev2 = RecordRevisionModel(
        id="rev-synth-002",
        source_record_id=src2.id,
        content_hash=compute_text_hash(a1),
        title=t1,
        abstract_text=a1,
        year=2023,
        journal="Diabetes Care",
        doi="10.1001/dc.2023.01",
        pmid="38100001",
    )
    db.add(rev2)
    db.flush()

    # Record 3: Rodent preclinical study (excluded by animal rule)
    t3 = "Effect of metformin on hepatic gluconeogenesis in Sprague-Dawley rats."
    a3 = "We administered metformin to male Wistar rats to measure hepatic glucose production in vivo."
    src3 = SourceRecordModel(
        id="src-synth-003",
        workspace_id=ws_id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="38100003",
    )
    db.add(src3)
    db.flush()
    rev3 = RecordRevisionModel(
        id="rev-synth-003",
        source_record_id=src3.id,
        content_hash=compute_text_hash(a3),
        title=t3,
        abstract_text=a3,
        year=2022,
        journal="Biochem Pharmacol",
        pmid="38100003",
    )
    db.add(rev3)
    db.flush()

    db.add(QueryMembershipModel(search_execution_id=se.id, source_record_id=src1.id, record_revision_id=rev1.id))
    db.add(QueryMembershipModel(search_execution_id=se.id, source_record_id=src2.id, record_revision_id=rev2.id))
    db.add(QueryMembershipModel(search_execution_id=se.id, source_record_id=src3.id, record_revision_id=rev3.id))
    db.commit()

    # Run deterministic process_corpus to generate initial revision & paper groups
    logger.info("Computing initial corpus revision and deduplication groups...")
    rev = process_corpus(db=db, workspace_id=ws_id, criteria_version_id=crit.id)
    logger.info("Initial corpus revision created: '%s' (groups=%d)", rev.id, rev.group_count)
    return ws_id


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
