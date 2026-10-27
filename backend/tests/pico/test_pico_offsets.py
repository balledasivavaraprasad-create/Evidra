"""Tests for Unicode code points and UTF-16 code units offset conversion and verification."""
from app.contracts.enums import PicoLabel
from app.contracts.models import PicoSpan
from app.pico.offsets import (
    codepoint_to_utf16_offset,
    span_codepoint_to_utf16,
    utf16_to_codepoint_offset,
    validate_span_offsets,
)


def test_ascii_offsets_are_identity():
    """For pure ASCII strings, code points and UTF-16 code units are 1:1 identical."""
    text = "Clinical trial of metformin in adult diabetics."
    for idx in range(len(text) + 1):
        u16 = codepoint_to_utf16_offset(text, idx)
        assert u16 == idx
        cp = utf16_to_codepoint_offset(text, u16)
        assert cp == idx


def test_bmp_multibyte_utf8_offsets_are_identity_in_utf16():
    """Greek letters (e.g. α, β) and accents are BMP (<= 0xFFFF), so 1 code point = 1 UTF-16 unit."""
    text = "Metformin action on β-cell preservation and α-glucosidase."
    for idx in range(len(text) + 1):
        u16 = codepoint_to_utf16_offset(text, idx)
        assert u16 == idx
        cp = utf16_to_codepoint_offset(text, u16)
        assert cp == idx


def test_non_bmp_emoji_surrogate_pairs():
    """Emoji (code points > 0xFFFF) take 1 code point in Python but 2 code units in UTF-16 / JavaScript DOM."""
    # Syringe emoji: \U0001F489 (1 code point, 2 UTF-16 units: \uD83D\uDC89)
    text = "Dose: 500mg 💉 twice daily."

    # Index of syringe emoji in Python code points
    emoji_idx = text.index("💉")
    assert emoji_idx == 12
    assert len(text) == 26

    # Offset before emoji is identical
    assert codepoint_to_utf16_offset(text, 12) == 12
    # Offset after emoji is shifted by +1 in UTF-16
    assert codepoint_to_utf16_offset(text, 13) == 14
    assert codepoint_to_utf16_offset(text, len(text)) == 27  # 26 code points = 27 UTF-16 units

    # Round-trip conversion for every position
    for cp_idx in range(len(text) + 1):
        u16 = codepoint_to_utf16_offset(text, cp_idx)
        recovered_cp = utf16_to_codepoint_offset(text, u16)
        assert recovered_cp == cp_idx, f"Failed round-trip at cp {cp_idx}: got {recovered_cp}"


def test_span_codepoint_to_utf16_conversion():
    """span_codepoint_to_utf16 correctly augments span with UTF-16 bounds."""
    text = "Evaluation 💉: reduction in HbA1c observed."
    # Text after syringe emoji
    quote = "reduction in HbA1c"
    start_cp = text.index(quote)
    end_cp = start_cp + len(quote)

    span = PicoSpan(
        label=PicoLabel.O,
        start_cp=start_cp,
        end_cp=end_cp,
        quote=quote,
        provenance="rule:test",
    )

    enriched = span_codepoint_to_utf16(text, span)
    assert enriched["label"] == "O"
    assert enriched["start_cp"] == start_cp
    assert enriched["end_cp"] == end_cp
    # UTF-16 offset must be shifted by 1 because of the syringe emoji earlier in the string
    assert enriched["start_utf16"] == start_cp + 1
    assert enriched["end_utf16"] == end_cp + 1
    assert enriched["quote"] == quote


def test_validate_span_offsets_valid_and_invalid():
    """validate_span_offsets enforces strict bounds and exact quote slices."""
    text = "Metformin improves glycemic control."

    # Valid span
    is_valid, msg = validate_span_offsets(text, 0, 9, "Metformin")
    assert is_valid
    assert msg == ""

    # Negative start
    is_valid, msg = validate_span_offsets(text, -1, 9, "Metformin")
    assert not is_valid
    assert "start_cp (-1) must be >= 0" in msg

    # Start >= end
    is_valid, msg = validate_span_offsets(text, 9, 9, "")
    assert not is_valid
    assert "strictly greater" in msg

    # End exceeds length
    is_valid, msg = validate_span_offsets(text, 0, 100, "Metformin")
    assert not is_valid
    assert "exceeds text length" in msg

    # Quote mismatch
    is_valid, msg = validate_span_offsets(text, 0, 9, "Placebo")
    assert not is_valid
    assert "Quote mismatch" in msg
