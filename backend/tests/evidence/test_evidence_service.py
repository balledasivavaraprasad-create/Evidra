"""Service and integration tests for Evidence Passport data operations, auditability, and exports."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.contracts.enums import (
    CriterionVerdict,
    EligibilityStatus,
    EvidenceClaimType,
    EvidenceProvenance,
    EvidenceSemanticAssessment,
    EvidenceValidationStatus,
    PicoLabel,
    ScreeningEvidenceSource,
)
from app.contracts.models import (
    CriterionEvidence,
    EvidenceCorrectionRequest,
    PicoResult,
    PicoSpan,
    ScreenResult,
)
from app.db.models import (
    EvidencePassportModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.pico.validator import compute_text_hash
from app.services.evidence_passport import (
    apply_reviewer_correction,
    export_evidence_passport_csv,
    generate_or_sync_passport_for_record,
    get_paper_group_evidence_bundle,
    sanitize_csv_cell,
)


@pytest.fixture
def evidence_test_env(db_session: Session):
    """Seed workspace, source record, and record revision for evidence testing."""
    ws = WorkspaceModel(title="Evidence Review WS", created_by="tester")
    db_session.add(ws)
    db_session.commit()

    src_rec = SourceRecordModel(
        workspace_id=ws.id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="PMID12345",
    )
    db_session.add(src_rec)
    db_session.commit()

    abstract = (
        "Adult outpatients with major depression were randomized to sertraline 50mg daily or placebo. "
        "Primary outcome was HAM-D total score reduction at 8 weeks. "
        "Response rate was 65% for sertraline versus 35% for placebo."
    )
    chash = compute_text_hash(abstract)

    rec_rev = RecordRevisionModel(
        source_record_id=src_rec.id,
        content_hash=chash,
        title="Sertraline vs Placebo for Depression",
        abstract_text=abstract,
    )
    db_session.add(rec_rev)
    db_session.commit()

    group = PaperGroupModel(
        workspace_id=ws.id,
        membership_fingerprint=f"mfp-{rec_rev.id}",
    )
    db_session.add(group)
    db_session.commit()

    from app.db.models import GroupMemberModel
    db_session.add(GroupMemberModel(group_id=group.id, source_record_id=src_rec.id))
    db_session.commit()

    return {
        "workspace": ws,
        "source_record": src_rec,
        "record_revision": rec_rev,
        "group": group,
        "abstract": abstract,
        "content_hash": chash,
    }


def test_passport_generation_from_pico_and_screening(db_session: Session, evidence_test_env):
    env = evidence_test_env
    rec_rev = env["record_revision"]
    abstract = env["abstract"]

    # Build PICO result
    p_quote = "Adult outpatients with major depression"
    p_start = abstract.find(p_quote)
    p_end = p_start + len(p_quote)

    i_quote = "sertraline 50mg daily"
    i_start = abstract.find(i_quote)
    i_end = i_start + len(i_quote)

    pico_res = PicoResult(
        record_revision_id=rec_rev.id,
        content_hash=rec_rev.content_hash,
        spans=[
            PicoSpan(label=PicoLabel.P, start_cp=p_start, end_cp=p_end, quote=p_quote, provenance="rule:v1.0"),
            PicoSpan(label=PicoLabel.I, start_cp=i_start, end_cp=i_end, quote=i_quote, provenance="rule:v1.0"),
        ],
        has_population=True,
        has_intervention=True,
        has_comparator=False,
        has_outcome=False,
        method_version="test_extractor:v1.0",
    )

    # Build Screening result
    screen_res = ScreenResult(
        record_revision_id=rec_rev.id,
        status=EligibilityStatus.MAYBE,
        reasons=[],
        criteria_evidence=[
            CriterionEvidence(
                criterion_id="population_adults",
                name="Adult Humans Only",
                verdict=CriterionVerdict.PASS,
                reason_code="ADULT_COHORT_PRESENT",
                explanation="Study reports adult cohort.",
                evidence_snippet=p_quote,
                source=ScreeningEvidenceSource.RULE,
                method_version="test_screener:v1.0",
            )
        ],
        method_version="test_screener:v1.0",
    )

    items = generate_or_sync_passport_for_record(
        db=db_session,
        workspace_id=env["workspace"].id,
        group_id=env["group"].id,
        record_revision=rec_rev,
        screen_result=screen_res,
        pico_result=pico_res,
    )

    # Verified population, intervention, absent comparator, and screening evidence
    claim_types = [it.claim_type for it in items]
    assert EvidenceClaimType.POPULATION.value in claim_types
    assert EvidenceClaimType.INTERVENTION.value in claim_types
    assert EvidenceClaimType.COMPARATOR.value in claim_types
    assert EvidenceClaimType.SCREENING_RATIONALE.value in claim_types

    # Bundle retrieval check
    bundle = get_paper_group_evidence_bundle(db_session, env["workspace"].id, env["group"].id)
    assert bundle.summary.total_claims >= 4
    assert bundle.summary.verified_quotes_count >= 2
    assert bundle.summary.pico_fields_with_evidence >= 2


def test_reviewer_correction_preserves_original_ai_claim(db_session: Session, evidence_test_env):
    env = evidence_test_env
    rec_rev = env["record_revision"]
    env["abstract"]

    # Create initial AI item
    item = EvidencePassportModel(
        workspace_id=env["workspace"].id,
        paper_group_id=env["group"].id,
        record_revision_id=rec_rev.id,
        claim_type=EvidenceClaimType.POPULATION.value,
        claim_value="Adult outpatients with depression",
        original_claim_value="Adult outpatients with depression",
        source_field="abstract",
        supporting_quote="Adult outpatients with major depression",
        start_cp=0,
        end_cp=40,
        source_fingerprint=rec_rev.content_hash,
        provenance=EvidenceProvenance.MODEL_GENERATED.value,
        validation_status=EvidenceValidationStatus.VERIFIED.value,
        semantic_assessment=EvidenceSemanticAssessment.UNASSESSED.value,
    )
    db_session.add(item)
    db_session.commit()

    # Reviewer corrects the claim
    updated_quote = "Adult outpatients with major depression were randomized"
    corr_req = EvidenceCorrectionRequest(
        claim_value="Major depressive disorder adult outpatients",
        supporting_quote=updated_quote,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS,
        reason="Refined clinical diagnostic terminology and expanded quote slice.",
        actor_id="dr_reviewer",
    )

    updated_res = apply_reviewer_correction(
        db=db_session,
        workspace_id=env["workspace"].id,
        evidence_id=item.id,
        payload=corr_req,
    )

    assert updated_res.claim_value == "Major depressive disorder adult outpatients"
    assert updated_res.original_claim_value == "Adult outpatients with depression"
    assert updated_res.provenance == EvidenceProvenance.HUMAN_CORRECTED
    assert updated_res.semantic_assessment == EvidenceSemanticAssessment.SUPPORTS
    assert updated_res.assessed_by == "human:dr_reviewer"
    assert updated_res.reviewer_correction_reason == corr_req.reason
    assert updated_res.validation_status == EvidenceValidationStatus.VERIFIED

    # Verify audit event was logged
    event = (
        db_session.query(ReviewEventModel)
        .filter_by(workspace_id=env["workspace"].id, event_type="evidence_correction")
        .first()
    )
    assert event is not None
    assert event.actor_id == "dr_reviewer"
    assert "Major depressive disorder" in event.payload_json


def test_reextraction_does_not_overwrite_human_correction(db_session: Session, evidence_test_env):
    env = evidence_test_env
    rec_rev = env["record_revision"]

    # Pre-existing human corrected claim
    human_item = EvidencePassportModel(
        workspace_id=env["workspace"].id,
        paper_group_id=env["group"].id,
        record_revision_id=rec_rev.id,
        claim_type=EvidenceClaimType.INTERVENTION.value,
        claim_value="Sertraline 50mg hydrochloride",
        original_claim_value="Sertraline",
        source_field="abstract",
        supporting_quote="sertraline 50mg daily",
        source_fingerprint=rec_rev.content_hash,
        provenance=EvidenceProvenance.HUMAN_CORRECTED.value,
        validation_status=EvidenceValidationStatus.VERIFIED.value,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
        reviewer_correction_reason="Clarified salt formulation",
    )
    db_session.add(human_item)
    db_session.commit()

    # Rerun extraction with new spans
    pico_res = PicoResult(
        record_revision_id=rec_rev.id,
        content_hash=rec_rev.content_hash,
        spans=[
            PicoSpan(
                label=PicoLabel.I,
                start_cp=env["abstract"].find("sertraline 50mg daily"),
                end_cp=env["abstract"].find("sertraline 50mg daily") + len("sertraline 50mg daily"),
                quote="sertraline 50mg daily",
                provenance="rule:v2.0",
            )
        ],
        has_intervention=True,
        method_version="v2.0",
    )

    generate_or_sync_passport_for_record(
        db=db_session,
        workspace_id=env["workspace"].id,
        group_id=env["group"].id,
        record_revision=rec_rev,
        screen_result=None,
        pico_result=pico_res,
    )

    db_session.refresh(human_item)
    assert human_item.claim_value == "Sertraline 50mg hydrochloride"
    assert human_item.provenance == EvidenceProvenance.HUMAN_CORRECTED.value
    assert human_item.reviewer_correction_reason == "Clarified salt formulation"


def test_csv_export_protects_against_formula_injection(db_session: Session, evidence_test_env):
    env = evidence_test_env

    # Malicious injection attempt in claim value
    malicious_item = EvidencePassportModel(
        workspace_id=env["workspace"].id,
        paper_group_id=env["group"].id,
        record_revision_id=env["record_revision"].id,
        claim_type=EvidenceClaimType.OUTCOME.value,
        claim_value="=cmd|'/C calc'!A0",
        original_claim_value="=cmd|'/C calc'!A0",
        source_field="abstract",
        supporting_quote="@SUM(1+1)",
        source_fingerprint=env["content_hash"],
        provenance=EvidenceProvenance.HUMAN_CREATED.value,
        validation_status=EvidenceValidationStatus.NEEDS_REVIEW.value,
        semantic_assessment=EvidenceSemanticAssessment.UNASSESSED.value,
    )
    db_session.add(malicious_item)
    db_session.commit()

    csv_output = export_evidence_passport_csv(db_session, env["workspace"].id)
    # Cells starting with = or @ must be prefixed with ' to neutralize execution
    assert "'=cmd|'/C calc'!A0" in csv_output
    assert "'@SUM(1+1)" in csv_output


def test_sanitize_csv_cell_neutralizes_all_dangerous_prefixes():
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+44123") == "'+44123"
    assert sanitize_csv_cell("-10") == "'-10"
    assert sanitize_csv_cell("@SUM") == "'@SUM"
    assert sanitize_csv_cell("\tTab") == "'\tTab"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    assert sanitize_csv_cell(None) == ""
