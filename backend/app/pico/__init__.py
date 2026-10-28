"""PICO extraction module for Evidra systematic literature review platform."""
from app.pico.extractor import (
    DEFAULT_PROVENANCE,
    METHOD_VERSION,
    RuleBasedPicoExtractor,
    extract_pico_spans,
)
from app.pico.llm import LLMPicoExtractor
from app.pico.offsets import (
    codepoint_to_utf16_offset,
    span_codepoint_to_utf16,
    utf16_to_codepoint_offset,
    validate_span_offsets,
)
from app.pico.patterns import COMPILED_RULES, PicoRule
from app.pico.validator import compute_text_hash, validate_pico_result

__all__ = [
    "COMPILED_RULES",
    "DEFAULT_PROVENANCE",
    "METHOD_VERSION",
    "LLMPicoExtractor",
    "PicoRule",
    "RuleBasedPicoExtractor",
    "codepoint_to_utf16_offset",
    "compute_text_hash",
    "extract_pico_spans",
    "span_codepoint_to_utf16",
    "utf16_to_codepoint_offset",
    "validate_pico_result",
    "validate_span_offsets",
]
