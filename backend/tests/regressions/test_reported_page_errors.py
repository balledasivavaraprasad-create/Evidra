"""Regression tests for two pages that showed "Internal Server Error" with the demo data.

1. Duplicates > genealogy panel: the service read ``ScreenResult.rationale``, which did not
   exist, so any group with only an automated (machine) suggestion crashed. The same lookup
   lived in the Devil's Advocate and PICO radar services.
2. Search Evolution: the service read ``PaperGroupModel.pre_screen_result_json`` (no such
   column) and looked for human decisions under a ``"decision"`` key the app never writes,
   so it crashed and, once fixed, would still have ignored reviewers' real decisions.

Both are exercised against the same synthetic workspace the demo server seeds.
"""

import json

from sqlalchemy.orm import Session

from app.contracts.enums import (
    CriterionVerdict,
    DecisionEventType,
    EffectiveDecisionState,
    EligibilityStatus,
    ScreeningEvidenceSource,
)
from app.contracts.models import CriterionEvidence, ScreenResult
from app.db.models import GroupMemberModel, ReviewEventModel
from app.demo_data import seed_synthetic_slr_workspace
from app.services.devils_advocate import get_or_generate_challenge
from app.services.genealogy import (
    get_duplicate_group_genealogy,
    get_workspace_duplicate_overview,
)
from app.services.search_evolution import list_search_versions


def _criterion(verdict: CriterionVerdict, explanation: str) -> CriterionEvidence:
    return CriterionEvidence(
        criterion_id="c1",
        name="Criterion",
        verdict=verdict,
        reason_code="CODE",
        explanation=explanation,
        source=ScreeningEvidenceSource.RULE,
        method_version="rules:test",
    )


# --------------------------------------------------------------------------
# ScreenResult.rationale
# --------------------------------------------------------------------------


def test_rationale_prefers_failed_criteria():
    res = ScreenResult(
        record_revision_id="r1",
        status=EligibilityStatus.EXCLUDE,
        reasons=["ANIMAL_STUDY_EXCLUDED"],
        criteria_evidence=[
            _criterion(CriterionVerdict.PASS, "Adults with T2D"),
            _criterion(CriterionVerdict.FAIL, "Animal-only study"),
        ],
        method_version="rules:test",
    )
    assert res.rationale == "Animal-only study"


def test_rationale_uses_uncertain_criteria_for_maybe_then_reason_codes():
    maybe = ScreenResult(
        record_revision_id="r1",
        status=EligibilityStatus.MAYBE,
        criteria_evidence=[_criterion(CriterionVerdict.UNKNOWN, "Population unclear")],
        method_version="rules:test",
    )
    assert maybe.rationale == "Population unclear"

    codes_only = ScreenResult(
        record_revision_id="r1", status=EligibilityStatus.EXCLUDE, reasons=["A", "B"], method_version="rules:test"
    )
    assert codes_only.rationale == "A, B"

    include = ScreenResult(record_revision_id="r1", status=EligibilityStatus.INCLUDE, method_version="rules:test")
    assert include.rationale is None


def test_rationale_is_not_part_of_the_api_contract():
    res = ScreenResult(record_revision_id="r1", status=EligibilityStatus.MAYBE, method_version="rules:test")
    assert "rationale" not in res.model_dump()
    assert "rationale" not in ScreenResult.model_json_schema()["properties"]


# --------------------------------------------------------------------------
# Duplicates genealogy (previously HTTP 500)
# --------------------------------------------------------------------------


def test_genealogy_loads_for_group_with_only_machine_suggestion(db_session: Session):
    ws_id = seed_synthetic_slr_workspace(db_session)
    overview = get_workspace_duplicate_overview(db=db_session, workspace_id=ws_id)
    assert overview.groups, "seeded workspace should contain a duplicate group"

    genealogy = get_duplicate_group_genealogy(db=db_session, workspace_id=ws_id, group_id=overview.groups[0].group_id)

    assert len(genealogy.members) == 2
    for member in genealogy.members:
        assert member.decision_source == "automated"
        assert member.decision_rationale  # readable text, not a crash


# --------------------------------------------------------------------------
# Search evolution (previously HTTP 500, then silently ignored human decisions)
# --------------------------------------------------------------------------


def test_search_versions_load_with_seeded_data(db_session: Session):
    ws_id = seed_synthetic_slr_workspace(db_session)
    versions = list_search_versions(db=db_session, workspace_id=ws_id)
    assert len(versions) == 1
    assert versions[0].total_records == 3
    assert versions[0].screened_records == 3


def test_search_evolution_respects_human_decision_written_by_review_queue(db_session: Session):
    ws_id = seed_synthetic_slr_workspace(db_session)
    from app.services.search_evolution import _resolve_record_screening_state

    member = db_session.query(GroupMemberModel).first()
    before, _, _ = _resolve_record_screening_state(db_session, member.source_record_id)
    assert before != EffectiveDecisionState.EXCLUDE

    # Same payload shape the review queue writes (app/services/review_decisions.py)
    db_session.add(
        ReviewEventModel(
            workspace_id=ws_id,
            group_id=member.group_id,
            sequence=999,
            event_type=DecisionEventType.SCREEN_DECISION.value,
            payload_json=json.dumps({"status": "exclude"}),
            actor_id="reviewer-1",
            reason="Animal-only study",
        )
    )
    db_session.commit()

    after, reason, _ = _resolve_record_screening_state(db_session, member.source_record_id)
    assert after == EffectiveDecisionState.EXCLUDE
    assert reason == "Animal-only study"


# --------------------------------------------------------------------------
# Devil's Advocate used the same missing attribute
# --------------------------------------------------------------------------


def test_devils_advocate_challenge_uses_machine_rationale(db_session: Session):
    ws_id = seed_synthetic_slr_workspace(db_session)
    group_id = get_workspace_duplicate_overview(db=db_session, workspace_id=ws_id).groups[0].group_id

    challenge = get_or_generate_challenge(db=db_session, workspace_id=ws_id, group_id=group_id)

    assert challenge.original_exclusion_reason  # derived from the machine suggestion
