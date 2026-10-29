"""A job that hits a database error must end as failed, with a message that is safe to show."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import JobModel
from app.services.jobs import safe_error_message
from app.worker import poll_and_execute_next


def broken_flush(db: Session) -> None:
    """Leave the session in the state a failed INSERT leaves it in: it refuses work until rolled back."""
    db.add(JobModel(id="not-enough-columns"))  # NOT NULL columns missing
    db.flush()


def test_a_database_error_during_processing_fails_the_job_instead_of_leaving_it_running(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
):
    ws = client.post("/api/v1/workspaces", json={"title": "Review"}).json()
    job = client.post(f"/api/v1/workspaces/{ws['id']}/process-corpus").json()

    def explode(**kwargs):
        broken_flush(kwargs["db"])

    monkeypatch.setattr("app.workflows.pipeline.run_review_pipeline", explode)
    assert poll_and_execute_next(db=db_session)

    after = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert after["state"] == "failed", after
    assert after["error"]["code"] == "EXECUTION_ERROR"
    # the SQL and its values stay in the log, not in what a reviewer sees
    assert "INSERT" not in after["error"]["message"] and "SQL" not in after["error"]["message"]
    assert "database error" in after["error"]["message"]


def test_safe_error_message_hides_sql_but_keeps_ordinary_errors():
    class Fake(IntegrityError):
        pass

    db_error = IntegrityError("INSERT INTO t VALUES (:secret)", {"secret": "hunter2"}, Exception("constraint"))
    shown = safe_error_message(db_error)
    assert "INSERT" not in shown and "hunter2" not in shown and "database error" in shown
    assert safe_error_message(ValueError("The workspace has no records")) == "The workspace has no records"
    assert safe_error_message(RuntimeError()) == "RuntimeError"
    assert len(safe_error_message(ValueError("x" * 1000))) == 300
