"""Records derived from a processed corpus: evidence claims, the Missing-Evidence Radar and challenges.

These used to be created the first time someone opened a page (a GET that wrote to the database).
They are now created once, when the corpus is processed, and every GET only reads them.

Every database statement is a network round trip to a hosted database, so this loads what it needs
in a few bulk queries instead of asking per paper.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.contracts.enums import EffectiveDecisionState
from app.contracts.models import PicoResult, ScreenResult
from app.db.models import GroupSnapshotModel, MachineResultModel, RecordRevisionModel
from app.services.corpus import list_paper_groups_in_revision
from app.services.devils_advocate import get_or_generate_challenge
from app.services.evidence_passport import generate_or_sync_passport_for_record
from app.services.radar import get_or_sync_article_radar

logger = logging.getLogger(__name__)

PAGE = 200


def _latest_machine_results(db: Session, revision_id: str) -> dict[tuple[str, str], str]:
    """The newest saved output per (group, stage) for this revision, in one query."""
    rows = (
        db.query(MachineResultModel.group_id, MachineResultModel.stage, MachineResultModel.output_json)
        .filter(MachineResultModel.corpus_revision_id == revision_id)
        .order_by(MachineResultModel.created_at.asc())
        .all()
    )
    return {(group_id, stage): output for group_id, stage, output in rows}


def _parse(model, raw: str | None):
    if not raw:
        return None
    try:
        return model.model_validate(json.loads(raw))
    except (ValueError, TypeError):
        return None


def precompute_review_artifacts(db: Session, workspace_id: str, revision_id: str) -> dict[str, int]:
    """Create the evidence claims for every group in the revision, and for each group the screening
    excluded, its Missing-Evidence Radar status and a Devil's Advocate challenge. A failure on one
    group is logged and skipped: the paper is still screened, and its pages show what is available.
    """
    counts = {"groups": 0, "passports": 0, "radars": 0, "challenges": 0, "failed": 0}

    summaries = []
    offset = 0
    while True:
        page = list_paper_groups_in_revision(db=db, revision_id=revision_id, limit=PAGE, offset=offset)
        summaries.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE

    snapshots = {
        s.group_id: s.representative_revision_id
        for s in db.query(GroupSnapshotModel).filter(GroupSnapshotModel.corpus_revision_id == revision_id).all()
    }
    revisions = {
        r.id: r
        for r in db.query(RecordRevisionModel).filter(RecordRevisionModel.id.in_(set(snapshots.values()) or {""})).all()
    }
    machine = _latest_machine_results(db, revision_id)

    for summary in summaries:
        counts["groups"] += 1
        rep = revisions.get(snapshots.get(summary.id, ""))
        if rep is None:
            continue
        try:
            generate_or_sync_passport_for_record(
                db=db,
                workspace_id=workspace_id,
                group_id=summary.id,
                record_revision=rep,
                screen_result=_parse(ScreenResult, machine.get((summary.id, "screening"))),
                pico_result=_parse(PicoResult, machine.get((summary.id, "pico"))),
            )
            counts["passports"] += 1
            if summary.effective_status == EffectiveDecisionState.EXCLUDE:
                # The challenge weighs the radar's status, so only excluded papers need it saved
                get_or_sync_article_radar(db, workspace_id, summary.id, persist=True)
                counts["radars"] += 1
                get_or_generate_challenge(db, workspace_id, summary.id, persist=True)
                counts["challenges"] += 1
        except Exception:
            db.rollback()
            counts["failed"] += 1
            logger.exception("Could not prepare evidence for group %s", summary.id)
    return counts
