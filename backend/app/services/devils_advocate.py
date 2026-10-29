"""Devil's Advocate Reviewer domain service for challenging fragile literature exclusions."""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import (
    ChallengeDisposition,
    ChallengeRecommendation,
    DecisionEventType,
    EffectiveDecisionState,
    EligibilityStatus,
    RadarEvidenceStatus,
    VulnerabilityFlag,
)
from app.contracts.models import (
    CounterArgumentItem,
    DevilsAdvocateChallengeResponse,
    DevilsAdvocateDashboardItem,
    DevilsAdvocateDashboardResponse,
    DevilsAdvocateDispositionRequest,
    DevilsAdvocateGenerateRequest,
)
from app.db.models import (
    DevilsAdvocateChallengeModel,
    EvidencePassportModel,
    GroupMemberModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.corpus import project_effective_group_decision

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def _get_next_event_sequence(db: Session, workspace_id: str) -> int:
    """Get next monotonically increasing event sequence for workspace."""
    max_seq = (
        db.query(func.max(ReviewEventModel.sequence))
        .filter_by(workspace_id=workspace_id)
        .scalar()
    )
    return (max_seq or 0) + 1


def _resolve_paper_group(
    db: Session,
    workspace_id: str,
    group_id: str,
) -> tuple[PaperGroupModel, RecordRevisionModel]:
    """Resolve a paper group and its most recent representative record revision."""
    group = (
        db.query(PaperGroupModel)
        .filter_by(workspace_id=workspace_id, id=group_id)
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' not found in workspace '{workspace_id}'",
        )

    member = (
        db.query(GroupMemberModel, SourceRecordModel)
        .join(SourceRecordModel, SourceRecordModel.id == GroupMemberModel.source_record_id)
        .filter(GroupMemberModel.group_id == group.id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper group '{group_id}' contains no member source records",
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


def _extract_counter_arguments(
    title: str,
    abstract_text: str,
    exclusion_reason: str | None,
    passports: list[EvidencePassportModel],
) -> tuple[list[CounterArgumentItem], list[VulnerabilityFlag], float, str]:
    """Analyze abstract, title, and exclusion rationale to build counter-arguments and vulnerability score."""
    text = (abstract_text or "").strip()
    title_text = (title or "").strip()
    combined_text = f"{title_text} {text}".strip()
    reason = (exclusion_reason or "").lower().strip()

    counter_arguments: list[CounterArgumentItem] = []
    flags: set[VulnerabilityFlag] = set()
    vulnerability_score = 0.10

    # 1. Rationale brevity & vagueness check
    if not reason or len(reason) < 15 or reason in {"no", "irrelevant", "exclude", "not relevant", "wrong study"}:
        flags.add(VulnerabilityFlag.WEAK_RATIONALE)
        vulnerability_score += 0.25

    # 2. Abstract-only limitation check
    # Many exclusions cite lack of granular trial parameters that only appear in full text
    abstract_limitation_keywords = ["dose", "protocol", "dosing", "secondary", "adverse event", "subgroup", "safety", "long-term", "pharmacokinetic"]
    if any(k in reason for k in abstract_limitation_keywords) or (len(text) < 600 and text):
        flags.add(VulnerabilityFlag.ABSTRACT_ONLY_LIMITATION)
        vulnerability_score += 0.15

    # 3. Comparator Analysis
    if "comparator" in reason or "control" in reason or "no comparison" in reason or "single arm" in reason:
        # Check if text contains comparator or control indicators
        match = re.search(r'([^.?!;]*\b(?:placebo|standard of care|active comparator|control group|versus|vs\.?|compared to|randomized|comparison)\b[^.?!;]*)', combined_text, re.IGNORECASE)
        if match:
            quote = match.group(0).strip()
            counter_arguments.append(
                CounterArgumentItem(
                    argument="Source text mentions a comparator, control group, or comparative design.",
                    supporting_quote=quote,
                    source_field="abstract" if quote in text else "title",
                    relevance_aspect="comparator",
                    confidence=0.9,
                )
            )
            flags.add(VulnerabilityFlag.INDIRECT_COMPARATOR)
            flags.add(VulnerabilityFlag.COUNTER_EVIDENCE_FOUND)
            vulnerability_score += 0.35
        else:
            # If abstract only, point out absence in abstract is not absence in full trial
            flags.add(VulnerabilityFlag.ABSTRACT_ONLY_LIMITATION)
            vulnerability_score += 0.10

    # 4. Population & Subgroup Analysis
    if "population" in reason or "pediatric" in reason or "adult" in reason or "wrong sample" in reason or "age" in reason:
        # Check if text mentions patients, cohorts, or specific populations
        match = re.search(r'([^.?!;]*\b(?:patients|participants|subjects|cohort|subgroup|adults|children|aged|enrolled|eligible)\b[^.?!;]*)', combined_text, re.IGNORECASE)
        if match:
            quote = match.group(0).strip()
            counter_arguments.append(
                CounterArgumentItem(
                    argument="Target patient cohort or potential subgroup reported in text.",
                    supporting_quote=quote,
                    source_field="abstract" if quote in text else "title",
                    relevance_aspect="population",
                    confidence=0.85,
                )
            )
            flags.add(VulnerabilityFlag.OVERLOOKED_SUBGROUP)
            flags.add(VulnerabilityFlag.COUNTER_EVIDENCE_FOUND)
            vulnerability_score += 0.20

    # 5. Outcome & Efficacy Analysis
    if "outcome" in reason or "endpoint" in reason or "no effect" in reason:
        match = re.search(r'([^.?!;]*\b(?:remission|survival|mortality|response rate|efficacy|significant|improved|outcome|resolution)\b[^.?!;]*)', combined_text, re.IGNORECASE)
        if match:
            quote = match.group(0).strip()
            counter_arguments.append(
                CounterArgumentItem(
                    argument="Clinical endpoints or surrogate outcome metrics reported.",
                    supporting_quote=quote,
                    source_field="abstract" if quote in text else "title",
                    relevance_aspect="outcome",
                    confidence=0.85,
                )
            )
            flags.add(VulnerabilityFlag.SURROGATE_OUTCOME)
            flags.add(VulnerabilityFlag.COUNTER_EVIDENCE_FOUND)
            vulnerability_score += 0.20

    # 6. Methodological Rigor / Trial Quality Signals
    method_match = re.search(r'([^.?!;]*\b(?:randomized|double-blind|clinical trial|phase [1234]|prospective|multicenter)\b[^.?!;]*)', combined_text, re.IGNORECASE)
    if method_match:
        m_quote = method_match.group(0).strip()
        if not any(ca.supporting_quote == m_quote for ca in counter_arguments):
            counter_arguments.append(
                CounterArgumentItem(
                    argument="High-rigor prospective clinical trial methodology identified.",
                    supporting_quote=m_quote,
                    source_field="abstract" if m_quote in text else "title",
                    relevance_aspect="methodology",
                    confidence=0.95,
                )
            )
            flags.add(VulnerabilityFlag.COUNTER_EVIDENCE_FOUND)
            vulnerability_score += 0.20

    # 7. Integration with Evidence Passports & Radar
    for p in passports:
        if p.radar_status == RadarEvidenceStatus.UNCERTAIN.value or p.uncertainty_note:
            flags.add(VulnerabilityFlag.UNCERTAIN_PICO_ELEMENT)
            vulnerability_score += 0.15
            break

    # Cap vulnerability score
    vulnerability_score = min(max(round(vulnerability_score, 2), 0.05), 0.98)

    # 8. Critique Formulation
    if vulnerability_score >= 0.60:
        critique = (
            f"High risk of false exclusion: The stated exclusion rationale ('{exclusion_reason or 'unspecified'}') "
            f"is directly challenged by affirmative evidence found in the study text. "
            f"Notable trial characteristics and clinical endpoints suggest this paper should not be discarded prematurely. "
            f"Recommended to reconsider for inclusion or full-text review."
        )
    elif vulnerability_score >= 0.35:
        critique = (
            f"Moderate exclusion vulnerability: While some exclusion criteria may be cited, "
            f"textual limitations (such as abstract-only evaluation) or ambiguous cohort definitions create uncertainty. "
            f"Escalation to human consensus or dual-screening is recommended."
        )
    else:
        critique = (
            f"Exclusion stands: The exclusion rationale ('{exclusion_reason or 'unspecified'}') is consistent with "
            f"the examined text. Counter-arguments identified do not establish sufficient eligibility to overturn exclusion."
        )

    return counter_arguments, list(flags), vulnerability_score, critique


def get_or_generate_challenge(
    db: Session,
    workspace_id: str,
    group_id: str,
    payload: DevilsAdvocateGenerateRequest | None = None,
    persist: bool = True,
) -> DevilsAdvocateChallengeResponse:
    """Retrieve existing active challenge or generate a new Devil's Advocate assessment.

    With ``persist=False`` (a GET) a missing challenge is computed for the response but not saved.
    Processing and the explicit generate action save it.
    """
    group, rep_rev = _resolve_paper_group(db, workspace_id, group_id)

    force_refresh = payload.force_refresh if payload else False

    # Check for active existing challenge
    existing = (
        db.query(DevilsAdvocateChallengeModel)
        .filter_by(workspace_id=workspace_id, group_id=group.id, is_active=True)
        .order_by(DevilsAdvocateChallengeModel.created_at.desc())
        .first()
    )

    if existing and not force_refresh:
        return _model_to_response(existing)

    # Resolve effective decision and exclusion rationale
    eff_decision, latest_event, screen_res, _ = project_effective_group_decision(db, group.id)

    proposed_decision = (payload.proposed_decision if payload and payload.proposed_decision else eff_decision.value).lower()
    exclusion_reason = payload.exclusion_reason if payload and payload.exclusion_reason else None

    if not exclusion_reason:
        if latest_event and latest_event.reason:
            exclusion_reason = latest_event.reason
        elif latest_event and latest_event.payload_json:
            try:
                pl = json.loads(latest_event.payload_json)
                exclusion_reason = pl.get("notes") or pl.get("reason")
            except (json.JSONDecodeError, ValueError):
                pass
        elif screen_res and screen_res.rationale:
            exclusion_reason = screen_res.rationale

    # Fetch active evidence passports for radar/uncertainty context
    passports = (
        db.query(EvidencePassportModel)
        .filter_by(workspace_id=workspace_id, paper_group_id=group.id)
        .filter(EvidencePassportModel.superseded_by_id.is_(None))
        .all()
    )

    # Run Devil's Advocate Challenge analysis
    counter_args, flags, vuln_score, critique = _extract_counter_arguments(
        title=rep_rev.title or "",
        abstract_text=rep_rev.abstract_text or "",
        exclusion_reason=exclusion_reason,
        passports=passports,
    )

    # Determine recommendation
    if vuln_score >= 0.60:
        recommendation = ChallengeRecommendation.RECONSIDER_EXCLUSION
    elif vuln_score >= 0.35:
        recommendation = ChallengeRecommendation.NEEDS_HUMAN_REVIEW
    else:
        recommendation = ChallengeRecommendation.UPHOLD_EXCLUSION

    # Deactivate existing challenges if refreshing
    if persist and existing and force_refresh:
        existing.is_active = False
        existing.updated_at = utc_now()

    # Create new challenge record
    challenge = DevilsAdvocateChallengeModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group.id,
        record_revision_id=rep_rev.id,
        proposed_decision=proposed_decision,
        original_exclusion_reason=exclusion_reason,
        recommendation=recommendation.value,
        vulnerability_score=vuln_score,
        critique=critique,
        counter_arguments_json=json.dumps([ca.model_dump() for ca in counter_args]),
        vulnerability_flags_json=json.dumps([f.value for f in flags]),
        disposition=ChallengeDisposition.PENDING.value,
        is_active=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    if persist:
        db.add(challenge)
        db.commit()

    return _model_to_response(challenge)


def record_challenge_disposition(
    db: Session,
    workspace_id: str,
    group_id: str,
    payload: DevilsAdvocateDispositionRequest,
) -> DevilsAdvocateChallengeResponse:
    """Record human reviewer response to a Devil's Advocate challenge without silent overrides."""
    group, _ = _resolve_paper_group(db, workspace_id, group_id)

    challenge = (
        db.query(DevilsAdvocateChallengeModel)
        .filter_by(workspace_id=workspace_id, group_id=group.id, is_active=True)
        .order_by(DevilsAdvocateChallengeModel.created_at.desc())
        .first()
    )
    if not challenge:
        get_or_generate_challenge(db, workspace_id, group_id)
        challenge = (
            db.query(DevilsAdvocateChallengeModel)
            .filter_by(workspace_id=workspace_id, group_id=group.id, is_active=True)
            .order_by(DevilsAdvocateChallengeModel.created_at.desc())
            .first()
        )
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active Devil's Advocate challenge found for paper group '{group_id}'",
        )

    # 1. Update challenge disposition
    challenge.disposition = payload.disposition.value
    challenge.disposition_notes = payload.notes
    challenge.disposition_by = payload.actor_id
    challenge.disposed_at = utc_now()
    challenge.updated_at = utc_now()

    # 2. Append-only audit record in review_events
    seq = _get_next_event_sequence(db, workspace_id)
    disp_event = ReviewEventModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        group_id=group.id,
        sequence=seq,
        actor_id=payload.actor_id,
        event_type=DecisionEventType.DEVILS_ADVOCATE_DISPOSITION.value,
        payload_json=json.dumps({
            "challenge_id": challenge.id,
            "disposition": payload.disposition.value,
            "recommendation": challenge.recommendation,
            "vulnerability_score": challenge.vulnerability_score,
            "notes": payload.notes,
            "conceded_decision": payload.conceded_decision.value if payload.conceded_decision else None,
        }),
        reason=payload.notes,
        created_at=utc_now(),
    )
    db.add(disp_event)
    db.flush()

    # 3. If reviewer CONCEDED and specified a new decision (e.g. Include / Maybe), update group decision
    if payload.disposition == ChallengeDisposition.CONCEDED and payload.conceded_decision:
        seq2 = _get_next_event_sequence(db, workspace_id)
        decision_event = ReviewEventModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            group_id=group.id,
            sequence=seq2,
            actor_id=payload.actor_id,
            event_type=DecisionEventType.SCREEN_DECISION.value,
            payload_json=json.dumps({
                "status": payload.conceded_decision.value,
                "decision": payload.conceded_decision.value,
                "source": "devils_advocate_concession",
                "challenge_id": challenge.id,
            }),
            reason=f"Conceded to Devil's Advocate challenge: {payload.notes or 'Reconsidered after challenge'}",
            created_at=utc_now(),
        )
        db.add(decision_event)
        group.row_version += 1

    db.commit()
    return _model_to_response(challenge)


def get_workspace_challenge_dashboard(
    db: Session,
    workspace_id: str,
    disposition_filter: str | None = None,
    high_vulnerability_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> DevilsAdvocateDashboardResponse:
    """Compute review-wide Devil's Advocate dashboard metrics and prioritized challenge ledger."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # Query all active challenges for workspace
    q = (
        db.query(DevilsAdvocateChallengeModel, PaperGroupModel, RecordRevisionModel)
        .join(PaperGroupModel, DevilsAdvocateChallengeModel.group_id == PaperGroupModel.id)
        .join(RecordRevisionModel, DevilsAdvocateChallengeModel.record_revision_id == RecordRevisionModel.id)
        .filter(DevilsAdvocateChallengeModel.workspace_id == workspace_id)
        .filter(DevilsAdvocateChallengeModel.is_active.is_(True))
    )

    all_rows = q.order_by(DevilsAdvocateChallengeModel.vulnerability_score.desc()).all()

    total_challenged = len(all_rows)
    pending_count = 0
    high_vuln_count = 0
    conceded_count = 0
    upheld_count = 0
    dismissed_count = 0

    dashboard_items: list[DevilsAdvocateDashboardItem] = []

    for chal, grp, rev in all_rows:
        if chal.disposition == ChallengeDisposition.PENDING.value:
            pending_count += 1
        elif chal.disposition == ChallengeDisposition.CONCEDED.value:
            conceded_count += 1
        elif chal.disposition == ChallengeDisposition.UPHELD.value:
            upheld_count += 1
        elif chal.disposition == ChallengeDisposition.DISMISSED.value:
            dismissed_count += 1

        if chal.vulnerability_score >= 0.60:
            high_vuln_count += 1

        try:
            counter_args = json.loads(chal.counter_arguments_json)
        except (json.JSONDecodeError, TypeError):
            counter_args = []

        try:
            flags = [VulnerabilityFlag(f) for f in json.loads(chal.vulnerability_flags_json)]
        except (json.JSONDecodeError, TypeError, ValueError):
            flags = []

        try:
            authors = json.loads(rev.authors_json) if rev.authors_json else []
        except (json.JSONDecodeError, TypeError):
            authors = []

        dashboard_items.append(
            DevilsAdvocateDashboardItem(
                challenge_id=chal.id,
                group_id=grp.id,
                title=rev.title or "Untitled Study",
                authors=authors,
                year=rev.year,
                pmid=rev.pmid,
                doi=rev.doi,
                proposed_decision=chal.proposed_decision,
                original_exclusion_reason=chal.original_exclusion_reason,
                recommendation=ChallengeRecommendation(chal.recommendation),
                vulnerability_score=chal.vulnerability_score,
                vulnerability_flags=flags,
                disposition=ChallengeDisposition(chal.disposition),
                counter_argument_count=len(counter_args),
                created_at=chal.created_at,
            )
        )

    # Calculate concession rate
    resolved_total = conceded_count + upheld_count + dismissed_count
    concession_rate = round((conceded_count / float(resolved_total or 1)) * 100, 1) if resolved_total > 0 else 0.0

    # Filtering
    filtered = dashboard_items
    if disposition_filter:
        filtered = [item for item in filtered if item.disposition.value == disposition_filter]
    if high_vulnerability_only:
        filtered = [item for item in filtered if item.vulnerability_score >= 0.60]

    paginated = filtered[offset : offset + limit]

    return DevilsAdvocateDashboardResponse(
        workspace_id=workspace_id,
        total_challenged=total_challenged,
        pending_challenges=pending_count,
        high_vulnerability_count=high_vuln_count,
        conceded_count=conceded_count,
        upheld_count=upheld_count,
        dismissed_count=dismissed_count,
        concession_rate=concession_rate,
        false_exclusions_prevented=conceded_count,
        challenges=paginated,
    )


def _model_to_response(model: DevilsAdvocateChallengeModel) -> DevilsAdvocateChallengeResponse:
    """Convert database model to contract response."""
    try:
        raw_args = json.loads(model.counter_arguments_json)
        counter_args = [CounterArgumentItem(**arg) for arg in raw_args]
    except (json.JSONDecodeError, TypeError, ValueError):
        counter_args = []

    try:
        raw_flags = json.loads(model.vulnerability_flags_json)
        flags = [VulnerabilityFlag(f) for f in raw_flags]
    except (json.JSONDecodeError, TypeError, ValueError):
        flags = []

    return DevilsAdvocateChallengeResponse(
        id=model.id,
        workspace_id=model.workspace_id,
        group_id=model.group_id,
        record_revision_id=model.record_revision_id,
        proposed_decision=model.proposed_decision,
        original_exclusion_reason=model.original_exclusion_reason,
        recommendation=ChallengeRecommendation(model.recommendation),
        vulnerability_score=model.vulnerability_score,
        critique=model.critique,
        counter_arguments=counter_args,
        vulnerability_flags=flags,
        disposition=ChallengeDisposition(model.disposition),
        disposition_notes=model.disposition_notes,
        disposition_by=model.disposition_by,
        disposed_at=model.disposed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
