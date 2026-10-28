"""Evidence Passport domain service: auditable evidence claims, deterministic quote validation, and human overrides."""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    EvidenceClaimType,
    EvidenceProvenance,
    EvidenceSemanticAssessment,
    EvidenceValidationStatus,
    PicoLabel,
)
from app.contracts.models import (
    EvidenceCorrectionRequest,
    EvidenceCoverageResponse,
    EvidenceItemCreateRequest,
    EvidenceItemResponse,
    EvidencePassportBundle,
    EvidencePassportSummary,
    EvidenceRevalidateResponse,
    PicoResult,
    ScreenResult,
)
from app.db.models import (
    EvidencePassportModel,
    GroupMemberModel,
    GroupSnapshotModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
)
from app.pico.validator import compute_text_hash

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def find_quote_occurrences(text: str, quote: str) -> list[tuple[int, int]]:
    """Find all start and end code-point offsets where quote appears in text."""
    matches: list[tuple[int, int]] = []
    if not quote or not text:
        return matches
    start = 0
    while True:
        idx = text.find(quote, start)
        if idx == -1:
            break
        matches.append((idx, idx + len(quote)))
        start = idx + 1
    return matches


def validate_quote_against_source(
    quote: str,
    start_cp: int | None,
    end_cp: int | None,
    source_text: str | None,
    stored_fingerprint: str | None,
    claim_type: EvidenceClaimType | str,
    claim_value: str,
) -> tuple[EvidenceValidationStatus, str, int | None, int | None]:
    """Deterministically validate an evidence quotation against stored source text.

    Distinguishes structural text presence from logical semantic support.
    Never marks semantic support as verified; returns status and code-point offsets.
    """
    if source_text is None or len(source_text.strip()) == 0:
        return (
            EvidenceValidationStatus.MISSING_SOURCE,
            "Required source text is unavailable or empty in stored record revision.",
            start_cp,
            end_cp,
        )

    current_fingerprint = compute_text_hash(source_text)
    is_stale = stored_fingerprint is not None and stored_fingerprint != current_fingerprint

    # Handle explicit absent comparator or empty quote
    if not quote or len(quote.strip()) == 0:
        if (
            (claim_type == EvidenceClaimType.COMPARATOR or claim_type == "comparator")
            and "not found" in claim_value.lower()
        ):
            return (
                EvidenceValidationStatus.INSUFFICIENT_EVIDENCE,
                "No active comparator or control group reported in available abstract.",
                None,
                None,
            )
        return (
            EvidenceValidationStatus.INSUFFICIENT_EVIDENCE,
            "No supporting quotation passage supplied for this claim.",
            None,
            None,
        )

    text_len = len(source_text)
    occurrences = find_quote_occurrences(source_text, quote)

    if not occurrences:
        return (
            EvidenceValidationStatus.MISMATCHED,
            "Quotation does not exist in current stored source text.",
            start_cp,
            end_cp,
        )

    # Check if supplied offsets match an exact slice
    if (
        start_cp is not None
        and end_cp is not None
        and 0 <= start_cp < end_cp <= text_len
        and source_text[start_cp:end_cp] == quote
    ):
        if is_stale:
            return (
                EvidenceValidationStatus.STALE,
                "Source text fingerprint changed since extraction, though quotation still matches slice.",
                start_cp,
                end_cp,
            )
        return (
            EvidenceValidationStatus.VERIFIED,
            "Exact quotation and code-point offsets verified against source text.",
            start_cp,
            end_cp,
        )

    # If offsets missing or shifted, attempt unambiguous re-anchoring
    if len(occurrences) == 1:
        resolved_start, resolved_end = occurrences[0]
        if is_stale:
            return (
                EvidenceValidationStatus.STALE,
                f"Source text fingerprint changed; quotation re-anchored to single match at [{resolved_start}:{resolved_end}).",
                resolved_start,
                resolved_end,
            )
        return (
            EvidenceValidationStatus.VERIFIED,
            f"Exact quotation verified in source text; offsets anchored to single match at [{resolved_start}:{resolved_end}).",
            resolved_start,
            resolved_end,
        )

    # Ambiguous: multiple matches found in source text and provided offsets don't match
    return (
        EvidenceValidationStatus.NEEDS_REVIEW,
        f"Quotation appears {len(occurrences)} times in source text; offsets require human review to resolve ambiguity.",
        start_cp,
        end_cp,
    )


def parse_evidence_provenance(raw: str) -> EvidenceProvenance:
    """Safely map raw provenance strings (e.g. 'rule:v1.0', 'llm:v1') to EvidenceProvenance enum."""
    try:
        return EvidenceProvenance(raw)
    except ValueError:
        raw_lower = raw.lower()
        if raw_lower.startswith("rule:") or "deterministic" in raw_lower:
            return EvidenceProvenance.DETERMINISTIC_EXTRACTION
        if raw_lower.startswith("llm:") or "model" in raw_lower:
            return EvidenceProvenance.MODEL_GENERATED
        if raw_lower.startswith("human:") or "override" in raw_lower:
            return EvidenceProvenance.HUMAN_CORRECTED
        if "import" in raw_lower:
            return EvidenceProvenance.IMPORTED_ANNOTATION
        return EvidenceProvenance.DETERMINISTIC_EXTRACTION


def model_to_item_response(model: EvidencePassportModel) -> EvidenceItemResponse:
    """Convert ORM model to EvidenceItemResponse contract."""
    return EvidenceItemResponse(
        id=model.id,
        workspace_id=model.workspace_id,
        paper_group_id=model.paper_group_id,
        record_revision_id=model.record_revision_id,
        claim_type=EvidenceClaimType(model.claim_type),
        claim_value=model.claim_value,
        original_claim_value=model.original_claim_value,
        source_field=model.source_field,
        supporting_quote=model.supporting_quote,
        start_cp=model.start_cp,
        end_cp=model.end_cp,
        source_fingerprint=model.source_fingerprint,
        provenance=parse_evidence_provenance(model.provenance),
        validation_status=EvidenceValidationStatus(model.validation_status),
        validation_message=model.validation_message,
        semantic_assessment=EvidenceSemanticAssessment(model.semantic_assessment),
        assessed_by=model.assessed_by,
        is_contradictory=model.is_contradictory,
        uncertainty_note=model.uncertainty_note,
        reviewer_correction_reason=model.reviewer_correction_reason,
        event_id=model.event_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def compute_summary_metrics(items: list[EvidenceItemResponse]) -> EvidencePassportSummary:
    """Compute aggregate validation and transparency statistics."""
    pico_categories_seen = set()
    verified_count = 0
    needs_review_count = 0
    stale_count = 0
    mismatched_count = 0
    missing_source_count = 0
    human_corrected = 0
    contradictory = 0

    pico_types = {
        EvidenceClaimType.POPULATION,
        EvidenceClaimType.INTERVENTION,
        EvidenceClaimType.COMPARATOR,
        EvidenceClaimType.OUTCOME,
    }

    for item in items:
        if item.validation_status == EvidenceValidationStatus.VERIFIED:
            verified_count += 1
            if item.claim_type in pico_types:
                pico_categories_seen.add(item.claim_type)
        elif item.validation_status == EvidenceValidationStatus.NEEDS_REVIEW:
            needs_review_count += 1
        elif item.validation_status == EvidenceValidationStatus.STALE:
            stale_count += 1
        elif item.validation_status == EvidenceValidationStatus.MISMATCHED:
            mismatched_count += 1
        elif item.validation_status == EvidenceValidationStatus.MISSING_SOURCE:
            missing_source_count += 1

        if item.provenance == EvidenceProvenance.HUMAN_CORRECTED:
            human_corrected += 1
        if item.is_contradictory or item.semantic_assessment == EvidenceSemanticAssessment.CONTRADICTS:
            contradictory += 1

    return EvidencePassportSummary(
        total_claims=len(items),
        verified_quotes_count=verified_count,
        needs_review_count=needs_review_count,
        stale_count=stale_count,
        mismatched_count=mismatched_count,
        missing_source_count=missing_source_count,
        pico_fields_with_evidence=len(pico_categories_seen),
        human_corrected_count=human_corrected,
        contradictory_count=contradictory,
    )


def generate_or_sync_passport_for_record(
    db: Session,
    workspace_id: str,
    group_id: str | None,
    record_revision: RecordRevisionModel,
    screen_result: ScreenResult | None,
    pico_result: PicoResult | None,
) -> list[EvidencePassportModel]:
    """Generate or update Evidence Passport claims from screening and PICO results.

    Preserves any existing human corrections and approved annotations.
    Deterministic quotation validation runs automatically against stored text.
    """
    abstract_text = record_revision.abstract_text or ""
    source_fingerprint = record_revision.content_hash

    # 1. Load existing items for this record revision
    existing_models = (
        db.query(EvidencePassportModel)
        .filter_by(workspace_id=workspace_id, record_revision_id=record_revision.id)
        .all()
    )
    existing_by_key: dict[tuple[str, str], EvidencePassportModel] = {}
    for em in existing_models:
        existing_by_key[(em.claim_type, em.claim_value)] = em

    new_items_to_add: list[EvidencePassportModel] = []

    # 2. Extract PICO claims from PicoResult
    label_to_claim_type = {
        PicoLabel.P: EvidenceClaimType.POPULATION,
        PicoLabel.I: EvidenceClaimType.INTERVENTION,
        PicoLabel.C: EvidenceClaimType.COMPARATOR,
        PicoLabel.O: EvidenceClaimType.OUTCOME,
    }

    pico_spans_present = set()
    if pico_result and pico_result.spans:
        for span in pico_result.spans:
            claim_type = label_to_claim_type.get(span.label, EvidenceClaimType.STUDY_CHARACTERISTIC)
            pico_spans_present.add(span.label)
            key = (claim_type.value, span.quote)

            # Preserve human corrected item if already present
            if key in existing_by_key:
                existing_item = existing_by_key[key]
                if existing_item.provenance == EvidenceProvenance.HUMAN_CORRECTED.value:
                    continue

            status_val, msg, s_cp, e_cp = validate_quote_against_source(
                quote=span.quote,
                start_cp=span.start_cp,
                end_cp=span.end_cp,
                source_text=abstract_text,
                stored_fingerprint=source_fingerprint,
                claim_type=claim_type,
                claim_value=span.quote,
            )

            if key in existing_by_key:
                m = existing_by_key[key]
                m.start_cp = s_cp
                m.end_cp = e_cp
                m.validation_status = status_val.value
                m.validation_message = msg
                m.paper_group_id = group_id
                m.updated_at = utc_now()
            else:
                m = EvidencePassportModel(
                    workspace_id=workspace_id,
                    paper_group_id=group_id,
                    record_revision_id=record_revision.id,
                    claim_type=claim_type.value,
                    claim_value=span.quote,
                    original_claim_value=span.quote,
                    source_field="abstract",
                    supporting_quote=span.quote,
                    start_cp=s_cp,
                    end_cp=e_cp,
                    source_fingerprint=source_fingerprint,
                    provenance=span.provenance or EvidenceProvenance.DETERMINISTIC_EXTRACTION.value,
                    validation_status=status_val.value,
                    validation_message=msg,
                    semantic_assessment=EvidenceSemanticAssessment.UNASSESSED.value,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                new_items_to_add.append(m)
                existing_by_key[key] = m

    # If comparator is missing, explicitly record absent comparator evidence
    if pico_result and not pico_result.has_comparator and PicoLabel.C not in pico_spans_present:
        comp_key = (EvidenceClaimType.COMPARATOR.value, "Not found in abstract")
        if comp_key not in existing_by_key:
            m = EvidencePassportModel(
                workspace_id=workspace_id,
                paper_group_id=group_id,
                record_revision_id=record_revision.id,
                claim_type=EvidenceClaimType.COMPARATOR.value,
                claim_value="Not found in abstract",
                original_claim_value="Not found in abstract",
                source_field="abstract",
                supporting_quote="",
                start_cp=None,
                end_cp=None,
                source_fingerprint=source_fingerprint,
                provenance=EvidenceProvenance.DETERMINISTIC_EXTRACTION.value,
                validation_status=EvidenceValidationStatus.INSUFFICIENT_EVIDENCE.value,
                validation_message="No active comparator or control group reported in abstract text.",
                semantic_assessment=EvidenceSemanticAssessment.INSUFFICIENT.value,
                uncertainty_note="No active comparator found; requires human review if protocol specifies one.",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            new_items_to_add.append(m)
            existing_by_key[comp_key] = m

    # 3. Extract Screening Rationale claims from ScreenResult
    if screen_result:
        # Top-level screening verdict claim
        verdict_str = f"Eligibility: {screen_result.status.value.upper()}"
        if screen_result.reasons:
            verdict_str += f" ({', '.join(screen_result.reasons)})"

        # Criterion-level evidence passages
        for crit in screen_result.criteria_evidence:
            snippet = crit.evidence_snippet or crit.explanation
            crit_claim = f"{crit.name} [{crit.verdict.value.upper()}]: {crit.reason_code}"
            key = (EvidenceClaimType.SCREENING_RATIONALE.value, crit_claim)

            if key in existing_by_key and existing_by_key[key].provenance == EvidenceProvenance.HUMAN_CORRECTED.value:
                continue

            status_val, msg, s_cp, e_cp = validate_quote_against_source(
                quote=snippet,
                start_cp=None,
                end_cp=None,
                source_text=abstract_text,
                stored_fingerprint=source_fingerprint,
                claim_type=EvidenceClaimType.SCREENING_RATIONALE,
                claim_value=crit_claim,
            )

            if key in existing_by_key:
                m = existing_by_key[key]
                m.supporting_quote = snippet
                m.start_cp = s_cp
                m.end_cp = e_cp
                m.validation_status = status_val.value
                m.validation_message = msg
                m.paper_group_id = group_id
                m.updated_at = utc_now()
            else:
                m = EvidencePassportModel(
                    workspace_id=workspace_id,
                    paper_group_id=group_id,
                    record_revision_id=record_revision.id,
                    claim_type=EvidenceClaimType.SCREENING_RATIONALE.value,
                    claim_value=crit_claim,
                    original_claim_value=crit_claim,
                    source_field="abstract",
                    supporting_quote=snippet,
                    start_cp=s_cp,
                    end_cp=e_cp,
                    source_fingerprint=source_fingerprint,
                    provenance=f"rule:{screen_result.method_version}",
                    validation_status=status_val.value,
                    validation_message=msg,
                    semantic_assessment=EvidenceSemanticAssessment.UNASSESSED.value,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                new_items_to_add.append(m)
                existing_by_key[key] = m

    for item in new_items_to_add:
        db.add(item)
    db.commit()

    return list(existing_by_key.values())


def get_paper_group_evidence_bundle(
    db: Session,
    workspace_id: str,
    group_id: str,
) -> EvidencePassportBundle:
    """Retrieve complete Evidence Passport bundle for a paper group."""
    group = db.query(PaperGroupModel).filter_by(id=group_id, workspace_id=workspace_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found in workspace '{workspace_id}'",
        )

    # Find representative revision
    rep_rev: RecordRevisionModel | None = None
    snap = db.query(GroupSnapshotModel).filter_by(group_id=group_id).first()
    if snap:
        rep_rev = db.query(RecordRevisionModel).filter_by(id=snap.representative_revision_id).first()

    if not rep_rev:
        first_member = db.query(GroupMemberModel).filter_by(group_id=group_id).first()
        if first_member:
            rep_rev = (
                db.query(RecordRevisionModel)
                .filter_by(source_record_id=first_member.source_record_id)
                .order_by(RecordRevisionModel.fetched_at.desc())
                .first()
            )

    if not rep_rev:
        # Fallback to evidence item record revision
        first_ev = db.query(EvidencePassportModel).filter_by(paper_group_id=group_id).first()
        if first_ev:
            rep_rev = db.query(RecordRevisionModel).filter_by(id=first_ev.record_revision_id).first()

    if not rep_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored text revision found for paper group '{group_id}'",
        )

    # Query all evidence passport items for this group or revision
    models = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            (EvidencePassportModel.paper_group_id == group_id)
            | (EvidencePassportModel.record_revision_id == rep_rev.id),
        )
        .order_by(EvidencePassportModel.created_at.asc())
        .all()
    )

    items = [model_to_item_response(m) for m in models]
    summary = compute_summary_metrics(items)

    return EvidencePassportBundle(
        workspace_id=workspace_id,
        group_id=group_id,
        record_revision_id=rep_rev.id,
        title=rep_rev.title,
        abstract_text=rep_rev.abstract_text,
        source_fingerprint=rep_rev.content_hash,
        summary=summary,
        items=items,
    )


def apply_reviewer_correction(
    db: Session,
    workspace_id: str,
    evidence_id: str,
    payload: EvidenceCorrectionRequest,
) -> EvidenceItemResponse:
    """Submit human correction for an evidence-backed claim with persistent audit preservation.

    Never trusts client verification flags; validates updated quotes deterministically on backend.
    Preserves original AI claim and records append-only review audit event.
    """
    item = (
        db.query(EvidencePassportModel)
        .filter_by(id=evidence_id, workspace_id=workspace_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence passport item '{evidence_id}' not found in workspace",
        )

    rec_rev = db.query(RecordRevisionModel).filter_by(id=item.record_revision_id).first()
    if not rec_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Underlying record revision not found for evidence item",
        )

    # Preserve initial AI claim value if first human correction
    if item.original_claim_value is None:
        item.original_claim_value = item.claim_value

    quote_to_validate = payload.supporting_quote if payload.supporting_quote is not None else item.supporting_quote

    status_val, msg, s_cp, e_cp = validate_quote_against_source(
        quote=quote_to_validate,
        start_cp=payload.start_cp if payload.start_cp is not None else item.start_cp,
        end_cp=payload.end_cp if payload.end_cp is not None else item.end_cp,
        source_text=rec_rev.abstract_text,
        stored_fingerprint=rec_rev.content_hash,
        claim_type=item.claim_type,
        claim_value=payload.claim_value,
    )

    # Record append-only review event
    next_seq = (
        db.query(ReviewEventModel)
        .filter_by(workspace_id=workspace_id)
        .count()
        + 1
    )

    audit_payload = {
        "evidence_id": item.id,
        "previous_claim": item.claim_value,
        "new_claim": payload.claim_value,
        "previous_quote": item.supporting_quote,
        "new_quote": quote_to_validate,
        "semantic_assessment": payload.semantic_assessment.value,
        "validation_status": status_val.value,
        "reason": payload.reason,
    }

    event = ReviewEventModel(
        workspace_id=workspace_id,
        group_id=item.paper_group_id or "ungrouped",
        sequence=next_seq,
        event_type=DecisionEventType.EVIDENCE_CORRECTION.value,
        payload_json=json.dumps(audit_payload),
        actor_id=payload.actor_id,
        reason=payload.reason,
        created_at=utc_now(),
    )
    db.add(event)
    db.flush()

    # Update evidence passport record
    item.claim_value = payload.claim_value
    item.supporting_quote = quote_to_validate
    item.start_cp = s_cp
    item.end_cp = e_cp
    item.source_fingerprint = rec_rev.content_hash
    item.provenance = EvidenceProvenance.HUMAN_CORRECTED.value
    item.validation_status = status_val.value
    item.validation_message = msg
    item.semantic_assessment = payload.semantic_assessment.value
    item.assessed_by = f"human:{payload.actor_id}"
    item.is_contradictory = (payload.semantic_assessment == EvidenceSemanticAssessment.CONTRADICTS)
    item.reviewer_correction_reason = payload.reason
    item.event_id = event.id
    item.updated_at = utc_now()

    db.commit()
    db.refresh(item)

    return model_to_item_response(item)


def create_manual_evidence_item(
    db: Session,
    workspace_id: str,
    group_id: str | None,
    payload: EvidenceItemCreateRequest,
) -> EvidenceItemResponse:
    """Create a new human or imported evidence claim bound to stored source text."""
    rec_rev = db.query(RecordRevisionModel).filter_by(id=payload.record_revision_id).first()
    if not rec_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record revision '{payload.record_revision_id}' not found",
        )

    source_text = rec_rev.abstract_text if payload.source_field == "abstract" else rec_rev.title
    status_val, msg, s_cp, e_cp = validate_quote_against_source(
        quote=payload.supporting_quote,
        start_cp=payload.start_cp,
        end_cp=payload.end_cp,
        source_text=source_text,
        stored_fingerprint=rec_rev.content_hash,
        claim_type=payload.claim_type,
        claim_value=payload.claim_value,
    )

    item = EvidencePassportModel(
        workspace_id=workspace_id,
        paper_group_id=group_id,
        record_revision_id=payload.record_revision_id,
        claim_type=payload.claim_type.value,
        claim_value=payload.claim_value,
        original_claim_value=payload.claim_value,
        source_field=payload.source_field,
        supporting_quote=payload.supporting_quote,
        start_cp=s_cp,
        end_cp=e_cp,
        source_fingerprint=rec_rev.content_hash,
        provenance=EvidenceProvenance.HUMAN_CREATED.value,
        validation_status=status_val.value,
        validation_message=msg,
        semantic_assessment=payload.semantic_assessment.value,
        assessed_by=f"human:{payload.actor_id}" if payload.actor_id else None,
        is_contradictory=(payload.semantic_assessment == EvidenceSemanticAssessment.CONTRADICTS),
        uncertainty_note=payload.uncertainty_note,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return model_to_item_response(item)


def revalidate_group_evidence(
    db: Session,
    workspace_id: str,
    group_id: str,
) -> EvidenceRevalidateResponse:
    """Deterministically revalidate all evidence claims for a paper group against current source text."""
    items = (
        db.query(EvidencePassportModel)
        .filter_by(workspace_id=workspace_id, paper_group_id=group_id)
        .all()
    )

    verified = 0
    stale = 0
    mismatched = 0
    needs_review = 0

    for item in items:
        rec_rev = db.query(RecordRevisionModel).filter_by(id=item.record_revision_id).first()
        source_text = rec_rev.abstract_text if rec_rev and item.source_field == "abstract" else (rec_rev.title if rec_rev else None)

        status_val, msg, s_cp, e_cp = validate_quote_against_source(
            quote=item.supporting_quote,
            start_cp=item.start_cp,
            end_cp=item.end_cp,
            source_text=source_text,
            stored_fingerprint=item.source_fingerprint,
            claim_type=item.claim_type,
            claim_value=item.claim_value,
        )

        item.validation_status = status_val.value
        item.validation_message = msg
        item.start_cp = s_cp
        item.end_cp = e_cp
        item.updated_at = utc_now()

        if status_val == EvidenceValidationStatus.VERIFIED:
            verified += 1
        elif status_val == EvidenceValidationStatus.STALE:
            stale += 1
        elif status_val == EvidenceValidationStatus.MISMATCHED:
            mismatched += 1
        else:
            needs_review += 1

    db.commit()

    return EvidenceRevalidateResponse(
        items_revalidated=len(items),
        verified_count=verified,
        stale_count=stale,
        mismatched_count=mismatched,
        needs_review_count=needs_review,
    )


def get_workspace_evidence_coverage(
    db: Session,
    workspace_id: str,
    total_papers_count: int | None = None,
) -> EvidenceCoverageResponse:
    """Calculate review-wide evidence transparency and coverage metrics."""
    items = (
        db.query(EvidencePassportModel)
        .filter_by(workspace_id=workspace_id)
        .all()
    )

    if total_papers_count is None:
        total_papers_count = (
            db.query(PaperGroupModel)
            .filter_by(workspace_id=workspace_id)
            .count()
        )

    verified_claims = 0
    stale_claims = 0
    mismatched_claims = 0
    human_corrections = 0

    papers_with_verified: set[str] = set()
    papers_needing_review: set[str] = set()
    pico_categories_by_paper: dict[str, set[str]] = {}

    pico_types = {"population", "intervention", "comparator", "outcome"}

    for it in items:
        paper_id = it.paper_group_id or it.record_revision_id
        if it.validation_status == EvidenceValidationStatus.VERIFIED.value:
            verified_claims += 1
            papers_with_verified.add(paper_id)
            if it.claim_type in pico_types:
                pico_categories_by_paper.setdefault(paper_id, set()).add(it.claim_type)
        elif it.validation_status in {
            EvidenceValidationStatus.NEEDS_REVIEW.value,
            EvidenceValidationStatus.STALE.value,
            EvidenceValidationStatus.MISMATCHED.value,
        }:
            papers_needing_review.add(paper_id)

        if it.validation_status == EvidenceValidationStatus.STALE.value:
            stale_claims += 1
        elif it.validation_status == EvidenceValidationStatus.MISMATCHED.value:
            mismatched_claims += 1

        if it.provenance == EvidenceProvenance.HUMAN_CORRECTED.value:
            human_corrections += 1

    # Average PICO coverage across papers (each paper has 4 potential PICO slots)
    total_pico_slots = max(1, total_papers_count * 4)
    filled_pico_slots = sum(len(cats) for cats in pico_categories_by_paper.values())
    pico_pct = round((filled_pico_slots / total_pico_slots) * 100.0, 1)

    return EvidenceCoverageResponse(
        workspace_id=workspace_id,
        total_papers=total_papers_count,
        papers_with_verified_evidence=len(papers_with_verified),
        papers_needing_review=len(papers_needing_review),
        total_claims=len(items),
        verified_claims=verified_claims,
        stale_claims=stale_claims,
        mismatched_claims=mismatched_claims,
        pico_evidence_coverage_percent=pico_pct,
        human_corrections_count=human_corrections,
    )


def sanitize_csv_cell(value: Any) -> str:
    """Sanitize cell against CSV formula injection attacks (=, +, -, @, tab, cr)."""
    if value is None:
        return ""
    s = str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


def export_evidence_passport_csv(
    db: Session,
    workspace_id: str,
) -> str:
    """Generate formula-injection safe CSV export of workspace evidence passports."""
    items = (
        db.query(EvidencePassportModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(EvidencePassportModel.created_at.asc())
        .all()
    )

    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "evidence_id",
        "paper_group_id",
        "record_revision_id",
        "claim_type",
        "claim_value",
        "original_claim_value",
        "source_field",
        "supporting_quote",
        "start_cp",
        "end_cp",
        "source_fingerprint",
        "validation_status",
        "semantic_assessment",
        "provenance",
        "assessed_by",
        "is_contradictory",
        "correction_reason",
        "created_at",
    ])

    for it in items:
        writer.writerow([
            sanitize_csv_cell(it.id),
            sanitize_csv_cell(it.paper_group_id),
            sanitize_csv_cell(it.record_revision_id),
            sanitize_csv_cell(it.claim_type),
            sanitize_csv_cell(it.claim_value),
            sanitize_csv_cell(it.original_claim_value),
            sanitize_csv_cell(it.source_field),
            sanitize_csv_cell(it.supporting_quote),
            sanitize_csv_cell(it.start_cp),
            sanitize_csv_cell(it.end_cp),
            sanitize_csv_cell(it.source_fingerprint),
            sanitize_csv_cell(it.validation_status),
            sanitize_csv_cell(it.semantic_assessment),
            sanitize_csv_cell(it.provenance),
            sanitize_csv_cell(it.assessed_by),
            sanitize_csv_cell(it.is_contradictory),
            sanitize_csv_cell(it.reviewer_correction_reason),
            sanitize_csv_cell(it.created_at.isoformat() if it.created_at else ""),
        ])

    return out.getvalue()
