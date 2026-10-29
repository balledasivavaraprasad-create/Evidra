"""PRISMA 2020 Flow Diagram and Automated Reporting domain service.

Derives transparent, explainable, and reproducible PRISMA 2020 flow counts
from persisted review records, deduplication lineages, and screening decisions.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.enums import (
    EffectiveDecisionState,
    PrismaStage,
    PrismaStageStatus,
    PrismaValidationSeverity,
)
from app.contracts.models import (
    PrismaEligibilityDetails,
    PrismaExclusionReasonItem,
    PrismaIdentificationDetails,
    PrismaIncludedDetails,
    PrismaPreScreeningDetails,
    PrismaReconciliationSummary,
    PrismaReportResponse,
    PrismaRetrievalDetails,
    PrismaScreeningDetails,
    PrismaSnapshotCreateRequest,
    PrismaSnapshotSummaryItem,
    PrismaSourceBreakdown,
    PrismaStageRecordItem,
    PrismaStageRecordsResponse,
    PrismaStages,
    PrismaValidationIssue,
)
from app.db.models import (
    GroupMemberModel,
    PaperGroupModel,
    PrismaSnapshotModel,
    QueryVersionModel,
    RecordRevisionModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.corpus import project_effective_group_decision
from app.services.exports import sanitize_formula_injection

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def _safe_json_list(val: str | None) -> list[Any]:
    if not val:
        return []
    try:
        data = json.loads(val)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def compute_prisma_flow_report(
    db: Session,
    workspace_id: str,
    corpus_revision_id: str | None = None,
    query_version_id: str | None = None,
) -> PrismaReportResponse:
    """Compute live, fully reconciled PRISMA 2020 flow report from persisted review data."""
    workspace = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    # 1. Identification Stage: Source Records & Databases
    source_records = (
        db.query(SourceRecordModel)
        .filter_by(workspace_id=workspace_id)
        .all()
    )
    total_identified = len(source_records)

    # Breakdown by database / source
    sources_count: dict[str, int] = {}
    for r in source_records:
        src = r.source_namespace or r.source or "Unknown Source"
        src_lower = src.lower().replace(" ", "").replace("_", "").replace("-", "")
        clean_src = "PubMed" if ("pubmed" in src_lower or src_lower == "pmid") else "Europe PMC" if ("europe" in src_lower or "pmc" in src_lower) else src.title()
        sources_count[clean_src] = sources_count.get(clean_src, 0) + 1

    # Map search execution IDs
    search_execs = (
        db.query(SearchExecutionModel)
        .join(QueryVersionModel, SearchExecutionModel.query_version_id == QueryVersionModel.id)
        .filter(QueryVersionModel.workspace_id == workspace_id)
        .all()
    )
    exec_map: dict[str, list[str]] = {}
    for se in search_execs:
        src_val = se.source or "Unknown"
        src_lower = src_val.lower().replace(" ", "").replace("_", "").replace("-", "")
        src_key = "PubMed" if ("pubmed" in src_lower or src_lower == "pmid") else "Europe PMC" if ("europe" in src_lower or "pmc" in src_lower) else src_val.title()
        exec_map.setdefault(src_key, []).append(se.id)

    db_sources: list[PrismaSourceBreakdown] = [
        PrismaSourceBreakdown(
            source_name=name,
            records_count=cnt,
            search_execution_ids=exec_map.get(name, []),
        )
        for name, cnt in sorted(sources_count.items(), key=lambda x: -x[1])
    ]

    identification_details = PrismaIdentificationDetails(
        database_sources=db_sources,
        total_database_records=total_identified,
        other_sources=[],
        total_other_records=0,
        total_identified=total_identified,
    )

    # 2. Pre-Screening: Deduplication & Study Aggregation
    paper_groups = (
        db.query(PaperGroupModel)
        .filter_by(workspace_id=workspace_id)
        .all()
    )
    total_study_groups = len(paper_groups)

    # Duplicate records removed = raw records - unique study groups (if records were merged)
    duplicates_removed = max(0, total_identified - total_study_groups)
    other_removed = 0
    records_eligible = total_study_groups

    pre_screening_details = PrismaPreScreeningDetails(
        duplicate_records_removed=duplicates_removed,
        other_records_removed=other_removed,
        other_removal_reasons=[],
        total_removed=duplicates_removed + other_removed,
        records_eligible_for_screening=records_eligible,
    )

    # 3. Screening Stage: Title / Abstract Decisions & Reasons
    included_studies_count = 0
    included_reports_count = 0
    excluded_count = 0
    pending_count = 0
    maybe_count = 0
    conflict_count = 0
    exclusion_reasons_counter: dict[str, int] = {}

    for grp in paper_groups:
        eff_state, latest_event, screen_res, has_conflict = project_effective_group_decision(db, grp.id)

        # Count member reports in this study group
        member_reports_count = (
            db.query(GroupMemberModel)
            .filter_by(group_id=grp.id)
            .count()
        ) or 1

        if has_conflict or eff_state == EffectiveDecisionState.CONFLICT:
            conflict_count += 1
        elif eff_state == EffectiveDecisionState.INCLUDE:
            included_studies_count += 1
            included_reports_count += member_reports_count
        elif eff_state == EffectiveDecisionState.EXCLUDE:
            excluded_count += 1
            # Extract exclusion reason
            reason = None
            if latest_event and latest_event.reason:
                reason = latest_event.reason.strip()
            elif screen_res and screen_res.rationale:
                reason = screen_res.rationale.strip()
            if not reason:
                reason = "Reason not recorded"
            exclusion_reasons_counter[reason] = exclusion_reasons_counter.get(reason, 0) + 1
        elif eff_state == EffectiveDecisionState.MAYBE:
            maybe_count += 1
        else:
            pending_count += 1

    records_screened = included_studies_count + excluded_count
    records_advancing = included_studies_count

    # Build exclusion reason breakdown
    exclusion_reason_items: list[PrismaExclusionReasonItem] = []
    for r_text, r_cnt in sorted(exclusion_reasons_counter.items(), key=lambda x: -x[1]):
        pct = round((r_cnt / excluded_count * 100.0), 1) if excluded_count > 0 else 0.0
        exclusion_reason_items.append(
            PrismaExclusionReasonItem(
                reason=r_text,
                count=r_cnt,
                percentage=pct,
                stage=PrismaStage.SCREENING,
            )
        )

    screening_details = PrismaScreeningDetails(
        records_screened=records_screened,
        records_excluded=excluded_count,
        exclusion_reasons=exclusion_reason_items,
        records_pending=pending_count,
        records_maybe=maybe_count,
        records_conflicts=conflict_count,
        records_advancing=records_advancing,
    )

    # 4. Retrieval Stage: Truthful Disclosure
    retrieval_details = PrismaRetrievalDetails(
        is_supported=False,
        status=PrismaStageStatus.NOT_STARTED,
        reports_sought_for_retrieval=0,
        reports_not_retrieved=0,
        notes="Automated full-text retrieval stage is not started. Evidra currently screens titles and abstracts deterministically with exact PICO offset verification.",
    )

    # 5. Eligibility Stage: Full-Text Eligibility Truthful Disclosure
    eligibility_details = PrismaEligibilityDetails(
        is_supported=False,
        status=PrismaStageStatus.NOT_STARTED,
        reports_assessed=0,
        reports_excluded=0,
        exclusion_reasons=[],
        notes="Full-text eligibility screening stage is not configured. Study eligibility is currently adjudicated at the title and abstract level.",
    )

    # 6. Included Stage: Authoritative Final Review State
    included_details = PrismaIncludedDetails(
        studies_included=included_studies_count,
        reports_included=included_reports_count,
        studies_included_title_abstract=included_studies_count,
        notes=(
            f"{included_studies_count} unique study "
            f"{'group' if included_studies_count == 1 else 'groups'} and {included_reports_count} "
            f"publication {'report' if included_reports_count == 1 else 'reports'} included in review."
        ) if included_studies_count > 0 else "No studies have been marked as included yet.",
    )

    # 7. Mathematical Reconciliation & Consistency Checks
    id_balance = total_identified - (duplicates_removed + other_removed + records_eligible)
    screen_balance = records_eligible - (records_screened + pending_count + maybe_count + conflict_count)
    is_reconciled = (id_balance == 0) and (screen_balance == 0)

    reconciliation = PrismaReconciliationSummary(
        is_reconciled=is_reconciled,
        identification_balance=id_balance,
        screening_balance=screen_balance,
        discrepancy_explanation=None if is_reconciled else f"Identification discrepancy: {id_balance}, Screening discrepancy: {screen_balance}.",
    )

    # 8. Validation Issues & Warnings
    validation_issues: list[PrismaValidationIssue] = []

    if not is_reconciled:
        validation_issues.append(
            PrismaValidationIssue(
                code="ARITHMETIC_DISCREPANCY",
                message=f"Flow numbers do not balance mathematically: identification balance={id_balance}, screening balance={screen_balance}.",
                severity=PrismaValidationSeverity.ERROR,
                stage=PrismaStage.SCREENING,
            )
        )

    if pending_count > 0:
        validation_issues.append(
            PrismaValidationIssue(
                code="UNSCREENED_RECORDS",
                message=f"{pending_count} records remain unscreened. Final PRISMA inclusion counts are in-progress and tentative.",
                severity=PrismaValidationSeverity.WARNING,
                stage=PrismaStage.SCREENING,
                affected_count=pending_count,
            )
        )

    if maybe_count > 0:
        validation_issues.append(
            PrismaValidationIssue(
                code="MAYBE_DECISIONS_PENDING",
                message=f"{maybe_count} records are marked 'Maybe' awaiting reviewer adjudication.",
                severity=PrismaValidationSeverity.WARNING,
                stage=PrismaStage.SCREENING,
                affected_count=maybe_count,
            )
        )

    if conflict_count > 0:
        validation_issues.append(
            PrismaValidationIssue(
                code="UNRESOLVED_CONFLICTS",
                message=f"{conflict_count} duplicate groups have active conflicting decisions requiring reconciliation.",
                severity=PrismaValidationSeverity.ERROR,
                stage=PrismaStage.PRE_SCREENING,
                affected_count=conflict_count,
            )
        )

    if "Reason not recorded" in exclusion_reasons_counter and exclusion_reasons_counter["Reason not recorded"] > 0:
        validation_issues.append(
            PrismaValidationIssue(
                code="MISSING_EXCLUSION_REASONS",
                message=f"{exclusion_reasons_counter['Reason not recorded']} excluded records do not have an explicit exclusion reason recorded.",
                severity=PrismaValidationSeverity.INFO,
                stage=PrismaStage.SCREENING,
                affected_count=exclusion_reasons_counter["Reason not recorded"],
            )
        )

    validation_issues.append(
        PrismaValidationIssue(
            code="FULL_TEXT_STAGE_UNAVAILABLE",
            message="Full-text retrieval and eligibility stages are not started. Title/abstract screening is the authoritative inclusion gate.",
            severity=PrismaValidationSeverity.INFO,
            stage=PrismaStage.ELIGIBILITY,
        )
    )

    stages = PrismaStages(
        identification=identification_details,
        pre_screening=pre_screening_details,
        screening=screening_details,
        retrieval=retrieval_details,
        eligibility=eligibility_details,
        included=included_details,
    )

    return PrismaReportResponse(
        workspace_id=workspace.id,
        workspace_title=workspace.title,
        generated_at=utc_now(),
        is_live=True,
        snapshot_id=None,
        corpus_revision_id=corpus_revision_id,
        query_version_id=query_version_id,
        schema_version="2020.1",
        stages=stages,
        validation_issues=validation_issues,
        reconciliation=reconciliation,
        exclusion_reasons_summary=exclusion_reason_items,
    )


def get_prisma_stage_records(
    db: Session,
    workspace_id: str,
    stage: str | PrismaStage,
    limit: int = 50,
    offset: int = 0,
    corpus_revision_id: str | None = None,
    query_version_id: str | None = None,
) -> PrismaStageRecordsResponse:
    """Retrieve actual persisted records contributing to a specific PRISMA 2020 node or count."""
    workspace = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    stage_raw = stage.value if hasattr(stage, 'value') else str(stage)
    stage_clean = stage_raw.lower().strip()
    records_out: list[PrismaStageRecordItem] = []
    total_count = 0
    stage_label = stage_clean.replace("_", " ").title()

    if stage_clean in ("identified", "all_records"):
        stage_label = "Records Identified (All Databases)"
        query = (
            db.query(SourceRecordModel, RecordRevisionModel)
            .outerjoin(RecordRevisionModel, RecordRevisionModel.source_record_id == SourceRecordModel.id)
            .filter(SourceRecordModel.workspace_id == workspace_id)
        )
        total_count = query.count()
        rows = query.offset(offset).limit(limit).all()

        for s_rec, rev in rows:
            authors = _safe_json_list(rev.authors_json) if rev else []
            records_out.append(
                PrismaStageRecordItem(
                    source_record_id=s_rec.id,
                    title=rev.title if rev else f"Record {s_rec.external_id}",
                    authors=authors,
                    year=rev.year if rev else None,
                    journal=rev.journal if rev else None,
                    doi=rev.doi if rev else None,
                    pmid=s_rec.external_id if (s_rec.source_namespace or "").lower() == "pubmed" else (rev.pmid if rev else None),
                    source_namespace=s_rec.source_namespace or s_rec.source,
                    decision="unscreened",
                    is_canonical=False,
                    is_duplicate=False,
                )
            )

    elif stage_clean in ("duplicates_removed", "duplicates"):
        stage_label = "Duplicate Records Removed Before Screening"
        # Find all groups with > 1 member and fetch non-canonical records
        groups = db.query(PaperGroupModel).filter_by(workspace_id=workspace_id).all()
        dup_record_ids = []
        for g in groups:
            members = db.query(GroupMemberModel).filter_by(group_id=g.id).all()
            if len(members) > 1:
                # Keep first/canonical, others are duplicates removed
                for m in members[1:]:
                    dup_record_ids.append(m.source_record_id)

        total_count = len(dup_record_ids)
        page_ids = dup_record_ids[offset : offset + limit]

        if page_ids:
            query = (
                db.query(SourceRecordModel, RecordRevisionModel)
                .outerjoin(RecordRevisionModel, RecordRevisionModel.source_record_id == SourceRecordModel.id)
                .filter(SourceRecordModel.id.in_(page_ids))
            )
            for s_rec, rev in query.all():
                authors = _safe_json_list(rev.authors_json) if rev else []
                records_out.append(
                    PrismaStageRecordItem(
                        source_record_id=s_rec.id,
                        title=rev.title if rev else f"Duplicate Record {s_rec.external_id}",
                        authors=authors,
                        year=rev.year if rev else None,
                        journal=rev.journal if rev else None,
                        doi=rev.doi if rev else None,
                        pmid=s_rec.external_id if (s_rec.source_namespace or "").lower() == "pubmed" else (rev.pmid if rev else None),
                        source_namespace=s_rec.source_namespace or s_rec.source,
                        decision="duplicate_removed",
                        decision_reason="Merged with canonical publication copy",
                        is_canonical=False,
                        is_duplicate=True,
                    )
                )

    else:
        # Screening / Decision stages (screened, excluded, included, pending, maybe, conflicts)
        target_states = []
        if stage_clean == "included":
            stage_label = "Studies Included in Review"
            target_states = [EffectiveDecisionState.INCLUDE]
        elif stage_clean == "excluded":
            stage_label = "Records Excluded at Title/Abstract Screening"
            target_states = [EffectiveDecisionState.EXCLUDE]
        elif stage_clean == "screened":
            stage_label = "Records Screened by Title/Abstract"
            target_states = [EffectiveDecisionState.INCLUDE, EffectiveDecisionState.EXCLUDE]
        elif stage_clean in ("pending", "unscreened"):
            stage_label = "Records Pending Screening"
            target_states = [EffectiveDecisionState.UNSCREENED]
        elif stage_clean == "maybe":
            stage_label = "Records with Maybe / Uncertain Decisions"
            target_states = [EffectiveDecisionState.MAYBE]
        elif stage_clean == "conflicts":
            stage_label = "Records with Unresolved Conflicts"
            target_states = [EffectiveDecisionState.CONFLICT]
        else:
            stage_label = f"Stage: {stage_clean.title()}"
            target_states = [EffectiveDecisionState.INCLUDE, EffectiveDecisionState.EXCLUDE]

        all_groups = db.query(PaperGroupModel).filter_by(workspace_id=workspace_id).all()
        matched_groups: list[tuple[PaperGroupModel, str, str | None]] = []

        for g in all_groups:
            eff_state, latest_event, screen_res, has_conflict = project_effective_group_decision(db, g.id)
            state_to_check = EffectiveDecisionState.CONFLICT if has_conflict else eff_state

            if state_to_check in target_states:
                reason = None
                if latest_event and latest_event.reason:
                    reason = latest_event.reason.strip()
                elif screen_res and screen_res.rationale:
                    reason = screen_res.rationale.strip()
                matched_groups.append((g, state_to_check.value, reason))

        total_count = len(matched_groups)
        paged_groups = matched_groups[offset : offset + limit]

        for grp, dec_val, dec_reason in paged_groups:
            # Fetch canonical or first member record revision
            member_link = db.query(GroupMemberModel).filter_by(group_id=grp.id).first()
            if member_link:
                s_rec = db.query(SourceRecordModel).filter_by(id=member_link.source_record_id).first()
                rev = (
                    db.query(RecordRevisionModel)
                    .filter_by(source_record_id=member_link.source_record_id)
                    .order_by(RecordRevisionModel.fetched_at.desc())
                    .first()
                )
                authors = _safe_json_list(rev.authors_json) if rev else []
                records_out.append(
                    PrismaStageRecordItem(
                        group_id=grp.id,
                        source_record_id=s_rec.id if s_rec else None,
                        title=rev.title if rev else f"Study Group {grp.id}",
                        authors=authors,
                        year=rev.year if rev else None,
                        journal=rev.journal if rev else None,
                        doi=rev.doi if rev else None,
                        pmid=s_rec.external_id if s_rec and (s_rec.source_namespace or "").lower() == "pubmed" else (rev.pmid if rev else None),
                        source_namespace=s_rec.source_namespace or s_rec.source if s_rec else None,
                        decision=dec_val,
                        decision_reason=dec_reason or ("Reason not recorded" if dec_val == "exclude" else None),
                        is_canonical=True,
                        is_duplicate=False,
                    )
                )

    return PrismaStageRecordsResponse(
        workspace_id=workspace_id,
        stage_key=stage_clean,
        stage_label=stage_label,
        total_count=total_count,
        limit=limit,
        offset=offset,
        records=records_out,
    )


def export_prisma_csv(
    db: Session,
    workspace_id: str,
    corpus_revision_id: str | None = None,
    query_version_id: str | None = None,
) -> str:
    """Generate a sanitized, auditable CSV export of PRISMA 2020 counts and exclusion reasons."""
    report = compute_prisma_flow_report(db, workspace_id, corpus_revision_id=corpus_revision_id, query_version_id=query_version_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header / Meta
    writer.writerow([sanitize_formula_injection(f"PRISMA 2020 Flow Report: {report.workspace_title}")])
    writer.writerow(["Generated At", report.generated_at.isoformat()])
    writer.writerow(["Workspace ID", sanitize_formula_injection(report.workspace_id)])
    writer.writerow(["Schema Version", report.schema_version])
    writer.writerow(["Reconciled", "Yes" if report.reconciliation.is_reconciled else "No"])
    writer.writerow([])

    # Section 1: PRISMA Flow Node Counts
    writer.writerow(["Stage", "PRISMA 2020 Node / Metric", "Count", "Notes"])
    st = report.stages
    writer.writerow(["Identification", "Records identified from databases", st.identification.total_database_records, "Total records imported from external bibliographic queries"])
    for src in st.identification.database_sources:
        writer.writerow(["Identification", f"  - Source: {src.source_name}", src.records_count, f"{len(src.search_execution_ids)} search batches"])
    writer.writerow(["Identification", "Total records identified before screening", st.identification.total_identified, "Total initial raw search records"])

    writer.writerow(["Pre-Screening", "Duplicate records removed", st.pre_screening.duplicate_records_removed, "Identified by DOI, PMID, and normalized title matching"])
    writer.writerow(["Pre-Screening", "Other records removed", st.pre_screening.other_records_removed, ""])
    writer.writerow(["Pre-Screening", "Net unique records entering screening", st.pre_screening.records_eligible_for_screening, "Unique study records eligible for title/abstract screening"])

    writer.writerow(["Screening", "Records screened by title/abstract", st.screening.records_screened, "Completed title/abstract screening"])
    writer.writerow(["Screening", "Records excluded at title/abstract", st.screening.records_excluded, "Excluded during title/abstract review"])
    writer.writerow(["Screening", "Records pending screening", st.screening.records_pending, "Unscreened records awaiting decision"])
    writer.writerow(["Screening", "Records with Maybe / uncertain status", st.screening.records_maybe, "Requires reviewer consensus or adjudication"])
    writer.writerow(["Screening", "Records with active conflicts", st.screening.records_conflicts, "Discrepancy across duplicate copies"])
    writer.writerow(["Screening", "Records advancing beyond title/abstract", st.screening.records_advancing, "Eligible studies advancing to inclusion/full-text"])

    writer.writerow(["Retrieval", "Reports sought for retrieval", st.retrieval.reports_sought_for_retrieval, st.retrieval.notes])
    writer.writerow(["Eligibility", "Full-text reports assessed for eligibility", st.eligibility.reports_assessed, st.eligibility.notes])

    writer.writerow(["Included", "Studies included in review", st.included.studies_included, "Unique clinical trials/studies meeting inclusion criteria"])
    writer.writerow(["Included", "Reports of included studies", st.included.reports_included, "Total individual publication reports included across all studies"])
    writer.writerow([])

    # Section 2: Exclusion Reasons Breakdown
    writer.writerow(["Exclusion Reasons Breakdown (Title/Abstract Screening)", "Count", "Percentage (%)"])
    if st.screening.exclusion_reasons:
        for ex in st.screening.exclusion_reasons:
            writer.writerow([sanitize_formula_injection(ex.reason), ex.count, f"{ex.percentage}%"])
    else:
        writer.writerow(["No exclusions recorded yet", 0, "0.0%"])
    writer.writerow([])

    # Section 3: Validation & Consistency Warnings
    writer.writerow(["Severity", "Code", "Stage", "Validation Message"])
    for issue in report.validation_issues:
        writer.writerow([issue.severity.value.upper(), issue.code, issue.stage.value, sanitize_formula_injection(issue.message)])

    return output.getvalue()


def save_prisma_snapshot(
    db: Session,
    workspace_id: str,
    payload: PrismaSnapshotCreateRequest,
    corpus_revision_id: str | None = None,
    query_version_id: str | None = None,
) -> PrismaSnapshotSummaryItem:
    """Create and persist an immutable PRISMA report snapshot for audit and publication reporting."""
    live_report = compute_prisma_flow_report(db, workspace_id, corpus_revision_id=corpus_revision_id, query_version_id=query_version_id)

    snapshot_id = str(uuid4())
    name = payload.name or f"PRISMA Snapshot {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"

    counts_data = live_report.stages.model_dump(mode="json")
    reasons_data = [r.model_dump(mode="json") for r in live_report.exclusion_reasons_summary]
    issues_data = [i.model_dump(mode="json") for i in live_report.validation_issues]

    snapshot = PrismaSnapshotModel(
        id=snapshot_id,
        workspace_id=workspace_id,
        corpus_revision_id=live_report.corpus_revision_id,
        query_version_id=None,
        name=name,
        notes=payload.notes,
        schema_version="2020.1",
        counts_json=json.dumps(counts_data),
        exclusion_reasons_json=json.dumps(reasons_data),
        validation_issues_json=json.dumps(issues_data),
        created_by=payload.actor_id,
        created_at=utc_now(),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    has_warnings = any(i.severity in (PrismaValidationSeverity.WARNING, PrismaValidationSeverity.ERROR) for i in live_report.validation_issues)

    return PrismaSnapshotSummaryItem(
        snapshot_id=snapshot.id,
        workspace_id=snapshot.workspace_id,
        name=snapshot.name or "PRISMA Snapshot",
        schema_version=snapshot.schema_version,
        corpus_revision_id=snapshot.corpus_revision_id,
        query_version_id=snapshot.query_version_id,
        total_identified=live_report.stages.identification.total_identified,
        duplicates_removed=live_report.stages.pre_screening.duplicate_records_removed,
        records_screened=live_report.stages.screening.records_screened,
        studies_included=live_report.stages.included.studies_included,
        has_warnings=has_warnings,
        created_by=snapshot.created_by,
        created_at=snapshot.created_at,
    )


def list_prisma_snapshots(
    db: Session,
    workspace_id: str,
) -> list[PrismaSnapshotSummaryItem]:
    """List all saved PRISMA report snapshots for a review workspace."""
    snapshots = (
        db.query(PrismaSnapshotModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(PrismaSnapshotModel.created_at.desc())
        .all()
    )

    items: list[PrismaSnapshotSummaryItem] = []
    for s in snapshots:
        try:
            counts = json.loads(s.counts_json)
            total_id = counts.get("identification", {}).get("total_identified", 0)
            dup_rem = counts.get("pre_screening", {}).get("duplicate_records_removed", 0)
            scr = counts.get("screening", {}).get("records_screened", 0)
            inc = counts.get("included", {}).get("studies_included", 0)
        except (json.JSONDecodeError, TypeError):
            total_id = dup_rem = scr = inc = 0

        try:
            issues = json.loads(s.validation_issues_json)
            has_warn = any(i.get("severity") in ("warning", "error") for i in issues if isinstance(i, dict))
        except (json.JSONDecodeError, TypeError):
            has_warn = False

        items.append(
            PrismaSnapshotSummaryItem(
                snapshot_id=s.id,
                workspace_id=s.workspace_id,
                name=s.name or f"Snapshot {s.created_at.strftime('%Y-%m-%d')}",
                schema_version=s.schema_version,
                corpus_revision_id=s.corpus_revision_id,
                query_version_id=s.query_version_id,
                total_identified=total_id,
                duplicates_removed=dup_rem,
                records_screened=scr,
                studies_included=inc,
                has_warnings=has_warn,
                created_by=s.created_by,
                created_at=s.created_at,
            )
        )
    return items


def get_prisma_snapshot(
    db: Session,
    workspace_id: str,
    snapshot_id: str,
) -> PrismaReportResponse:
    """Retrieve an immutable historical PRISMA report snapshot."""
    snapshot = (
        db.query(PrismaSnapshotModel)
        .filter_by(id=snapshot_id, workspace_id=workspace_id)
        .first()
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PRISMA snapshot '{snapshot_id}' not found.",
        )

    workspace = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    title = workspace.title if workspace else "Review Workspace"

    try:
        stages_dict = json.loads(snapshot.counts_json)
        stages = PrismaStages.model_validate(stages_dict)
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
        logger.error("Failed to parse snapshot stages JSON: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Corrupted snapshot counts payload",
        )

    try:
        issues_list = json.loads(snapshot.validation_issues_json)
        issues = [PrismaValidationIssue.model_validate(i) for i in issues_list]
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        issues = []

    try:
        reasons_list = json.loads(snapshot.exclusion_reasons_json)
        reasons = [PrismaExclusionReasonItem.model_validate(r) for r in reasons_list]
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        reasons = []

    # Compute reconciliation
    st = stages
    id_balance = st.identification.total_identified - (st.pre_screening.total_removed + st.pre_screening.records_eligible_for_screening)
    screen_balance = st.pre_screening.records_eligible_for_screening - (
        st.screening.records_screened + st.screening.records_pending + st.screening.records_maybe + st.screening.records_conflicts
    )
    is_reconciled = (id_balance == 0) and (screen_balance == 0)

    reconciliation = PrismaReconciliationSummary(
        is_reconciled=is_reconciled,
        identification_balance=id_balance,
        screening_balance=screen_balance,
        discrepancy_explanation=None if is_reconciled else f"Historical discrepancy: {id_balance}/{screen_balance}",
    )

    return PrismaReportResponse(
        workspace_id=workspace_id,
        workspace_title=f"{title} [{snapshot.name}]",
        generated_at=snapshot.created_at,
        is_live=False,
        snapshot_id=snapshot.id,
        corpus_revision_id=snapshot.corpus_revision_id,
        query_version_id=snapshot.query_version_id,
        schema_version=snapshot.schema_version,
        stages=stages,
        validation_issues=issues,
        reconciliation=reconciliation,
        exclusion_reasons_summary=reasons,
    )
