"""Graph execution nodes calling D03 review services and human-in-the-loop review interrupts."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt
from sqlalchemy.orm import Session

from app.contracts.enums import EffectiveDecisionState
from app.db.models import WorkspaceModel
from app.db.session import SessionLocal
from app.services.corpus import list_paper_groups_in_revision, process_corpus
from app.workflows.state import ReviewGraphState

logger = logging.getLogger(__name__)


def get_node_db(config: RunnableConfig | None = None) -> tuple[Session, bool]:
    """Return a database session and a boolean indicating whether it should be closed."""
    if config:
        cfg = config.get("configurable", {})
        if "db" in cfg and cfg["db"] is not None:
            return cfg["db"], False
    return SessionLocal(), True


def validate_input_node(state: ReviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Validate workspace existence and state prerequisites."""
    ws_id = state["workspace_id"]
    db, should_close = get_node_db(config)
    try:
        ws = db.query(WorkspaceModel).filter_by(id=ws_id).first()
        if not ws:
            return {
                "error": f"Workspace '{ws_id}' not found",
                "stage": "failed",
                "trace_steps": state.get("trace_steps", []) + ["validate_input:failed"],
            }
        return {
            "stage": "validated",
            "error": None,
            "trace_steps": state.get("trace_steps", []) + ["validate_input:succeeded"],
        }
    finally:
        if should_close:
            db.close()


def process_corpus_node(state: ReviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Execute deterministic dedup, screening, and PICO extraction via D03 services."""
    if state.get("error"):
        return {}

    ws_id = state["workspace_id"]
    crit_id = state.get("criteria_version_id")
    db, should_close = get_node_db(config)
    try:
        rev = process_corpus(db=db, workspace_id=ws_id, criteria_version_id=crit_id)
        groups = list_paper_groups_in_revision(db=db, revision_id=rev.id)

        inc_count = sum(1 for g in groups if g.effective_status == EffectiveDecisionState.INCLUDE)
        exc_count = sum(1 for g in groups if g.effective_status == EffectiveDecisionState.EXCLUDE)
        unc_count = sum(
            1 for g in groups if g.effective_status in (EffectiveDecisionState.MAYBE, EffectiveDecisionState.CONFLICT)
        )

        pending_review = None
        # If there are uncertain records or conflicts, identify first group requiring human review
        first_uncertain = next(
            (g for g in groups if g.effective_status in (EffectiveDecisionState.MAYBE, EffectiveDecisionState.CONFLICT)),
            None,
        )
        if first_uncertain:
            pending_review = {
                "group_id": first_uncertain.id,
                "workspace_id": ws_id,
                "title": first_uncertain.representative_revision.title,
                "reason": "Uncertain eligibility requires reviewer confirmation",
            }

        return {
            "corpus_revision_id": rev.id,
            "group_count": rev.group_count,
            "record_count": rev.record_count,
            "included_count": inc_count,
            "excluded_count": exc_count,
            "uncertain_count": unc_count,
            "stage": "corpus_processed",
            "pending_human_review": pending_review,
            "trace_steps": state.get("trace_steps", []) + ["process_corpus:succeeded"],
        }
    except (ValueError, KeyError, RuntimeError, HTTPException) as e:
        logger.error("Error processing corpus in workflow node: %s", e)
        return {
            "error": str(e),
            "stage": "failed",
            "trace_steps": state.get("trace_steps", []) + [f"process_corpus:error:{e}"],
        }
    finally:
        if should_close:
            db.close()


def human_review_node(state: ReviewGraphState) -> dict[str, Any]:
    """Human-in-the-loop review interrupt for uncertain screening or conflict resolution."""
    if state.get("error") or not state.get("pending_human_review"):
        return {"stage": "review_skipped"}

    # Issue persistent interrupt to pause workflow execution
    interrupt_payload = state["pending_human_review"]
    response = interrupt(interrupt_payload)

    # When resumed via Command(resume=...), response contains resume payload
    approved = True
    event_id = None
    if isinstance(response, dict):
        approved = bool(response.get("approved", True))
        event_id = response.get("event_id")

    return {
        "human_approved": approved,
        "human_event_id": event_id,
        "stage": "human_reviewed",
        "pending_human_review": None,
        "trace_steps": state.get("trace_steps", []) + [f"human_review:resumed:{event_id}"],
    }


def finalize_run_node(state: ReviewGraphState) -> dict[str, Any]:
    """Finalize run status and emit observable trace summary."""
    final_stage = "completed" if not state.get("error") else "failed"
    return {
        "stage": final_stage,
        "trace_steps": state.get("trace_steps", []) + [f"finalize_run:{final_stage}"],
    }
