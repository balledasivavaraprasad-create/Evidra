"""Unit tests for Devil's Advocate Reviewer domain service."""
import hashlib
import json
import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    ChallengeDisposition,
    ChallengeRecommendation,
    DecisionEventType,
    EffectiveDecisionState,
    EligibilityStatus,
    SourceNamespace,
    VulnerabilityFlag,
)
from app.contracts.models import (
    DevilsAdvocateDispositionRequest,
    DevilsAdvocateGenerateRequest,
)
from app.db.models import (
    CriteriaVersionModel,
    DevilsAdvocateChallengeModel,
    GroupMemberModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.corpus import project_effective_group_decision
from app.services.devils_advocate import (
    get_or_generate_challenge,
    get_workspace_challenge_dashboard,
    record_challenge_disposition,
)


@pytest.fixture
def devils_test_setup(db_session: Session):
    """Seed test workspace and criteria."""
    ws = WorkspaceModel(created_by="reviewer-1", id="ws-devils-unit", title="Devils Advocate Unit Review")
    crit = CriteriaVersionModel(
        id="crit-da-1",
        workspace_id=ws.id,
        sequence=1,
        question="Clinical trial review question",
        pico_json=json.dumps({"p": "patients", "i": "intervention", "c": "comparator", "o": "outcome"}),
        criteria_json=json.dumps({"inclusion": ["human trials"], "exclusion": []}),
        content_hash="crit-hash-da",
    )
    db_session.add_all([ws, crit])
    db_session.commit()
    return ws, crit


def _seed_excluded_paper(
    db: Session,
    workspace_id: str,
    external_id: str,
    title: str,
    abstract_text: str,
    exclusion_reason: str,
) -> tuple[PaperGroupModel, RecordRevisionModel]:
    content_hash = hashlib.sha256((abstract_text or title).encode()).hexdigest()

    rec = SourceRecordModel(
        workspace_id=workspace_id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id=external_id,
    )
    db.add(rec)
    db.flush()

    rev = RecordRevisionModel(
        source_record_id=rec.id,
        content_hash=content_hash,
        title=title,
        abstract_text=abstract_text,
        authors_json=json.dumps(["Dr. Adams", "Dr. Baker"]),
        year=2024,
        journal="Journal of Clinical Oncology",
        pmid=external_id,
    )
    db.add(rev)
    db.flush()

    group = PaperGroupModel(
        workspace_id=workspace_id,
        membership_fingerprint=f"fp-{external_id}",
    )
    db.add(group)
    db.flush()

    member = GroupMemberModel(
        group_id=group.id,
        source_record_id=rec.id,
    )
    db.add(member)

    seq = (
        db.query(func.max(ReviewEventModel.sequence))
        .filter_by(workspace_id=workspace_id)
        .scalar()
        or 0
    ) + 1

    event = ReviewEventModel(
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id="screener-lead",
        event_type=DecisionEventType.SCREEN_DECISION.value,
        payload_json=json.dumps({
            "status": "exclude",
            "decision": "exclude",
            "reason": exclusion_reason,
        }),
        reason=exclusion_reason,
    )
    db.add(event)
    db.commit()

    return group, rev


def test_challenge_generation_for_excluded_paper(db_session: Session, devils_test_setup):
    """Test Devil's Advocate challenges fragile exclusion when counter-evidence exists."""
    ws, _ = devils_test_setup
    abstract = (
        "In this multicenter randomized phase 3 trial, 120 patients with acute myeloid leukemia "
        "received targeted immunotherapy compared to standard of care control group. "
        "Complete remission was significantly improved in the treatment group."
    )
    group, _ = _seed_excluded_paper(
        db_session,
        ws.id,
        "PMID_DA_01",
        "Targeted Therapy in AML",
        abstract,
        exclusion_reason="Single arm study without active comparator",
    )

    challenge = get_or_generate_challenge(db_session, ws.id, group.id)

    # Verifications
    assert challenge.workspace_id == ws.id
    assert challenge.group_id == group.id
    assert challenge.proposed_decision == "exclude"
    assert challenge.recommendation == ChallengeRecommendation.RECONSIDER_EXCLUSION
    assert challenge.vulnerability_score >= 0.60
    assert challenge.disposition == ChallengeDisposition.PENDING

    # Counter-arguments located
    assert len(challenge.counter_arguments) >= 1
    quotes = [ca.supporting_quote for ca in challenge.counter_arguments]
    assert any("standard of care" in q.lower() or "randomized" in q.lower() for q in quotes)

    # Invariant: Generating a challenge does NOT silently overturn human decision
    eff_state, _, _, _ = project_effective_group_decision(db_session, group.id)
    assert eff_state == EffectiveDecisionState.EXCLUDE


def test_reviewer_concession_reverses_exclusion(db_session: Session, devils_test_setup):
    """Test human concession changes effective decision to maybe and appends audit event."""
    ws, _ = devils_test_setup
    abstract = (
        "We tested novel monoclonal antibody in 80 pediatric participants aged 2-12 years. "
        "Patients with refractory leukemia achieved 65% objective response."
    )
    group, _ = _seed_excluded_paper(
        db_session,
        ws.id,
        "PMID_DA_02",
        "Pediatric Monoclonal Trial",
        abstract,
        exclusion_reason="Wrong population (adult criteria)",
    )

    chal = get_or_generate_challenge(db_session, ws.id, group.id)
    assert chal.disposition == ChallengeDisposition.PENDING

    # Reviewer concedes to challenge
    updated = record_challenge_disposition(
        db_session,
        ws.id,
        group.id,
        DevilsAdvocateDispositionRequest(
            disposition=ChallengeDisposition.CONCEDED,
            notes="Pediatric cohort directly relevant to sub-question; retrieve full text.",
            actor_id="dr-senior",
            conceded_decision=EligibilityStatus.MAYBE,
        ),
    )

    assert updated.disposition == ChallengeDisposition.CONCEDED
    assert updated.disposition_by == "dr-senior"
    assert updated.disposition_notes is not None

    # Invariant: Concession explicitly updates screening decision through human action
    eff_state, latest_event, _, _ = project_effective_group_decision(db_session, group.id)
    assert eff_state == EffectiveDecisionState.MAYBE

    # Audit event recorded
    events = (
        db_session.query(ReviewEventModel)
        .filter_by(group_id=group.id)
        .order_by(ReviewEventModel.sequence.asc())
        .all()
    )
    event_types = [e.event_type for e in events]
    assert DecisionEventType.DEVILS_ADVOCATE_DISPOSITION.value in event_types
    assert DecisionEventType.SCREEN_DECISION.value in event_types


def test_reviewer_uphold_exclusion(db_session: Session, devils_test_setup):
    """Test human reviewer upholds exclusion despite challenge counter-arguments."""
    ws, _ = devils_test_setup
    abstract = "We reviewed 15 historical cases of leukemia under chemotherapy."
    group, _ = _seed_excluded_paper(
        db_session,
        ws.id,
        "PMID_DA_03",
        "Retrospective Series",
        abstract,
        exclusion_reason="Case series without prospective trial data",
    )

    get_or_generate_challenge(db_session, ws.id, group.id)

    updated = record_challenge_disposition(
        db_session,
        ws.id,
        group.id,
        DevilsAdvocateDispositionRequest(
            disposition=ChallengeDisposition.UPHELD,
            notes="Confirmed retrospective case series without prospective protocol.",
            actor_id="dr-reviewer",
        ),
    )

    assert updated.disposition == ChallengeDisposition.UPHELD
    eff_state, _, _, _ = project_effective_group_decision(db_session, group.id)
    assert eff_state == EffectiveDecisionState.EXCLUDE


def test_workspace_challenge_dashboard_aggregation(db_session: Session, devils_test_setup):
    """Test dashboard metrics calculation across multiple challenged exclusions."""
    ws, _ = devils_test_setup
    group1, _ = _seed_excluded_paper(
        db_session, ws.id, "PMID_DASH_1", "Study A",
        "Randomized controlled trial in 50 patients with standard comparator.", "No comparator"
    )
    group2, _ = _seed_excluded_paper(
        db_session, ws.id, "PMID_DASH_2", "Study B",
        "Observational cohort in 100 participants.", "irrelevant"
    )

    get_or_generate_challenge(db_session, ws.id, group1.id)
    get_or_generate_challenge(db_session, ws.id, group2.id)

    # Concede on group1
    record_challenge_disposition(
        db_session, ws.id, group1.id,
        DevilsAdvocateDispositionRequest(
            disposition=ChallengeDisposition.CONCEDED,
            conceded_decision=EligibilityStatus.INCLUDE,
            actor_id="reviewer",
        )
    )

    dash = get_workspace_challenge_dashboard(db_session, ws.id)
    assert dash.total_challenged >= 2
    assert dash.conceded_count == 1
    assert dash.false_exclusions_prevented == 1
    assert dash.concession_rate > 0.0
