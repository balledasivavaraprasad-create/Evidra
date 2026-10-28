"""Missing-Evidence Radar domain service.

Provides article-level and review-level PICO evidence coverage tracking.
Distinguishes supported evidence, uncertain information, and unexamined / absent text.
Preserves human review decisions and guarantees that missing PICO information
never causes automatic screening exclusion.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    EvidenceClaimType,
    EvidenceProvenance,
    EvidenceSemanticAssessment,
    EvidenceValidationStatus,
    RadarEvidenceStatus,
    RadarHumanReviewStatus,
)
from app.contracts.models import (
    ArticleRadarResponse,
    RadarConfirmRequest,
    RadarCorrectRequest,
    RadarFieldDetail,
    RadarFlagConflictRequest,
    RadarFlagUncertainRequest,
    ReviewRadarArticleRow,
    ReviewRadarDimensionSummary,
    ReviewRadarResponse,
)
from app.db.models import (
    EvidencePassportModel,
    GroupMemberModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.corpus import project_effective_group_decision
from app.services.evidence_passport import (
    generate_or_sync_passport_for_record,
    validate_quote_against_source,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def _get_next_event_sequence(db: Session, workspace_id: str) -> int:
    """Get next review event sequence number for workspace."""
    max_seq = (
        db.query(func.max(ReviewEventModel.sequence))
        .filter_by(workspace_id=workspace_id)
        .scalar()
    )
    return (max_seq or 0) + 1


def derive_radar_status(
    claim_type: EvidenceClaimType | str,
    claim_value: str | None,
    supporting_quote: str | None,
    validation_status: EvidenceValidationStatus | str,
    semantic_assessment: EvidenceSemanticAssessment | str,
    is_contradictory: bool,
    uncertainty_note: str | None,
    has_source_text: bool,
) -> RadarEvidenceStatus:
    """Deterministically classify PICO evidence status based on source text and validation checks.

    Rules:
    1. If source text is absent/empty -> NOT_ASSESSED (cannot assert not found if text was unexamined).
    2. If is_contradictory or semantic assessment is contradicts -> CONFLICTING.
    3. If validation status is stale -> STALE.
    4. If claim_value explicitly indicates not found or empty quote with examined text -> NOT_FOUND.
    5. If verified and not uncertain -> SUPPORTED.
    6. If validation needs review, mismatched, or uncertainty note present -> UNCERTAIN.
    7. Default -> NOT_ASSESSED.
    """
    if not has_source_text:
        return RadarEvidenceStatus.NOT_ASSESSED

    if is_contradictory or semantic_assessment == EvidenceSemanticAssessment.CONTRADICTS.value:
        return RadarEvidenceStatus.CONFLICTING

    if uncertainty_note:
        return RadarEvidenceStatus.UNCERTAIN

    if validation_status == EvidenceValidationStatus.STALE.value:
        return RadarEvidenceStatus.STALE

    c_val = (claim_value or "").lower()
    q_val = (supporting_quote or "").strip()

    if not q_val or "not found in examined text" in c_val or "not found in abstract" in c_val or "no active comparator" in c_val:
        return RadarEvidenceStatus.NOT_FOUND

    if validation_status == EvidenceValidationStatus.VERIFIED.value:
        if uncertainty_note or semantic_assessment == EvidenceSemanticAssessment.INSUFFICIENT.value:
            return RadarEvidenceStatus.UNCERTAIN
        return RadarEvidenceStatus.SUPPORTED

    if validation_status in (
        EvidenceValidationStatus.NEEDS_REVIEW.value,
        EvidenceValidationStatus.MISMATCHED.value,
        EvidenceValidationStatus.INSUFFICIENT_EVIDENCE.value,
        EvidenceValidationStatus.MISSING_SOURCE.value,
    ):
        return RadarEvidenceStatus.UNCERTAIN

    return RadarEvidenceStatus.NOT_ASSESSED


def _safe_json_list(val: str | None) -> list[str]:
    """Safely deserialize a JSON array or return empty list."""
    if not val:
        return []
    try:
        res = json.loads(val)
        return res if isinstance(res, list) else []
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def _resolve_paper_group(db: Session, workspace_id: str, group_id: str) -> tuple[PaperGroupModel, RecordRevisionModel]:
    """Locate PaperGroupModel and representative RecordRevisionModel or raise 404."""
    group = (
        db.query(PaperGroupModel)
        .filter_by(id=group_id, workspace_id=workspace_id)
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found in workspace",
        )

    # Find canonical record revision
    member = (
        db.query(GroupMemberModel, SourceRecordModel)
        .join(SourceRecordModel, SourceRecordModel.id == GroupMemberModel.source_record_id)
        .filter(GroupMemberModel.group_id == group_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No source records associated with paper group '{group_id}'",
        )

    source_rec = member[1]
    rep_rev = (
        db.query(RecordRevisionModel)
        .filter_by(source_record_id=source_rec.id)
        .order_by(RecordRevisionModel.fetched_at.desc())
        .first()
    )
    if not rep_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No record revisions found for paper group '{group_id}'",
        )

    return group, rep_rev


def get_or_sync_article_radar(
    db: Session,
    workspace_id: str,
    group_id: str,
) -> ArticleRadarResponse:
    """Retrieve or compute article-level Missing-Evidence Radar for a specific paper group."""
    group, rep_rev = _resolve_paper_group(db, workspace_id, group_id)

    # 1. Ensure passport claims exist
    try:
        generate_or_sync_passport_for_record(
            db=db,
            workspace_id=workspace_id,
            group_id=group.id,
            record_revision=rep_rev,
            screen_result=None,
            pico_result=None,
        )
    except (HTTPException, ValueError, KeyError, AttributeError, TypeError) as e:
        logger.debug("Passport generation encountered error for group %s: %s", group_id, e)

    # 2. Resolve effective decision state and review notes
    eff_state, latest_event, screen_res, _ = project_effective_group_decision(db, group.id)
    screening_reason: str | None = None
    if latest_event and latest_event.payload_json:
        try:
            pl = json.loads(latest_event.payload_json)
            screening_reason = pl.get("notes") or (
                ", ".join(pl.get("exclusion_reasons", [])) if pl.get("exclusion_reasons") else None
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    elif screen_res:
        screening_reason = screen_res.rationale

    # 3. Load active non-superseded passport items
    active_passports = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            EvidencePassportModel.paper_group_id == group.id,
            EvidencePassportModel.superseded_by_id.is_(None),
        )
        .all()
    )

    passports_by_type: dict[str, EvidencePassportModel] = {}
    for p in active_passports:
        # Keep latest or human-corrected item for each claim type
        if p.claim_type not in passports_by_type or p.provenance in (
            EvidenceProvenance.HUMAN_CORRECTED.value,
            EvidenceProvenance.HUMAN_CREATED.value,
        ):
            passports_by_type[p.claim_type] = p

    abstract_text = rep_rev.abstract_text or ""
    has_source_text = len(abstract_text.strip()) > 0

    # 4. Construct RadarFieldDetail for each PICO dimension
    pico_labels = {
        EvidenceClaimType.POPULATION.value: "Population",
        EvidenceClaimType.INTERVENTION.value: "Intervention",
        EvidenceClaimType.COMPARATOR.value: "Comparator",
        EvidenceClaimType.OUTCOME.value: "Outcome",
    }

    radar_fields: dict[str, RadarFieldDetail] = {}
    supported_count = 0
    needs_review = False

    for c_type_str, label in pico_labels.items():
        item = passports_by_type.get(c_type_str)

        if item:
            # Derive human review status
            if (
                item.provenance == EvidenceProvenance.HUMAN_CORRECTED.value
                or item.reviewer_correction_reason
                or item.human_review_status == RadarHumanReviewStatus.CORRECTED.value
            ):
                h_status = RadarHumanReviewStatus.CORRECTED
            elif item.provenance == "human_confirmed" or item.human_review_status == RadarHumanReviewStatus.CONFIRMED.value:
                h_status = RadarHumanReviewStatus.CONFIRMED
            else:
                h_status = RadarHumanReviewStatus.UNREVIEWED

            # Derive current radar status
            if h_status == RadarHumanReviewStatus.CONFIRMED:
                r_status = RadarEvidenceStatus.SUPPORTED
            elif h_status == RadarHumanReviewStatus.CORRECTED:
                if item.is_contradictory or item.semantic_assessment == EvidenceSemanticAssessment.CONTRADICTS.value:
                    r_status = RadarEvidenceStatus.CONFLICTING
                elif item.uncertainty_note:
                    r_status = RadarEvidenceStatus.UNCERTAIN
                elif item.validation_status == EvidenceValidationStatus.STALE.value:
                    r_status = RadarEvidenceStatus.STALE
                else:
                    r_status = RadarEvidenceStatus.SUPPORTED
            else:
                r_status = derive_radar_status(
                    claim_type=item.claim_type,
                    claim_value=item.claim_value,
                    supporting_quote=item.supporting_quote,
                    validation_status=item.validation_status,
                    semantic_assessment=item.semantic_assessment,
                    is_contradictory=item.is_contradictory,
                    uncertainty_note=item.uncertainty_note,
                    has_source_text=has_source_text,
                )

            # Sync database columns if changed
            if item.radar_status != r_status.value or item.human_review_status != h_status.value:
                item.radar_status = r_status.value
                item.human_review_status = h_status.value
                db.commit()

            field_detail = RadarFieldDetail(
                claim_type=EvidenceClaimType(c_type_str),
                field_label=label,
                radar_status=r_status,
                human_review_status=h_status,
                claim_value=item.claim_value,
                original_claim_value=item.original_claim_value,
                source_field=item.source_field or "abstract",
                supporting_quote=item.supporting_quote or None,
                start_cp=item.start_cp,
                end_cp=item.end_cp,
                validation_status=EvidenceValidationStatus(item.validation_status),
                validation_message=item.validation_message,
                semantic_assessment=EvidenceSemanticAssessment(item.semantic_assessment),
                is_contradictory=item.is_contradictory,
                uncertainty_note=item.uncertainty_note,
                reviewer_correction_reason=item.reviewer_correction_reason,
                reviewer_notes=item.reviewer_notes,
                evidence_id=item.id,
                updated_at=item.updated_at,
            )
        else:
            # Dimension was not extracted
            if has_source_text:
                r_status = RadarEvidenceStatus.NOT_FOUND
                val_msg = f"No {label.lower()} evidence located in examined abstract text."
                claim_val = "Not found in examined text (abstract)"
            else:
                r_status = RadarEvidenceStatus.NOT_ASSESSED
                val_msg = "No source text available to evaluate."
                claim_val = None

            field_detail = RadarFieldDetail(
                claim_type=EvidenceClaimType(c_type_str),
                field_label=label,
                radar_status=r_status,
                human_review_status=RadarHumanReviewStatus.UNREVIEWED,
                claim_value=claim_val,
                source_field="abstract",
                supporting_quote=None,
                validation_status=EvidenceValidationStatus.INSUFFICIENT_EVIDENCE,
                validation_message=val_msg,
                semantic_assessment=EvidenceSemanticAssessment.INSUFFICIENT,
            )

        if field_detail.radar_status == RadarEvidenceStatus.SUPPORTED:
            supported_count += 1

        if field_detail.radar_status in (
            RadarEvidenceStatus.UNCERTAIN,
            RadarEvidenceStatus.CONFLICTING,
            RadarEvidenceStatus.STALE,
        ) or (field_detail.human_review_status == RadarHumanReviewStatus.UNREVIEWED and field_detail.radar_status != RadarEvidenceStatus.SUPPORTED):
            needs_review = True

        radar_fields[c_type_str] = field_detail

    coverage_pct = round((supported_count / 4.0) * 100, 1)

    return ArticleRadarResponse(
        workspace_id=workspace_id,
        group_id=group.id,
        paper_title=rep_rev.title,
        source_text=rep_rev.abstract_text,
        source_field="abstract",
        has_source_text=has_source_text,
        effective_decision=eff_state,
        screening_reason=screening_reason,
        pico=radar_fields,
        overall_coverage_pct=coverage_pct,
        needs_human_review=needs_review,
    )


def get_review_level_radar(
    db: Session,
    workspace_id: str,
    dimension_filter: str | None = None,
    status_filter: str | None = None,
    needs_review_only: bool = False,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ReviewRadarResponse:
    """Compute review-level Missing-Evidence Radar matrix, dimension metrics, and prioritized queue.

    Batch processes all workspace paper groups and active evidence passports to prevent N+1 query overhead.
    """
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # 1. Fetch all paper groups and representative revisions for workspace
    groups = (
        db.query(PaperGroupModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(PaperGroupModel.created_at.asc())
        .all()
    )

    if not groups:
        empty_summaries = {
            dim.value: ReviewRadarDimensionSummary(
                dimension=dim,
                total_assessed=0,
                supported_count=0,
                uncertain_count=0,
                not_found_count=0,
                conflicting_count=0,
                stale_count=0,
                not_assessed_count=0,
                human_confirmed_count=0,
                human_corrected_count=0,
                pending_review_count=0,
                supported_percent=0.0,
            )
            for dim in [
                EvidenceClaimType.POPULATION,
                EvidenceClaimType.INTERVENTION,
                EvidenceClaimType.COMPARATOR,
                EvidenceClaimType.OUTCOME,
            ]
        }
        return ReviewRadarResponse(
            workspace_id=workspace_id,
            total_articles=0,
            articles_with_source_text=0,
            articles_without_source_text=0,
            dimension_summaries=empty_summaries,
            total_fields_supported_percent=0.0,
            needs_review_total=0,
            rows=[],
        )

    # 2. Batch load representative revisions
    group_ids = [g.id for g in groups]
    members = (
        db.query(GroupMemberModel.group_id, SourceRecordModel.id)
        .join(SourceRecordModel, SourceRecordModel.id == GroupMemberModel.source_record_id)
        .filter(GroupMemberModel.group_id.in_(group_ids))
        .all()
    )
    group_to_source_id: dict[str, str] = {m[0]: m[1] for m in members}

    source_ids = list(group_to_source_id.values())
    revisions = (
        db.query(RecordRevisionModel)
        .filter(RecordRevisionModel.source_record_id.in_(source_ids))
        .order_by(RecordRevisionModel.fetched_at.desc())
        .all()
    )
    source_to_rev: dict[str, RecordRevisionModel] = {}
    for r in revisions:
        if r.source_record_id not in source_to_rev:
            source_to_rev[r.source_record_id] = r

    # 3. Batch load active evidence passports for workspace
    passports = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            EvidencePassportModel.superseded_by_id.is_(None),
        )
        .all()
    )
    passports_by_group: dict[str, dict[str, EvidencePassportModel]] = {g.id: {} for g in groups}
    for p in passports:
        if p.paper_group_id and p.paper_group_id in passports_by_group:
            # Store primary item per claim type
            group_dict = passports_by_group[p.paper_group_id]
            if p.claim_type not in group_dict or p.provenance in (
                EvidenceProvenance.HUMAN_CORRECTED.value,
                EvidenceProvenance.HUMAN_CREATED.value,
            ):
                group_dict[p.claim_type] = p

    # 4. Dimensions to track
    pico_dims = [
        EvidenceClaimType.POPULATION,
        EvidenceClaimType.INTERVENTION,
        EvidenceClaimType.COMPARATOR,
        EvidenceClaimType.OUTCOME,
    ]

    dimension_metrics: dict[str, dict[str, int]] = {
        dim.value: {
            "total_assessed": 0,
            "supported": 0,
            "uncertain": 0,
            "not_found": 0,
            "conflicting": 0,
            "stale": 0,
            "not_assessed": 0,
            "confirmed": 0,
            "corrected": 0,
            "pending": 0,
        }
        for dim in pico_dims
    }

    articles_with_text = 0
    articles_without_text = 0
    article_rows: list[ReviewRadarArticleRow] = []

    for group in groups:
        src_id = group_to_source_id.get(group.id)
        rev = source_to_rev.get(src_id) if src_id else None

        has_text = False
        title = "Untitled Paper"
        authors: list[str] = []
        year: int | None = None
        journal: str | None = None
        doi: str | None = None
        pmid: str | None = None

        if rev:
            title = rev.title
            has_text = bool(rev.abstract_text and len(rev.abstract_text.strip()) > 0)
            authors = _safe_json_list(rev.authors_json)
            year = rev.year
            journal = rev.journal
            doi = rev.doi
            pmid = rev.pmid

        if has_text:
            articles_with_text += 1
        else:
            articles_without_text += 1

        eff_decision, _, _, _ = project_effective_group_decision(db, group.id)

        # Check PICO statuses
        group_passports = passports_by_group.get(group.id, {})
        row_statuses: dict[str, RadarEvidenceStatus] = {}
        row_values: dict[str, str | None] = {}
        row_needs_review = False
        row_priority = 5  # default normal

        for dim in pico_dims:
            dim_key = dim.value
            item = group_passports.get(dim_key)
            metrics = dimension_metrics[dim_key]

            if item:
                metrics["total_assessed"] += 1

                # Check human review status & radar status
                if (
                    item.provenance == EvidenceProvenance.HUMAN_CORRECTED.value
                    or item.reviewer_correction_reason
                    or item.human_review_status == RadarHumanReviewStatus.CORRECTED.value
                ):
                    metrics["corrected"] += 1
                    if item.is_contradictory or item.semantic_assessment == EvidenceSemanticAssessment.CONTRADICTS.value:
                        r_status = RadarEvidenceStatus.CONFLICTING
                    elif item.uncertainty_note:
                        r_status = RadarEvidenceStatus.UNCERTAIN
                    elif item.validation_status == EvidenceValidationStatus.STALE.value:
                        r_status = RadarEvidenceStatus.STALE
                    else:
                        r_status = RadarEvidenceStatus.SUPPORTED
                elif item.provenance == "human_confirmed" or item.human_review_status == RadarHumanReviewStatus.CONFIRMED.value:
                    metrics["confirmed"] += 1
                    r_status = RadarEvidenceStatus.SUPPORTED
                else:
                    metrics["pending"] += 1
                    r_status = derive_radar_status(
                        claim_type=dim_key,
                        claim_value=item.claim_value,
                        supporting_quote=item.supporting_quote,
                        validation_status=item.validation_status,
                        semantic_assessment=item.semantic_assessment,
                        is_contradictory=item.is_contradictory,
                        uncertainty_note=item.uncertainty_note,
                        has_source_text=has_text,
                    )

                row_statuses[dim_key] = r_status
                row_values[dim_key] = item.claim_value

                # Update metrics
                if r_status == RadarEvidenceStatus.SUPPORTED:
                    metrics["supported"] += 1
                elif r_status == RadarEvidenceStatus.UNCERTAIN:
                    metrics["uncertain"] += 1
                elif r_status == RadarEvidenceStatus.NOT_FOUND:
                    metrics["not_found"] += 1
                elif r_status == RadarEvidenceStatus.CONFLICTING:
                    metrics["conflicting"] += 1
                elif r_status == RadarEvidenceStatus.STALE:
                    metrics["stale"] += 1
                else:
                    metrics["not_assessed"] += 1

            else:
                if has_text:
                    r_status = RadarEvidenceStatus.NOT_FOUND
                    row_values[dim_key] = "Not found in examined text"
                    metrics["total_assessed"] += 1
                    metrics["not_found"] += 1
                else:
                    r_status = RadarEvidenceStatus.NOT_ASSESSED
                    row_values[dim_key] = None
                    metrics["not_assessed"] += 1

                row_statuses[dim_key] = r_status
                metrics["pending"] += 1

            # Determine row review priority
            if r_status == RadarEvidenceStatus.STALE:
                row_needs_review = True
                row_priority = min(row_priority, 1)
            elif r_status == RadarEvidenceStatus.CONFLICTING:
                row_needs_review = True
                row_priority = min(row_priority, 2)
            elif r_status == RadarEvidenceStatus.UNCERTAIN:
                row_needs_review = True
                row_priority = min(row_priority, 3)
            elif r_status != RadarEvidenceStatus.SUPPORTED:
                row_needs_review = True
                row_priority = min(row_priority, 4)

        article_rows.append(
            ReviewRadarArticleRow(
                group_id=group.id,
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                doi=doi,
                pmid=pmid,
                has_source_text=has_text,
                effective_decision=eff_decision,
                population_status=row_statuses[EvidenceClaimType.POPULATION.value],
                intervention_status=row_statuses[EvidenceClaimType.INTERVENTION.value],
                comparator_status=row_statuses[EvidenceClaimType.COMPARATOR.value],
                outcome_status=row_statuses[EvidenceClaimType.OUTCOME.value],
                population_value=row_values[EvidenceClaimType.POPULATION.value],
                intervention_value=row_values[EvidenceClaimType.INTERVENTION.value],
                comparator_value=row_values[EvidenceClaimType.COMPARATOR.value],
                outcome_value=row_values[EvidenceClaimType.OUTCOME.value],
                needs_review=row_needs_review,
                priority_rank=row_priority,
            )
        )

    # 5. Build Dimension Summaries
    total_articles = len(groups)
    total_fields_evaluated = total_articles * 4
    total_supported_fields = 0
    dim_summaries: dict[str, ReviewRadarDimensionSummary] = {}

    for dim in pico_dims:
        k = dim.value
        m = dimension_metrics[k]
        total_supported_fields += m["supported"]
        denom = m["total_assessed"] or 1
        pct = round((m["supported"] / float(denom)) * 100, 1)

        dim_summaries[k] = ReviewRadarDimensionSummary(
            dimension=dim,
            total_assessed=m["total_assessed"],
            supported_count=m["supported"],
            uncertain_count=m["uncertain"],
            not_found_count=m["not_found"],
            conflicting_count=m["conflicting"],
            stale_count=m["stale"],
            not_assessed_count=m["not_assessed"],
            human_confirmed_count=m["confirmed"],
            human_corrected_count=m["corrected"],
            pending_review_count=m["pending"],
            supported_percent=pct,
        )

    overall_supported_pct = round(
        (total_supported_fields / float(total_fields_evaluated or 1)) * 100, 1
    )

    # 6. Apply filtering and sorting to rows
    filtered_rows = article_rows

    if needs_review_only:
        filtered_rows = [r for r in filtered_rows if r.needs_review]

    if query and query.strip():
        q_lower = query.strip().lower()
        filtered_rows = [
            r
            for r in filtered_rows
            if q_lower in r.title.lower()
            or (r.pmid and q_lower in r.pmid.lower())
            or (r.doi and q_lower in r.doi.lower())
        ]

    if status_filter:
        s_val = status_filter.lower()
        if dimension_filter:
            dim_key = dimension_filter.lower()
            if dim_key == "population":
                filtered_rows = [r for r in filtered_rows if r.population_status.value == s_val]
            elif dim_key == "intervention":
                filtered_rows = [r for r in filtered_rows if r.intervention_status.value == s_val]
            elif dim_key == "comparator":
                filtered_rows = [r for r in filtered_rows if r.comparator_status.value == s_val]
            elif dim_key == "outcome":
                filtered_rows = [r for r in filtered_rows if r.outcome_status.value == s_val]
        else:
            filtered_rows = [
                r
                for r in filtered_rows
                if r.population_status.value == s_val
                or r.intervention_status.value == s_val
                or r.comparator_status.value == s_val
                or r.outcome_status.value == s_val
            ]

    # Priority sorting: items needing attention first (priority_rank 1..5), then title
    filtered_rows.sort(key=lambda r: (r.priority_rank, r.title.lower()))

    # Pagination slice
    paginated_rows = filtered_rows[offset : offset + limit]

    needs_review_count = sum(1 for r in article_rows if r.needs_review)

    return ReviewRadarResponse(
        workspace_id=workspace_id,
        total_articles=total_articles,
        articles_with_source_text=articles_with_text,
        articles_without_source_text=articles_without_text,
        dimension_summaries=dim_summaries,
        total_fields_supported_percent=overall_supported_pct,
        needs_review_total=needs_review_count,
        rows=paginated_rows,
    )


def confirm_radar_field(
    db: Session,
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarConfirmRequest,
) -> ArticleRadarResponse:
    """Confirm an extracted PICO value as verified by human reviewer without altering screening decision."""
    group, rep_rev = _resolve_paper_group(db, workspace_id, group_id)

    # Locate active evidence passport item for this field
    item = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            EvidencePassportModel.paper_group_id == group.id,
            EvidencePassportModel.claim_type == field_type,
            EvidencePassportModel.superseded_by_id.is_(None),
        )
        .first()
    )

    if not item:
        # If item doesn't exist yet, create confirmed item
        item = EvidencePassportModel(
            workspace_id=workspace_id,
            paper_group_id=group.id,
            record_revision_id=rep_rev.id,
            claim_type=field_type,
            claim_value="Confirmed by reviewer",
            source_field="abstract",
            supporting_quote="",
            source_fingerprint=rep_rev.content_hash,
            provenance="human_confirmed",
            validation_status=EvidenceValidationStatus.VERIFIED.value,
            validation_message="Manually confirmed by reviewer.",
            semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
            assessed_by=payload.actor_id,
            radar_status=RadarEvidenceStatus.SUPPORTED.value,
            human_review_status=RadarHumanReviewStatus.CONFIRMED.value,
            reviewer_notes=payload.notes,
        )
        db.add(item)
    else:
        item.provenance = "human_confirmed"
        item.human_review_status = RadarHumanReviewStatus.CONFIRMED.value
        item.radar_status = RadarEvidenceStatus.SUPPORTED.value
        item.assessed_by = payload.actor_id
        if payload.notes:
            item.reviewer_notes = payload.notes
        item.updated_at = utc_now()

    # Record append-only audit event in review_events
    seq = _get_next_event_sequence(db, workspace_id)
    event = ReviewEventModel(
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.EVIDENCE_CORRECTION.value,
        payload_json=json.dumps({
            "action": "radar_confirm",
            "field": field_type,
            "notes": payload.notes,
        }),
    )
    db.add(event)
    db.commit()

    return get_or_sync_article_radar(db, workspace_id, group_id)


def correct_radar_field(
    db: Session,
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarCorrectRequest,
) -> ArticleRadarResponse:
    """Submit human correction for a PICO element with audit history preservation."""
    group, rep_rev = _resolve_paper_group(db, workspace_id, group_id)

    # Locate existing active item if any
    existing_item = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            EvidencePassportModel.paper_group_id == group.id,
            EvidencePassportModel.claim_type == field_type,
            EvidencePassportModel.superseded_by_id.is_(None),
        )
        .first()
    )

    abstract_text = rep_rev.abstract_text or ""
    quote_to_validate = payload.supporting_quote or (existing_item.supporting_quote if existing_item else "")

    status_val, msg, s_cp, e_cp = validate_quote_against_source(
        quote=quote_to_validate,
        start_cp=payload.start_cp,
        end_cp=payload.end_cp,
        source_text=abstract_text,
        stored_fingerprint=rep_rev.content_hash,
        claim_type=EvidenceClaimType(field_type),
        claim_value=payload.claim_value,
    )

    has_text = bool(abstract_text.strip())
    r_status = derive_radar_status(
        claim_type=field_type,
        claim_value=payload.claim_value,
        supporting_quote=quote_to_validate,
        validation_status=status_val.value,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
        is_contradictory=False,
        uncertainty_note=None,
        has_source_text=has_text,
    )

    # Create new superseding record
    new_item = EvidencePassportModel(
        workspace_id=workspace_id,
        paper_group_id=group.id,
        record_revision_id=rep_rev.id,
        claim_type=field_type,
        claim_value=payload.claim_value,
        original_claim_value=existing_item.original_claim_value if existing_item else payload.claim_value,
        source_field="abstract",
        supporting_quote=quote_to_validate,
        start_cp=s_cp,
        end_cp=e_cp,
        source_fingerprint=rep_rev.content_hash,
        provenance=EvidenceProvenance.HUMAN_CORRECTED.value,
        validation_status=status_val.value,
        validation_message=msg,
        semantic_assessment=EvidenceSemanticAssessment.SUPPORTS.value,
        assessed_by=payload.actor_id,
        reviewer_correction_reason=payload.reason,
        radar_status=r_status.value,
        human_review_status=RadarHumanReviewStatus.CORRECTED.value,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(new_item)
    db.flush()

    if existing_item:
        existing_item.superseded_by_id = new_item.id
        existing_item.updated_at = utc_now()

    # Record append-only review event
    seq = _get_next_event_sequence(db, workspace_id)
    event = ReviewEventModel(
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.EVIDENCE_CORRECTION.value,
        payload_json=json.dumps({
            "action": "radar_correct",
            "field": field_type,
            "corrected_value": payload.claim_value,
            "reason": payload.reason,
            "superseded_id": existing_item.id if existing_item else None,
        }),
    )
    db.add(event)
    db.commit()

    return get_or_sync_article_radar(db, workspace_id, group_id)


def flag_uncertain_radar_field(
    db: Session,
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarFlagUncertainRequest,
) -> ArticleRadarResponse:
    """Flag a PICO field as uncertain / ambiguous with reviewer explanation."""
    group, rep_rev = _resolve_paper_group(db, workspace_id, group_id)

    item = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            EvidencePassportModel.paper_group_id == group.id,
            EvidencePassportModel.claim_type == field_type,
            EvidencePassportModel.superseded_by_id.is_(None),
        )
        .first()
    )

    if not item:
        item = EvidencePassportModel(
            workspace_id=workspace_id,
            paper_group_id=group.id,
            record_revision_id=rep_rev.id,
            claim_type=field_type,
            claim_value="Uncertain / Ambiguous",
            source_field="abstract",
            supporting_quote="",
            source_fingerprint=rep_rev.content_hash,
            provenance="human_created",
            validation_status=EvidenceValidationStatus.NEEDS_REVIEW.value,
            validation_message="Flagged uncertain by human reviewer.",
            semantic_assessment=EvidenceSemanticAssessment.INSUFFICIENT.value,
            uncertainty_note=payload.uncertainty_note,
            assessed_by=payload.actor_id,
            radar_status=RadarEvidenceStatus.UNCERTAIN.value,
            human_review_status=RadarHumanReviewStatus.UNREVIEWED.value,
        )
        db.add(item)
    else:
        item.uncertainty_note = payload.uncertainty_note
        item.radar_status = RadarEvidenceStatus.UNCERTAIN.value
        item.validation_status = EvidenceValidationStatus.NEEDS_REVIEW.value
        item.assessed_by = payload.actor_id
        item.updated_at = utc_now()

    # Record review event
    seq = _get_next_event_sequence(db, workspace_id)
    event = ReviewEventModel(
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.EVIDENCE_CORRECTION.value,
        payload_json=json.dumps({
            "action": "radar_flag_uncertain",
            "field": field_type,
            "uncertainty_note": payload.uncertainty_note,
        }),
    )
    db.add(event)
    db.commit()

    return get_or_sync_article_radar(db, workspace_id, group_id)


def flag_conflict_radar_field(
    db: Session,
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarFlagConflictRequest,
) -> ArticleRadarResponse:
    """Flag conflicting evidence for a PICO field and record competing explanation."""
    group, rep_rev = _resolve_paper_group(db, workspace_id, group_id)

    item = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            EvidencePassportModel.paper_group_id == group.id,
            EvidencePassportModel.claim_type == field_type,
            EvidencePassportModel.superseded_by_id.is_(None),
        )
        .first()
    )

    if not item:
        item = EvidencePassportModel(
            workspace_id=workspace_id,
            paper_group_id=group.id,
            record_revision_id=rep_rev.id,
            claim_type=field_type,
            claim_value="Conflicting evidence",
            source_field="abstract",
            supporting_quote=payload.competing_quote or "",
            source_fingerprint=rep_rev.content_hash,
            provenance="human_created",
            validation_status=EvidenceValidationStatus.NEEDS_REVIEW.value,
            validation_message="Conflicting evidence passages flagged by reviewer.",
            semantic_assessment=EvidenceSemanticAssessment.CONTRADICTS.value,
            is_contradictory=True,
            uncertainty_note=payload.conflict_explanation,
            assessed_by=payload.actor_id,
            radar_status=RadarEvidenceStatus.CONFLICTING.value,
            human_review_status=RadarHumanReviewStatus.UNREVIEWED.value,
        )
        db.add(item)
    else:
        item.is_contradictory = True
        item.semantic_assessment = EvidenceSemanticAssessment.CONTRADICTS.value
        item.radar_status = RadarEvidenceStatus.CONFLICTING.value
        item.uncertainty_note = payload.conflict_explanation
        item.assessed_by = payload.actor_id
        item.updated_at = utc_now()

    # Record review event
    seq = _get_next_event_sequence(db, workspace_id)
    event = ReviewEventModel(
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.EVIDENCE_CORRECTION.value,
        payload_json=json.dumps({
            "action": "radar_flag_conflict",
            "field": field_type,
            "conflict_explanation": payload.conflict_explanation,
            "competing_quote": payload.competing_quote,
        }),
    )
    db.add(event)
    db.commit()

    return get_or_sync_article_radar(db, workspace_id, group_id)


def revalidate_radar_field(
    db: Session,
    workspace_id: str,
    group_id: str,
    field_type: str,
) -> ArticleRadarResponse:
    """Revalidate an evidence field against the stored source text and update stale flags."""
    group, rep_rev = _resolve_paper_group(db, workspace_id, group_id)

    item = (
        db.query(EvidencePassportModel)
        .filter(
            EvidencePassportModel.workspace_id == workspace_id,
            EvidencePassportModel.paper_group_id == group.id,
            EvidencePassportModel.claim_type == field_type,
            EvidencePassportModel.superseded_by_id.is_(None),
        )
        .first()
    )

    if item:
        abstract_text = rep_rev.abstract_text or ""
        status_val, msg, s_cp, e_cp = validate_quote_against_source(
            quote=item.supporting_quote,
            start_cp=item.start_cp,
            end_cp=item.end_cp,
            source_text=abstract_text,
            stored_fingerprint=item.source_fingerprint,
            claim_type=EvidenceClaimType(field_type),
            claim_value=item.claim_value,
        )

        item.validation_status = status_val.value
        item.validation_message = msg
        item.start_cp = s_cp
        item.end_cp = e_cp

        # Re-derive radar status
        has_text = bool(abstract_text.strip())
        item.radar_status = derive_radar_status(
            claim_type=field_type,
            claim_value=item.claim_value,
            supporting_quote=item.supporting_quote,
            validation_status=status_val.value,
            semantic_assessment=item.semantic_assessment,
            is_contradictory=item.is_contradictory,
            uncertainty_note=item.uncertainty_note,
            has_source_text=has_text,
        ).value

        # If fingerprint matches now, update stored fingerprint
        if status_val == EvidenceValidationStatus.VERIFIED:
            item.source_fingerprint = rep_rev.content_hash

        item.updated_at = utc_now()
        db.commit()

    return get_or_sync_article_radar(db, workspace_id, group_id)
