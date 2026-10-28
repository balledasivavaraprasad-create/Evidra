"""Unit tests for Evidence Passport deterministic quotation validation engine."""
from __future__ import annotations

from app.contracts.enums import (
    EvidenceClaimType,
    EvidenceValidationStatus,
)
from app.pico.validator import compute_text_hash
from app.services.evidence_passport import (
    find_quote_occurrences,
    validate_quote_against_source,
)

ABSTRACT_SAMPLE = (
    "A total of 320 adult patients with type 2 diabetes mellitus were randomized. "
    "Patients received metformin 1000 mg twice daily or matching placebo for 24 weeks. "
    "The primary outcome was change in HbA1c from baseline. "
    "Significant reduction in HbA1c was observed in the metformin cohort (-1.2% vs -0.1%, p < 0.001). "
    "No treatment-related serious adverse events were reported in either group."
)


def test_find_quote_occurrences():
    occurrences = find_quote_occurrences(ABSTRACT_SAMPLE, "metformin")
    assert len(occurrences) == 2
    for start, end in occurrences:
        assert ABSTRACT_SAMPLE[start:end] == "metformin"


def test_exact_quotation_and_offsets_verified():
    quote = "adult patients with type 2 diabetes mellitus"
    start_cp = ABSTRACT_SAMPLE.find(quote)
    end_cp = start_cp + len(quote)
    fp = compute_text_hash(ABSTRACT_SAMPLE)

    status, msg, s, e = validate_quote_against_source(
        quote=quote,
        start_cp=start_cp,
        end_cp=end_cp,
        source_text=ABSTRACT_SAMPLE,
        stored_fingerprint=fp,
        claim_type=EvidenceClaimType.POPULATION,
        claim_value="Adults with type 2 diabetes",
    )

    assert status == EvidenceValidationStatus.VERIFIED
    assert s == start_cp
    assert e == end_cp
    assert "verified against source text" in msg


def test_single_occurrence_reanchors_missing_offsets():
    quote = "change in HbA1c from baseline"
    fp = compute_text_hash(ABSTRACT_SAMPLE)

    # Provide None for offsets
    status, msg, s, e = validate_quote_against_source(
        quote=quote,
        start_cp=None,
        end_cp=None,
        source_text=ABSTRACT_SAMPLE,
        stored_fingerprint=fp,
        claim_type=EvidenceClaimType.OUTCOME,
        claim_value="HbA1c change",
    )

    assert status == EvidenceValidationStatus.VERIFIED
    assert s is not None and e is not None
    assert ABSTRACT_SAMPLE[s:e] == quote
    assert "anchored to single match" in msg


def test_mismatched_quote_detected():
    fabricated_quote = "Patients received insulin glargine injections"
    fp = compute_text_hash(ABSTRACT_SAMPLE)

    status, msg, _s, _e = validate_quote_against_source(
        quote=fabricated_quote,
        start_cp=0,
        end_cp=40,
        source_text=ABSTRACT_SAMPLE,
        stored_fingerprint=fp,
        claim_type=EvidenceClaimType.INTERVENTION,
        claim_value="Insulin glargine",
    )

    assert status == EvidenceValidationStatus.MISMATCHED
    assert "does not exist in current stored source text" in msg


def test_stale_fingerprint_detected_when_text_changes():
    quote = "placebo for 24 weeks"
    start_cp = ABSTRACT_SAMPLE.find(quote)
    end_cp = start_cp + len(quote)
    stale_fp = "0000000000000000000000000000000000000000000000000000000000000000"

    status, msg, _s, _e = validate_quote_against_source(
        quote=quote,
        start_cp=start_cp,
        end_cp=end_cp,
        source_text=ABSTRACT_SAMPLE,
        stored_fingerprint=stale_fp,
        claim_type=EvidenceClaimType.COMPARATOR,
        claim_value="Placebo",
    )

    assert status == EvidenceValidationStatus.STALE
    assert "Source text fingerprint changed" in msg


def test_missing_source_text_handled():
    status, msg, _s, _e = validate_quote_against_source(
        quote="Any quote",
        start_cp=0,
        end_cp=10,
        source_text=None,
        stored_fingerprint=None,
        claim_type=EvidenceClaimType.POPULATION,
        claim_value="Adults",
    )

    assert status == EvidenceValidationStatus.MISSING_SOURCE
    assert "unavailable or empty" in msg


def test_absent_comparator_explicit_insufficient_evidence():
    status, msg, _s, _e = validate_quote_against_source(
        quote="",
        start_cp=None,
        end_cp=None,
        source_text=ABSTRACT_SAMPLE,
        stored_fingerprint=compute_text_hash(ABSTRACT_SAMPLE),
        claim_type=EvidenceClaimType.COMPARATOR,
        claim_value="Not found in abstract",
    )

    assert status == EvidenceValidationStatus.INSUFFICIENT_EVIDENCE
    assert "No active comparator" in msg


def test_ambiguous_quotation_with_conflicting_offsets_requires_review():
    # 'metformin' appears twice in abstract
    quote = "metformin"
    fp = compute_text_hash(ABSTRACT_SAMPLE)

    # Provide an invalid offset slice (e.g. [10:19] which does not equal 'metformin')
    status, msg, _s, _e = validate_quote_against_source(
        quote=quote,
        start_cp=10,
        end_cp=19,
        source_text=ABSTRACT_SAMPLE,
        stored_fingerprint=fp,
        claim_type=EvidenceClaimType.INTERVENTION,
        claim_value="Metformin",
    )

    assert status == EvidenceValidationStatus.NEEDS_REVIEW
    assert "appears 2 times" in msg
    assert "ambiguity" in msg
