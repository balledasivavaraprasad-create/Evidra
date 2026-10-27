"""Tests for PICO result validation and invariant checking."""
import hashlib

from app.contracts.enums import PicoLabel
from app.contracts.models import PicoResult, PicoSpan
from app.pico.validator import compute_text_hash, validate_pico_result


def test_validator_accepts_valid_result():
    text = "In adults with type 2 diabetes, metformin lowered HbA1c compared with placebo."
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    spans = [
        PicoSpan(label=PicoLabel.P, start_cp=3, end_cp=30, quote="adults with type 2 diabetes", provenance="rule:v1"),
        PicoSpan(label=PicoLabel.I, start_cp=32, end_cp=41, quote="metformin", provenance="rule:v1"),
        PicoSpan(label=PicoLabel.C, start_cp=70, end_cp=77, quote="placebo", provenance="rule:v1"),
        PicoSpan(label=PicoLabel.O, start_cp=50, end_cp=55, quote="HbA1c", provenance="rule:v1"),
    ]

    result = PicoResult(
        record_revision_id="rec-001",
        content_hash=text_hash,
        spans=spans,
        has_population=True,
        has_intervention=True,
        has_comparator=True,
        has_outcome=True,
        method_version="pico:v1.0",
    )

    is_valid, errors = validate_pico_result(result, text)
    assert is_valid
    assert errors == []


def test_validator_detects_hash_mismatch():
    text = "Metformin trial in diabetes."
    result = PicoResult(
        record_revision_id="rec-001",
        content_hash="bad_stale_hash",
        spans=[],
        has_population=False,
        has_intervention=False,
        has_comparator=False,
        has_outcome=False,
        method_version="pico:v1.0",
    )

    is_valid, errors = validate_pico_result(result, text)
    assert not is_valid
    assert any("Content hash mismatch" in e for e in errors)


def test_validator_detects_quote_mismatch():
    text = "Metformin monotherapy."
    text_hash = compute_text_hash(text)

    # Offset points to 'Metformin' (0:9), but quote says 'Placebo'
    spans = [
        PicoSpan(label=PicoLabel.I, start_cp=0, end_cp=9, quote="Placebo", provenance="rule:v1"),
    ]

    result = PicoResult(
        record_revision_id="rec-001",
        content_hash=text_hash,
        spans=spans,
        has_population=False,
        has_intervention=True,
        has_comparator=False,
        has_outcome=False,
        method_version="pico:v1.0",
    )

    is_valid, errors = validate_pico_result(result, text)
    assert not is_valid
    assert any("quote mismatch" in e for e in errors)


def test_validator_detects_flag_inconsistency():
    text = "Metformin monotherapy."
    text_hash = compute_text_hash(text)

    spans = [
        PicoSpan(label=PicoLabel.I, start_cp=0, end_cp=9, quote="Metformin", provenance="rule:v1"),
    ]

    # Flag says has_comparator=True, but spans list has no C span
    result = PicoResult(
        record_revision_id="rec-001",
        content_hash=text_hash,
        spans=spans,
        has_population=False,
        has_intervention=True,
        has_comparator=True,  # Inconsistent!
        has_outcome=False,
        method_version="pico:v1.0",
    )

    is_valid, errors = validate_pico_result(result, text)
    assert not is_valid
    assert any("has_comparator flag (True) does not match" in e for e in errors)


def test_validator_handles_absent_abstract():
    # Empty result with None text passes
    result_empty = PicoResult(
        record_revision_id="rec-empty",
        content_hash="",
        spans=[],
        has_population=False,
        has_intervention=False,
        has_comparator=False,
        has_outcome=False,
        method_version="pico:v1.0",
    )
    is_valid, errors = validate_pico_result(result_empty, None)
    assert is_valid
    assert errors == []

    # Non-empty spans when abstract is None must fail
    result_spurious = PicoResult(
        record_revision_id="rec-bad",
        content_hash="",
        spans=[
            PicoSpan(label=PicoLabel.P, start_cp=0, end_cp=5, quote="Adult", provenance="rule:v1")
        ],
        has_population=True,
        has_intervention=False,
        has_comparator=False,
        has_outcome=False,
        method_version="pico:v1.0",
    )
    is_valid, errors = validate_pico_result(result_spurious, None)
    assert not is_valid
    assert any("abstract_text is absent/empty" in e for e in errors)
