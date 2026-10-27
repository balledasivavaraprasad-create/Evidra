"""Unicode code-point and UTF-16 offset mapping and validation utilities."""
from typing import Any

from app.contracts.models import PicoSpan


def codepoint_to_utf16_offset(text: str, cp_offset: int) -> int:
    """Convert a zero-based Unicode code-point index to a zero-based UTF-16 code-unit offset.

    Characters with code points > 0xFFFF (such as emoji or SMP symbols) are encoded
    as surrogate pairs (2 UTF-16 code units) in JavaScript/browser DOM environments.
    """
    if cp_offset <= 0:
        return 0
    clamped_offset = min(cp_offset, len(text))
    # Sum 2 for surrogate pairs, 1 for BMP characters
    return sum(2 if ord(c) > 0xFFFF else 1 for c in text[:clamped_offset])


def utf16_to_codepoint_offset(text: str, utf16_offset: int) -> int:
    """Convert a zero-based UTF-16 code-unit offset to a zero-based Unicode code-point index.

    Guarantees exact round-trip conversion when receiving browser text-selection offsets.
    """
    if utf16_offset <= 0:
        return 0
    current_utf16 = 0
    for cp_idx, c in enumerate(text):
        if current_utf16 >= utf16_offset:
            return cp_idx
        current_utf16 += 2 if ord(c) > 0xFFFF else 1
    return len(text)


def span_codepoint_to_utf16(text: str, span: PicoSpan) -> dict[str, Any]:
    """Convert a PicoSpan's code-point offsets to include browser UTF-16 offsets."""
    start_u16 = codepoint_to_utf16_offset(text, span.start_cp)
    end_u16 = codepoint_to_utf16_offset(text, span.end_cp)
    return {
        "label": span.label.value if hasattr(span.label, "value") else str(span.label),
        "start_cp": span.start_cp,
        "end_cp": span.end_cp,
        "start_utf16": start_u16,
        "end_utf16": end_u16,
        "quote": span.quote,
        "provenance": span.provenance,
    }


def validate_span_offsets(
    text: str,
    start_cp: int,
    end_cp: int,
    expected_quote: str,
) -> tuple[bool, str]:
    """Validate that start_cp and end_cp are valid half-open code-point bounds matching expected_quote."""
    if start_cp < 0:
        return False, f"start_cp ({start_cp}) must be >= 0"
    if end_cp <= start_cp:
        return False, f"end_cp ({end_cp}) must be strictly greater than start_cp ({start_cp})"
    if end_cp > len(text):
        return False, f"end_cp ({end_cp}) exceeds text length in code points ({len(text)})"
    actual_quote = text[start_cp:end_cp]
    if actual_quote != expected_quote:
        return (
            False,
            f"Quote mismatch: text[{start_cp}:{end_cp}] is '{actual_quote}', expected '{expected_quote}'",
        )
    return True, ""
