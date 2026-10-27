"""Durable LangGraph review orchestration tests with persistent SQLite checkpointing (C02)."""
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.workflows.pipeline import (
    resume_review_pipeline,
    run_review_pipeline,
)
from app.workflows.state import GRAPH_VERSION
from tests.integration.test_review_services import seed_test_workspace_with_records


def test_review_graph_end_to_end_with_interrupt_and_resume(db_session: Session):
    """Test full LangGraph orchestration: validation, corpus processing, interrupt, and resume from SQLite checkpoint."""
    ws_id, *_ = seed_test_workspace_with_records(db_session)

    with tempfile.TemporaryDirectory() as tmp_dir:
        checkpoint_path = str(Path(tmp_dir) / "checkpoints.sqlite")

        # 1. Execute initial review pipeline
        result = run_review_pipeline(
            workspace_id=ws_id,
            job_id="job-c02-test",
            checkpoint_db_path=checkpoint_path,
            db=db_session,
        )

        # In our seeded test data, record 3 is a rodent study with formula title which may trigger uncertain/maybe or screening
        # If there's an interrupt, __interrupt__ key is present in result
        if result.get("__interrupt__"):
            interrupt_info = result["__interrupt__"][0].value
            assert interrupt_info["workspace_id"] == ws_id
            assert "group_id" in interrupt_info

            # 2. Simulate fresh connection / process restart and resume with domain event ID
            resumed = resume_review_pipeline(
                workspace_id=ws_id,
                domain_event_id="ev-domain-12345",
                approved=True,
                checkpoint_db_path=checkpoint_path,
                db=db_session,
            )

            assert resumed["human_approved"] is True
            assert resumed["human_event_id"] == "ev-domain-12345"
            assert resumed["stage"] == "completed"
            assert resumed["graph_version"] == GRAPH_VERSION
            assert "finalize_run:completed" in resumed["trace_steps"]
        else:
            # All papers cleanly classified
            assert result["stage"] == "completed"
            assert result["corpus_revision_id"] is not None
            assert result["group_count"] >= 1


def test_review_graph_invalid_workspace_fails_visibly(db_session: Session):
    """Test that a non-existent workspace halts at validation without running effects."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        checkpoint_path = str(Path(tmp_dir) / "checkpoints.sqlite")

        result = run_review_pipeline(
            workspace_id="non-existent-workspace-id",
            checkpoint_db_path=checkpoint_path,
        )

        assert result["stage"] == "failed"
        assert "not found" in result["error"].lower()
        assert "validate_input:failed" in result["trace_steps"]


def test_review_graph_persists_interrupt_and_resumes_across_connection_reopen(db_session: Session):
    """Test interrupt persistence and resumption across SQLite connection reopen."""
    from uuid import uuid4

    from app.db.models import (
        QueryMembershipModel,
        RecordRevisionModel,
        SearchExecutionModel,
        SourceRecordModel,
    )
    from app.pico.validator import compute_text_hash

    ws_id, *_ = seed_test_workspace_with_records(db_session)

    # Add an uncertain record with no abstract to guarantee EffectiveDecisionState.MAYBE
    se = db_session.query(SearchExecutionModel).first()
    src_u = SourceRecordModel(
        id=f"src-u-{uuid4().hex[:6]}",
        workspace_id=ws_id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="999999",
    )
    db_session.add(src_u)
    db_session.flush()

    rev_u = RecordRevisionModel(
        id=f"rev-u-{uuid4().hex[:6]}",
        source_record_id=src_u.id,
        content_hash=compute_text_hash(""),
        title="Uncertain protocol without abstract",
        abstract_text=None,
        year=2024,
    )
    db_session.add(rev_u)
    db_session.flush()

    db_session.add(QueryMembershipModel(search_execution_id=se.id, source_record_id=src_u.id, record_revision_id=rev_u.id))
    db_session.commit()

    with tempfile.TemporaryDirectory() as tmp_dir:
        checkpoint_path = str(Path(tmp_dir) / "checkpoints.sqlite")

        # Step 1: Execute initial pipeline; must pause at interrupt for uncertain record
        res1 = run_review_pipeline(
            workspace_id=ws_id,
            job_id="job-interrupt-test",
            checkpoint_db_path=checkpoint_path,
            db=db_session,
        )

        assert "__interrupt__" in res1
        interrupt_val = res1["__interrupt__"][0].value
        assert interrupt_val["workspace_id"] == ws_id
        assert "group_id" in interrupt_val

        # Step 2: Fresh execution simulates process restart; resumes with human review event
        resumed = resume_review_pipeline(
            workspace_id=ws_id,
            domain_event_id="ev-human-override-99",
            approved=True,
            checkpoint_db_path=checkpoint_path,
            db=db_session,
        )

        assert resumed["human_approved"] is True
        assert resumed["human_event_id"] == "ev-human-override-99"
        assert resumed["stage"] == "completed"
        assert resumed["graph_version"] == GRAPH_VERSION
        assert "human_review:resumed:ev-human-override-99" in resumed["trace_steps"]
        assert "finalize_run:completed" in resumed["trace_steps"]
