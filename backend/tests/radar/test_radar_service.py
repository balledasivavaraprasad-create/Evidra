"""Unit tests for Missing-Evidence Radar domain service and status derivation."""
import hashlib
import json
import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    EffectiveDecisionState,
    EvidenceClaimType,
    EvidenceProvenance,
    EvidenceSemanticAssessment,
    EvidenceValidationStatus,
    RadarEvidenceStatus,
    RadarHumanReviewStatus,
    SourceNamespace,
)
from app.contracts.models import (
    RadarConfirmRequest,
    RadarCorrectRequest,
    RadarFlagConflictRequest,
    RadarFlagUncertainRequest,
)
from app.db.models import (
    CriteriaVersionModel,
    EvidencePassportModel,
    GroupMemberModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.radar import (
    confirm_radar_field,
    correct_radar_field,
    derive_radar_status,
    flag_conflict_radar_field,
    flag_uncertain_radar_field,
    get_or_sync_article_radar,
    get_review_level_radar,
    revalidate_radar_field,
)


@pytest.fixture
def radar_test_setup(db_session: Session):
    """Seed test workspace, criteria, source records, and paper groups."""
    ws = WorkspaceModel(created_by="test-researcher", id="ws-radar-unit", title="PICO Radar Unit Review")
    crit = CriteriaVersionModel(
        id="crit-radar-1",
        workspace_id=ws.id,
        sequence=1,
        question="PICO efficacy question",
        pico_json=json.dumps({"p": "patients", "i": "intervention", "c": "comparator", "o": "outcome"}),
        criteria_json=json.dumps({"inclusion": ["RCTs"], "exclusion": []}),
        content_hash="crit-hash-radar",
    )
    db_session.add_all([ws, crit])
    db_session.flush()
    return ws, crit


def _seed_paper_group_with_evidence(
    db: Session,
    workspace_id: str,
    external_id: str,
    title: str,
    abstract_text: str | None,
    decision: str = "include",
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
        authors_json=json.dumps(["Author A", "Author B"]),
        year=2024,
        journal="Journal of Clinical Review",
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

    # Human screening decision
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
        actor_id="lead-reviewer",
        event_type=DecisionEventType.SCREEN_DECISION.value,
        payload_json=json.dumps({"status": decision, "decision": decision, "notes": "Criteria satisfied"}),
    )
    db.add(event)
    db.commit()

    return group, rev


def test_derive_radar_status_logic():
    """Verify deterministic radar status derivation rules."""
    # 1. Supported
    st1 = derive_radar_status(
        claim_type="population",
        claim_value="adults with diabetes",
        supporting_quote="adults with diabetes",
        validation_status=EvidenceValidationStatus.VERIFIED.value,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
        is_contradictory=False,
        uncertainty_note=None,
        has_source_text=True,
    )
    assert st1 == RadarEvidenceStatus.SUPPORTED

    # 2. Uncertain due to ambiguity note
    st2 = derive_radar_status(
        claim_type="intervention",
        claim_value="metformin",
        supporting_quote="metformin",
        validation_status=EvidenceValidationStatus.VERIFIED.value,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
        is_contradictory=False,
        uncertainty_note="Dose and duration unstated",
        has_source_text=True,
    )
    assert st2 == RadarEvidenceStatus.UNCERTAIN

    # 3. Not found in examined text
    st3 = derive_radar_status(
        claim_type="comparator",
        claim_value="Not found in examined text",
        supporting_quote="",
        validation_status=EvidenceValidationStatus.INSUFFICIENT_EVIDENCE.value,
        semantic_assessment=EvidenceSemanticAssessment.INSUFFICIENT.value,
        is_contradictory=False,
        uncertainty_note=None,
        has_source_text=True,
    )
    assert st3 == RadarEvidenceStatus.NOT_FOUND

    # 4. Conflicting evidence
    st4 = derive_radar_status(
        claim_type="outcome",
        claim_value="mortality reduced",
        supporting_quote="mortality reduced",
        validation_status=EvidenceValidationStatus.VERIFIED.value,
        semantic_assessment=EvidenceSemanticAssessment.CONTRADICTS.value,
        is_contradictory=True,
        uncertainty_note="Conflicting table in text",
        has_source_text=True,
    )
    assert st4 == RadarEvidenceStatus.CONFLICTING

    # 5. Stale evidence (text changed)
    st5 = derive_radar_status(
        claim_type="population",
        claim_value="children",
        supporting_quote="children",
        validation_status=EvidenceValidationStatus.STALE.value,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
        is_contradictory=False,
        uncertainty_note=None,
        has_source_text=True,
    )
    assert st5 == RadarEvidenceStatus.STALE

    # 6. Not assessed (No source text available to examine)
    st6 = derive_radar_status(
        claim_type="population",
        claim_value="children",
        supporting_quote="",
        validation_status=EvidenceValidationStatus.MISSING_SOURCE.value,
        semantic_assessment=EvidenceSemanticAssessment.UNASSESSED.value,
        is_contradictory=False,
        uncertainty_note=None,
        has_source_text=False,
    )
    assert st6 == RadarEvidenceStatus.NOT_ASSESSED


def test_article_radar_generation_and_decision_preservation(db_session: Session, radar_test_setup):
    """Test article radar preserves screening decision even when comparator is not found."""
    ws, _ = radar_test_setup
    abstract = (
        "We tested CRISPR gene therapy in 50 children with sickle cell anemia. "
        "The primary outcome was complete resolution of crises. "
        "No control group or active comparator was included."
    )
    group, rev = _seed_paper_group_with_evidence(
        db_session, ws.id, "PMID_TEST_1", "CRISPR Trial", abstract, decision="include"
    )

    radar = get_or_sync_article_radar(db_session, ws.id, group.id)

    # Invariant: Decision remains INCLUDE
    assert radar.effective_decision == EffectiveDecisionState.INCLUDE
    assert radar.has_source_text is True

    # Check 4 dimensions
    assert "population" in radar.pico
    assert "intervention" in radar.pico
    assert "comparator" in radar.pico
    assert "outcome" in radar.pico

    # Population and intervention should be found
    pop = radar.pico["population"]
    assert pop.field_label == "Population"

    # Comparator should be not_found in examined text
    comp = radar.pico["comparator"]
    assert comp.radar_status == RadarEvidenceStatus.NOT_FOUND
    assert "Not found in examined text" in comp.claim_value

    # Overall coverage is calculated
    assert 0 <= radar.overall_coverage_pct <= 100


def test_article_without_source_text(db_session: Session, radar_test_setup):
    """Test article without abstract is marked NOT_ASSESSED rather than false not-found."""
    ws, _ = radar_test_setup
    group, _ = _seed_paper_group_with_evidence(
        db_session, ws.id, "PMID_NO_TEXT", "Title Only Paper", abstract_text=None, decision="maybe"
    )

    radar = get_or_sync_article_radar(db_session, ws.id, group.id)

    assert radar.has_source_text is False
    assert radar.effective_decision == EffectiveDecisionState.MAYBE

    # Invariant: Empty text cannot establish that evidence is missing
    for _, field in radar.pico.items():
        assert field.radar_status == RadarEvidenceStatus.NOT_ASSESSED


def test_human_review_actions(db_session: Session, radar_test_setup):
    """Test confirming, correcting, flagging uncertainty, and flagging conflicts."""
    ws, _ = radar_test_setup
    abstract = "Clinical study of 100 oncology patients receiving immunotherapy."
    group, rev = _seed_paper_group_with_evidence(
        db_session, ws.id, "PMID_ACTIONS", "Immunotherapy Trial", abstract, decision="include"
    )

    # 1. Confirm Population
    res1 = confirm_radar_field(
        db_session,
        ws.id,
        group.id,
        field_type="population",
        payload=RadarConfirmRequest(actor_id="reviewer-1", notes="Verified by human"),
    )
    pop = res1.pico["population"]
    assert pop.human_review_status == RadarHumanReviewStatus.CONFIRMED
    assert pop.radar_status == RadarEvidenceStatus.SUPPORTED

    # Invariant: Screening decision still INCLUDE!
    assert res1.effective_decision == EffectiveDecisionState.INCLUDE

    # 2. Correct Intervention
    res2 = correct_radar_field(
        db_session,
        ws.id,
        group.id,
        field_type="intervention",
        payload=RadarCorrectRequest(
            claim_value="Pembrolizumab 200mg IV",
            reason="Specific agent identified in study methods",
            actor_id="reviewer-1",
        ),
    )
    interv = res2.pico["intervention"]
    assert interv.human_review_status == RadarHumanReviewStatus.CORRECTED
    assert interv.claim_value == "Pembrolizumab 200mg IV"
    assert interv.reviewer_correction_reason == "Specific agent identified in study methods"

    # 3. Flag Uncertain on Outcome
    res3 = flag_uncertain_radar_field(
        db_session,
        ws.id,
        group.id,
        field_type="outcome",
        payload=RadarFlagUncertainRequest(
            uncertainty_note="Endpoints are exploratory and unvalidated surrogate markers",
            actor_id="reviewer-1",
        ),
    )
    outc = res3.pico["outcome"]
    assert outc.radar_status == RadarEvidenceStatus.UNCERTAIN
    assert "exploratory" in (outc.uncertainty_note or "")

    # 4. Flag Conflict on Comparator
    res4 = flag_conflict_radar_field(
        db_session,
        ws.id,
        group.id,
        field_type="comparator",
        payload=RadarFlagConflictRequest(
            conflict_explanation="Cohort A had placebo, but Cohort B had standard chemo",
            actor_id="reviewer-1",
        ),
    )
    comp = res4.pico["comparator"]
    assert comp.radar_status == RadarEvidenceStatus.CONFLICTING
    assert comp.is_contradictory is True


def test_review_level_dashboard_metrics(db_session: Session, radar_test_setup):
    """Test dashboard aggregation across multiple papers with correct denominators."""
    ws, _ = radar_test_setup

    # Paper 1: Fully described abstract
    _seed_paper_group_with_evidence(
        db_session,
        ws.id,
        "P1",
        "Trial 1",
        "Patients with asthma given albuterol versus placebo. Outcome was FEV1 increase.",
    )

    # Paper 2: Missing comparator
    _seed_paper_group_with_evidence(
        db_session,
        ws.id,
        "P2",
        "Trial 2",
        "Asthma cohort given budesonide. Outcome was peak flow.",
    )

    # Paper 3: Title only (No text)
    _seed_paper_group_with_evidence(
        db_session,
        ws.id,
        "P3",
        "Trial 3 No Abstract",
        abstract_text=None,
    )

    overview = get_review_level_radar(db_session, ws.id)

    assert overview.total_articles == 3
    assert overview.articles_with_source_text == 2
    assert overview.articles_without_source_text == 1
    assert len(overview.rows) == 3

    # Check dimension summaries
    pop_sum = overview.dimension_summaries["population"]
    assert pop_sum.total_assessed >= 2
    assert pop_sum.not_assessed_count == 1  # Paper 3 has no text

    comp_sum = overview.dimension_summaries["comparator"]
    assert comp_sum.not_assessed_count == 1
