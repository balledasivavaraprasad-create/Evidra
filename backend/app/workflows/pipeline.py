"""Durable LangGraph pipeline builder and execution facade for review orchestration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.workflows.nodes import (
    finalize_run_node,
    human_review_node,
    process_corpus_node,
    validate_input_node,
)
from app.workflows.state import GRAPH_VERSION, ReviewGraphState

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_DIR = Path("backend/data/checkpoints")


def route_after_validation(state: ReviewGraphState) -> str:
    """Route to process_corpus if valid, or finalize_run if error."""
    if state.get("error"):
        return "finalize_run"
    return "process_corpus"


def route_after_corpus_processing(state: ReviewGraphState) -> str:
    """Route to human_review if review is required, otherwise finalize."""
    if state.get("error"):
        return "finalize_run"
    if state.get("pending_human_review"):
        return "human_review"
    return "finalize_run"


def build_review_graph(checkpointer: SqliteSaver | None = None):
    """Build and compile the durable Review orchestration StateGraph."""
    builder = StateGraph(ReviewGraphState)

    builder.add_node("validate_input", validate_input_node)
    builder.add_node("process_corpus", process_corpus_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("finalize_run", finalize_run_node)

    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {"process_corpus": "process_corpus", "finalize_run": "finalize_run"},
    )
    builder.add_conditional_edges(
        "process_corpus",
        route_after_corpus_processing,
        {"human_review": "human_review", "finalize_run": "finalize_run"},
    )
    builder.add_edge("human_review", "finalize_run")
    builder.add_edge("finalize_run", END)

    if checkpointer:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


def run_review_pipeline(
    workspace_id: str,
    job_id: str | None = None,
    criteria_version_id: str | None = None,
    checkpoint_db_path: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Execute review orchestration graph with persistent SQLite checkpointing.

    Uses locked, durable SQLite checkpointing and namespaced thread ID.
    """
    db_path = checkpoint_db_path
    if not db_path:
        DEFAULT_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        db_path = str(DEFAULT_CHECKPOINT_DIR / "review_checkpoints.sqlite")

    thread_id = f"review-thread-{workspace_id}"
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if db is not None:
        configurable["db"] = db
    config = {"configurable": configurable}

    initial_state: ReviewGraphState = {
        "workspace_id": workspace_id,
        "job_id": job_id,
        "criteria_version_id": criteria_version_id,
        "corpus_revision_id": None,
        "group_count": 0,
        "record_count": 0,
        "included_count": 0,
        "excluded_count": 0,
        "uncertain_count": 0,
        "stage": "starting",
        "pending_human_review": None,
        "human_approved": False,
        "human_event_id": None,
        "error": None,
        "trace_steps": ["start"],
        "graph_version": GRAPH_VERSION,
    }

    with SqliteSaver.from_conn_string(db_path) as saver:
        graph = build_review_graph(checkpointer=saver)
        result = graph.invoke(initial_state, config=config)
        return result


def resume_review_pipeline(
    workspace_id: str,
    domain_event_id: str,
    approved: bool = True,
    checkpoint_db_path: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Resume an interrupted review graph after human review event is recorded."""
    db_path = checkpoint_db_path
    if not db_path:
        DEFAULT_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        db_path = str(DEFAULT_CHECKPOINT_DIR / "review_checkpoints.sqlite")

    thread_id = f"review-thread-{workspace_id}"
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if db is not None:
        configurable["db"] = db
    config = {"configurable": configurable}

    with SqliteSaver.from_conn_string(db_path) as saver:
        graph = build_review_graph(checkpointer=saver)
        current_state = graph.get_state(config)
        if not current_state or not current_state.values or not current_state.next:
            raise ValueError(
                f"No active checkpoint found to resume for workspace '{workspace_id}' (thread '{thread_id}')"
            )

        # Resume command payload passed into the interrupt
        resume_payload = {
            "approved": approved,
            "event_id": domain_event_id,
        }
        result = graph.invoke(Command(resume=resume_payload), config=config)
        return result
