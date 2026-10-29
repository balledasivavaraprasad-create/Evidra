"""Records derived from a processed corpus: evidence claims, the Missing-Evidence Radar and challenges.

These used to be created the first time someone opened a page (a GET that wrote to the database).
They are now created once, when the corpus is processed, and every GET only reads them.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.contracts.enums import EffectiveDecisionState
from app.db.models import RecordRevisionModel
from app.services.corpus import get_paper_group_detail, list_paper_groups_in_revision
from app.services.devils_advocate import get_or_generate_challenge
from app.services.evidence_passport import generate_or_sync_passport_for_record
from app.services.radar import get_or_sync_article_radar

logger = logging.getLogger(__name__)

PAGE = 200


def precompute_review_artifacts(db: Session, workspace_id: str, revision_id: str) -> dict[str, int]:
    """Create the evidence claims and radar for every group in the revision, and a Devil's Advocate
    challenge for each group the screening excluded. A failure on one group is logged and skipped:
    the paper is still screened, and its pages simply show what could not be prepared.
    """
    counts = {"groups": 0, "passports": 0, "radars": 0, "challenges": 0, "failed": 0}
    offset = 0
    while True:
        page = list_paper_groups_in_revision(db=db, revision_id=revision_id, limit=PAGE, offset=offset)
        if not page:
            break
        for summary in page:
            counts["groups"] += 1
            try:
                detail = get_paper_group_detail(db=db, group_id=summary.id, revision_id=revision_id)
                rep = db.get(RecordRevisionModel, detail.group.representative_revision.id)
                if rep is None:
                    continue
                generate_or_sync_passport_for_record(
                    db=db,
                    workspace_id=workspace_id,
                    group_id=summary.id,
                    record_revision=rep,
                    screen_result=detail.screen_result,
                    pico_result=detail.pico_result,
                )
                counts["passports"] += 1
                get_or_sync_article_radar(db, workspace_id, summary.id, persist=True)
                counts["radars"] += 1
                if summary.effective_status == EffectiveDecisionState.EXCLUDE:
                    get_or_generate_challenge(db, workspace_id, summary.id, persist=True)
                    counts["challenges"] += 1
            except Exception:
                db.rollback()
                counts["failed"] += 1
                logger.exception("Could not prepare evidence for group %s", summary.id)
        if len(page) < PAGE:
            break
        offset += PAGE
    return counts
