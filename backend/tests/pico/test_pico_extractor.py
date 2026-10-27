"""Comprehensive tests for deterministic PICO baseline extractor."""
from app.contracts.enums import PicoLabel
from app.contracts.models import RecordRevisionResponse
from app.contracts.ports import PicoPort
from app.pico.extractor import RuleBasedPicoExtractor, extract_pico_spans
from app.pico.validator import validate_pico_result
from tests.fixtures.synthetic_records import (
    RECORD_EXACT_EUROPEPMC,
    RECORD_EXACT_PUBMED,
    RECORD_MISSING_ABSTRACT,
    RECORD_REPEATED_PHRASES,
    RECORD_SINGLE_ARM_NO_COMPARATOR,
    RECORD_UNICODE_SPANS,
)


def test_extractor_satisfies_pico_port():
    """Verify that RuleBasedPicoExtractor implements PicoPort runtime checkable protocol."""
    extractor = RuleBasedPicoExtractor()
    assert isinstance(extractor, PicoPort)


def test_exact_pubmed_fixture_extraction():
    """Test standard clinical RCT record with all 4 PICO components present."""
    record = RecordRevisionResponse(**RECORD_EXACT_PUBMED)
    extractor = RuleBasedPicoExtractor()
    result = extractor.extract_pico_spans(record)

    assert result.record_revision_id == record.id
    assert result.has_population is True
    assert result.has_intervention is True
    assert result.has_comparator is True
    assert result.has_outcome is True
    assert len(result.spans) >= 4

    # Validate every quote strictly equals the text slice
    for span in result.spans:
        assert record.abstract_text[span.start_cp : span.end_cp] == span.quote

    # Validate against domain validator
    is_valid, errors = validate_pico_result(result, record.abstract_text)
    assert is_valid, f"Validation errors: {errors}"


def test_unicode_and_non_bmp_span_integrity():
    """Test abstract with Greek letters (β-cell, α-glucosidase) and non-BMP emoji (💉)."""
    record = RecordRevisionResponse(**RECORD_UNICODE_SPANS)
    result = extract_pico_spans(record)

    assert result.has_population is True
    assert result.has_intervention is True
    assert result.has_comparator is True
    assert result.has_outcome is True

    # Check Greek character spans
    greek_outcomes = [s for s in result.spans if "β-cell" in s.quote or "α-glucosidase" in s.quote]
    assert len(greek_outcomes) > 0

    # Ensure every span slice exactly matches without offset drift caused by the emoji
    for span in result.spans:
        slice_text = record.abstract_text[span.start_cp : span.end_cp]
        assert slice_text == span.quote, f"Span {span} did not match slice '{slice_text}'"

    is_valid, errors = validate_pico_result(result, record.abstract_text)
    assert is_valid, f"Validation errors: {errors}"


def test_repeated_phrases_disambiguation():
    """Test that multiple occurrences of 'metformin' receive distinct, non-overlapping exact offsets."""
    record = RecordRevisionResponse(**RECORD_REPEATED_PHRASES)
    result = extract_pico_spans(record)

    # In TEXT_REPEATED, metformin appears multiple times
    metformin_spans = [s for s in result.spans if s.quote.lower() == "metformin"]
    assert len(metformin_spans) >= 3, f"Expected multiple metformin spans, got {len(metformin_spans)}"

    # Ensure all offsets are distinct and exact
    offsets = set()
    for span in metformin_spans:
        assert (span.start_cp, span.end_cp) not in offsets
        offsets.add((span.start_cp, span.end_cp))
        assert record.abstract_text[span.start_cp : span.end_cp] == span.quote

    is_valid, errors = validate_pico_result(result, record.abstract_text)
    assert is_valid, f"Validation errors: {errors}"


def test_single_arm_study_comparator_is_strictly_absent():
    """Single-arm trial with no comparator must return has_comparator=False and NO C spans.

    Never invent placebo or control when unsupported by the text.
    """
    record = RecordRevisionResponse(**RECORD_SINGLE_ARM_NO_COMPARATOR)
    result = extract_pico_spans(record)

    assert result.has_intervention is True
    assert result.has_comparator is False, "Comparator must be False for single-arm trial"
    c_spans = [s for s in result.spans if s.label == PicoLabel.C]
    assert len(c_spans) == 0, f"Expected 0 comparator spans, got {c_spans}"

    is_valid, errors = validate_pico_result(result, record.abstract_text)
    assert is_valid, f"Validation errors: {errors}"


def test_missing_abstract_returns_clean_unavailable_state():
    """Records with abstract_text=None must return empty spans and False flags."""
    record = RecordRevisionResponse(**RECORD_MISSING_ABSTRACT)
    result = extract_pico_spans(record)

    assert result.record_revision_id == record.id
    assert len(result.spans) == 0
    assert result.has_population is False
    assert result.has_intervention is False
    assert result.has_comparator is False
    assert result.has_outcome is False

    is_valid, errors = validate_pico_result(result, record.abstract_text)
    assert is_valid, f"Validation errors: {errors}"


def test_extraction_is_deterministic_across_repeated_runs():
    """Repeated extraction on the exact same record must produce identical results."""
    record = RecordRevisionResponse(**RECORD_EXACT_EUROPEPMC)
    res1 = extract_pico_spans(record)
    res2 = extract_pico_spans(record)

    assert res1.model_dump() == res2.model_dump()
