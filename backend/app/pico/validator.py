"""Validation utilities for PICO extraction results and span integrity."""
import hashlib

from app.contracts.enums import PicoLabel
from app.contracts.models import PicoResult


def compute_text_hash(text: str | None) -> str:
    """Calculate the canonical SHA-256 content hash for abstract text."""
    if text is None:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_pico_result(
    result: PicoResult,
    abstract_text: str | None,
) -> tuple[bool, list[str]]:
    """Validate a PicoResult against original abstract text and domain invariants.

    Returns:
        (is_valid, error_messages): True and empty list if all invariants pass; False and errors otherwise.
    """
    errors: list[str] = []

    # 1. Missing / empty abstract handling
    if abstract_text is None or len(abstract_text) == 0:
        if len(result.spans) > 0:
            errors.append(f"Result contains {len(result.spans)} spans but abstract_text is absent/empty")
        if result.has_population or result.has_intervention or result.has_comparator or result.has_outcome:
            errors.append("Result has truthy has_* flags but abstract_text is absent/empty")
        expected_hash = compute_text_hash(abstract_text)
        if result.content_hash != expected_hash:
            errors.append(
                f"Content hash mismatch for empty abstract: got '{result.content_hash}', expected '{expected_hash}'"
            )
        return len(errors) == 0, errors

    # 2. Text hash verification
    expected_hash = compute_text_hash(abstract_text)
    if result.content_hash != expected_hash:
        errors.append(
            f"Content hash mismatch: result has '{result.content_hash}', computed '{expected_hash}'"
        )

    # 3. Span offset and quote integrity
    text_len_cp = len(abstract_text)
    seen_spans: set[tuple[str, int, int]] = set()

    for idx, span in enumerate(result.spans):
        label_val = span.label.value if hasattr(span.label, "value") else str(span.label)
        span_key = (label_val, span.start_cp, span.end_cp)

        if span_key in seen_spans:
            errors.append(f"Duplicate span at index {idx}: {label_val} [{span.start_cp}:{span.end_cp})")
        seen_spans.add(span_key)

        if span.start_cp < 0:
            errors.append(f"Span {idx} start_cp ({span.start_cp}) is negative")
        if span.end_cp <= span.start_cp:
            errors.append(
                f"Span {idx} end_cp ({span.end_cp}) must be greater than start_cp ({span.start_cp})"
            )
        if span.end_cp > text_len_cp:
            errors.append(
                f"Span {idx} end_cp ({span.end_cp}) exceeds abstract length in code points ({text_len_cp})"
            )

        # Quote verification against exact slice
        if 0 <= span.start_cp < span.end_cp <= text_len_cp:
            actual_quote = abstract_text[span.start_cp:span.end_cp]
            if actual_quote != span.quote:
                errors.append(
                    f"Span {idx} quote mismatch: abstract_text[{span.start_cp}:{span.end_cp}] is "
                    f"'{actual_quote}', expected '{span.quote}'"
                )

        if not span.provenance:
            errors.append(f"Span {idx} has missing or empty provenance")

    # 4. Consistency between span labels and summary boolean flags
    has_p = any(s.label == PicoLabel.P for s in result.spans)
    has_i = any(s.label == PicoLabel.I for s in result.spans)
    has_c = any(s.label == PicoLabel.C for s in result.spans)
    has_o = any(s.label == PicoLabel.O for s in result.spans)

    if result.has_population != has_p:
        errors.append(f"has_population flag ({result.has_population}) does not match presence of P spans ({has_p})")
    if result.has_intervention != has_i:
        errors.append(f"has_intervention flag ({result.has_intervention}) does not match presence of I spans ({has_i})")
    if result.has_comparator != has_c:
        errors.append(f"has_comparator flag ({result.has_comparator}) does not match presence of C spans ({has_c})")
    if result.has_outcome != has_o:
        errors.append(f"has_outcome flag ({result.has_outcome}) does not match presence of O spans ({has_o})")

    return len(errors) == 0, errors
