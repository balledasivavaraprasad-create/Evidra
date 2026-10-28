"""Screening engine implementation evaluating versioned review criteria (B02)."""
from __future__ import annotations

import hashlib
import json

from app.contracts.enums import (
    CriterionVerdict,
    EligibilityStatus,
    ScreeningEvidenceSource,
)
from app.contracts.models import (
    CriteriaVersionResponse,
    CriterionDefinition,
    CriterionEvidence,
    RecordRevisionResponse,
    ScreenResult,
)
from app.screening.defaults import METHOD_VERSION
from app.screening.rules import RULE_EVALUATORS, evaluate_keywords


def compute_screening_fingerprint(
    record: RecordRevisionResponse,
    criteria: CriteriaVersionResponse,
    method_version: str = METHOD_VERSION,
) -> str:
    """Calculate reproducible SHA-256 fingerprint for a screening evaluation.

    Binds record identity & content hash, active criteria version hash,
    and evaluator method version to ensure invalidation upon any change.
    """
    payload = {
        "record_id": record.id,
        "content_hash": record.content_hash,
        "criteria_version_id": criteria.id,
        "criteria_content_hash": criteria.content_hash,
        "method_version": method_version,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ScreeningEngine:
    """Deterministic, metadata-first screening engine implementing ScreeningPort."""

    def __init__(self, method_version: str = METHOD_VERSION) -> None:
        self.method_version = method_version

    def evaluate_criterion(
        self,
        record: RecordRevisionResponse,
        criterion: CriterionDefinition,
    ) -> CriterionEvidence:
        """Evaluate a single criterion against a normalized record revision."""
        # Rules with keywords (built from the review's question, or edited by the reviewer) are
        # evaluated by their keywords. The id-based evaluators below remain only for older
        # criteria versions that carry no keywords.
        if criterion.keywords or criterion.exclude_keywords:
            return evaluate_keywords(criterion, record)

        evaluator = RULE_EVALUATORS.get(criterion.id)
        if evaluator is not None:
            return evaluator(record, criterion)

        # Fallback for unrecognized custom criterion
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.UNKNOWN,
            reason_code="UNRECOGNIZED_CRITERION",
            explanation=f"No automated heuristic available for criterion '{criterion.id}'; requires manual review",
            evidence_snippet=None,
            source=ScreeningEvidenceSource.RULE,
            method_version=self.method_version,
        )

    def screen_record(
        self,
        record: RecordRevisionResponse,
        criteria: CriteriaVersionResponse,
    ) -> ScreenResult:
        """Evaluate all active criteria for a record revision and compute aggregate eligibility."""
        criteria_evidence: list[CriterionEvidence] = []
        failing_reasons: list[str] = []
        has_unknown = False

        for criterion in criteria.criteria:
            evidence = self.evaluate_criterion(record, criterion)
            criteria_evidence.append(evidence)

            if evidence.verdict == CriterionVerdict.FAIL:
                failing_reasons.append(evidence.reason_code)
            elif evidence.verdict == CriterionVerdict.UNKNOWN:
                has_unknown = True

        # Aggregate decision rules:
        # 1. Any active failure yields Exclude with all failure reason codes.
        # 2. If no failures and no unknowns -> Include.
        # 3. Otherwise (no failures, but at least one unknown) -> Maybe (honest abstention).
        if failing_reasons:
            status = EligibilityStatus.EXCLUDE
            reasons = failing_reasons
        elif has_unknown:
            status = EligibilityStatus.MAYBE
            reasons = []
        else:
            status = EligibilityStatus.INCLUDE
            reasons = []

        return ScreenResult(
            group_id=None,
            record_revision_id=record.id,
            status=status,
            reasons=reasons,
            criteria_evidence=criteria_evidence,
            method_version=self.method_version,
        )


def screen_record(
    record: RecordRevisionResponse,
    criteria: CriteriaVersionResponse,
    method_version: str = METHOD_VERSION,
) -> ScreenResult:
    """Convenience functional interface for screening a record."""
    engine = ScreeningEngine(method_version=method_version)
    return engine.screen_record(record, criteria)
