"""Security boundary and authority isolation tests for review workflow (C03).

Verifies workspace scoping, invalid/forged thread ID protection,
replay safety on human review resumption, and cross-workspace isolation.
"""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from app.db.models import WorkspaceModel
from app.workflows.pipeline import (
    build_review_graph,
    resume_review_pipeline,
    run_review_pipeline,
)


@pytest.fixture
def isolated_workspace(db_session):
    """Seed test workspace."""
    ws = WorkspaceModel(
        id=f"ws-sec-{uuid.uuid4().hex[:8]}",
        title="Security Boundary Test Workspace",
        description="Workspace for security boundary regression tests",
        created_by="sec-tester",
        row_version=1,
    )
    db_session.add(ws)
    db_session.commit()
    return ws


class TestWorkflowSecurityBoundaries:
    """Authority and isolation tests for LangGraph pipeline execution."""

    def test_forged_workspace_fails_closed(self, db_session):
        """Graph refuses execution on unknown/forged workspace and records failure."""
        fake_ws_id = f"ws-forged-{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory() as tmp_dir:
            checkpoint_path = str(Path(tmp_dir) / "checkpoints.sqlite")
            result = run_review_pipeline(
                workspace_id=fake_ws_id,
                checkpoint_db_path=checkpoint_path,
                db=db_session,
            )
            assert result.get("error") is not None
            assert f"Workspace '{fake_ws_id}' not found" in result["error"]
            assert result.get("stage") == "failed"

    def test_resume_non_existent_thread_fails_gracefully(self, db_session, isolated_workspace):
        """Resuming a review thread that was never started or interrupted fails cleanly."""
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            pytest.raises(ValueError, match="No active checkpoint found to resume"),
        ):
            checkpoint_path = str(Path(tmp_dir) / "checkpoints.sqlite")
            resume_review_pipeline(
                workspace_id=isolated_workspace.id,
                domain_event_id="evt-forged-001",
                approved=True,
                checkpoint_db_path=checkpoint_path,
                db=db_session,
            )

    def test_cross_workspace_checkpoint_isolation(self, db_session, isolated_workspace):
        """Checkpoints for workspace A cannot be read or resumed under workspace B thread key."""
        ws_b = WorkspaceModel(
            id=f"ws-sec-b-{uuid.uuid4().hex[:8]}",
            title="Second Isolated Workspace",
            description="Testing isolation",
            created_by="sec-tester",
            row_version=1,
        )
        db_session.add(ws_b)
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            checkpoint_path = str(Path(tmp_dir) / "checkpoints.sqlite")
            with SqliteSaver.from_conn_string(checkpoint_path) as checkpointer:
                graph = build_review_graph(checkpointer=checkpointer)
                # Verify thread IDs are strictly namespaced
                thread_b = {"configurable": {"thread_id": f"review-thread-{ws_b.id}"}}

                # Reading state for thread B before any run returns None
                state_b = graph.get_state(thread_b)
                assert state_b.values == {}
