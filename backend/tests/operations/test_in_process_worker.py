"""Tests for in-process background worker daemon and job recovery."""
import os
import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import JobKind, JobState
from app.db.models import JobModel, SourceRecordModel, WorkspaceModel
from app.db.session import get_db
from app.main import app
from app.services.jobs import acquire_next_job, create_job, recover_stuck_jobs
from app.settings import Settings, settings


def test_settings_run_worker_in_process_defaults():
    """Verify run_worker_in_process defaults based on environment."""
    # Production defaults to True
    prod_s = Settings(
        app_env="production",
        secret_key="a" * 32,
        auth_mode="accounts",
    )
    assert prod_s.run_worker_in_process is True

    # Test/Dev defaults to False
    test_s = Settings(app_env="test")
    assert test_s.run_worker_in_process is False

    dev_s = Settings(app_env="development")
    assert dev_s.run_worker_in_process is False

    # Explicit override is preserved
    explicit_s = Settings(
        app_env="production",
        secret_key="a" * 32,
        auth_mode="accounts",
        run_worker_in_process=False,
    )
    assert explicit_s.run_worker_in_process is False


def test_recover_stuck_jobs(db_session: Session):
    """Jobs left in RUNNING state recover back to QUEUED on startup."""
    ws = WorkspaceModel(title="Recovery WS", created_by="tester")
    db_session.add(ws)
    db_session.commit()

    job1 = create_job(
        db=db_session,
        workspace_id=ws.id,
        kind=JobKind.IMPORT_RECORDS,
        request_key="stuck-key-1",
        payload={"search_execution_ids": []},
    )
    job1.state = JobState.RUNNING.value
    job1.lease_owner = "dead-worker-pid-999"
    job1.lease_until = datetime.now(UTC) + timedelta(minutes=10)
    job1.stage = "importing_records"
    db_session.commit()

    recovered_count = recover_stuck_jobs(db_session)
    assert recovered_count == 1

    db_session.refresh(job1)
    assert job1.state == JobState.QUEUED.value
    assert job1.lease_owner is None
    assert job1.lease_until is None
    assert job1.stage == "queued"


def test_acquire_next_job_reclaims_expired_lease(db_session: Session):
    """Running jobs with expired lease are re-acquired safely."""
    ws = WorkspaceModel(title="Lease WS", created_by="tester")
    db_session.add(ws)
    db_session.commit()

    job = create_job(
        db=db_session,
        workspace_id=ws.id,
        kind=JobKind.IMPORT_RECORDS,
        request_key="expired-key-1",
        payload={"search_execution_ids": []},
    )
    job.state = JobState.RUNNING.value
    job.lease_owner = "crashed-worker"
    job.lease_until = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    claimed = acquire_next_job(db_session, worker_id="new-worker", lease_seconds=60)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.lease_owner == "new-worker"
    assert claimed.state == JobState.RUNNING.value


def test_in_process_worker_executes_queued_import(db_session: Session, monkeypatch):
    """With RUN_WORKER_IN_PROCESS=true, queued import jobs complete via background worker."""
    monkeypatch.setattr(settings, "run_worker_in_process", True)
    monkeypatch.setattr(settings, "source_mode", "fixture")

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as tc:
            # 1. Create workspace
            ws_res = tc.post("/api/v1/workspaces", json={"title": "Worker Test WS", "description": "Testing in-process worker"})
            assert ws_res.status_code == 201
            ws_id = ws_res.json()["id"]

            # 2. Create criteria
            crit_payload = {
                "question": "Metformin and HbA1c in T2D?",
                "pico_description": {},
                "criteria": [
                    {
                        "id": "c1",
                        "name": "Adults",
                        "category": "population",
                        "is_inclusion": True,
                        "rationale": "Adult population",
                    }
                ],
            }
            crit_res = tc.post(f"/api/v1/workspaces/{ws_id}/criteria", json=crit_payload)
            assert crit_res.status_code == 201
            crit_id = crit_res.json()["id"]

            # 3. Create query
            q_payload = {
                "ast": {"term": "metformin"},
                "sources": ["pubmed"],
                "criteria_version_id": crit_id,
            }
            q_res = tc.post(f"/api/v1/workspaces/{ws_id}/queries", json=q_payload)
            assert q_res.status_code == 201
            q_id = q_res.json()["id"]

            # 4. Search count
            s_res = tc.post(f"/api/v1/queries/{q_id}/searches", json={"source": "pubmed", "cap": 10})
            assert s_res.status_code == 202
            exec_id = s_res.json()["id"]

            # 5. Trigger import
            import_payload = {
                "search_execution_ids": [exec_id],
                "cap": 5,
                "idempotency_key": "in-proc-worker-test-key-1",
            }
            import_res = tc.post(f"/api/v1/workspaces/{ws_id}/imports", json=import_payload)
            assert import_res.status_code == 202
            job_id = import_res.json()["id"]
            assert import_res.json()["state"] == "queued"

            # 6. Poll job status until worker completes it (timeout 10s)
            start_time = time.time()
            final_job_data = None
            while time.time() - start_time < 10.0:
                poll_res = tc.get(f"/api/v1/jobs/{job_id}")
                assert poll_res.status_code == 200
                final_job_data = poll_res.json()
                if final_job_data["state"] in ("succeeded", "failed"):
                    break
                time.sleep(0.2)

            assert final_job_data is not None
            assert final_job_data["state"] == "succeeded"
            assert final_job_data["progress"] == 1.0
            assert final_job_data["processed_items"] > 0

            # 7. Check source records persisted
            recs = db_session.query(SourceRecordModel).filter_by(workspace_id=ws_id).all()
            assert len(recs) > 0
    finally:
        app.dependency_overrides.clear()


def test_in_process_worker_warns_when_workers_gt_one(db_session: Session, monkeypatch, caplog):
    """When WORKERS > 1 and in-process worker is active, log a warning."""
    monkeypatch.setattr(settings, "run_worker_in_process", True)
    monkeypatch.setenv("WORKERS", "3")

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with caplog.at_level("WARNING"):
            with TestClient(app) as tc:
                res = tc.get("/health/live")
                assert res.status_code == 200
        assert any("WORKERS is set to 3" in record.message for record in caplog.records)
    finally:
        app.dependency_overrides.clear()
