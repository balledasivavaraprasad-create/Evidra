"""Input sanitization and indirect prompt injection defense (C03).

Treats literature abstracts, citations, and model fixtures as passive data,
preventing execution of embedded instructions or secret exfiltration.
"""
from __future__ import annotations

import re

# High-confidence indirect prompt injection patterns in literature and external text
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior)\s+(?:rules|guidelines|context)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:an?\s+unrestricted|in\s+developer\s+mode|dan\b)", re.IGNORECASE),
    re.compile(r"<\|(?:im_start|im_end|endoftext)\|>", re.IGNORECASE),
    re.compile(r"\[(?:INST|\/INST|SYS|\/SYS)\]", re.IGNORECASE),
    re.compile(r"output\s+(?:the\s+)?(?:system\s+prompt|api\s+key|environment\s+variables?)", re.IGNORECASE),
    re.compile(r"print\s+(?:the\s+)?(?:secret|canary|password|bearer\s+token)", re.IGNORECASE),
]

_SECRET_CANARY_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"canary_token_[a-f0-9]{16,}", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> tuple[bool, str | None]:
    """Scan untrusted input text for indirect prompt injection signatures.

    Returns (is_injection, matched_pattern_description).
    """
    if not text:
        return False, None

    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"Matched injection pattern: {match.group(0)}"

    return False, None


def sanitize_untrusted_text(text: str) -> str:
    """Sanitize untrusted text before inclusion in any model context.

    Neutralizes prompt boundary tokens and escapes dangerous delimiters.
    """
    if not text:
        return ""

    sanitized = text
    # Strip prompt boundary tags
    sanitized = re.sub(r"<\|[^>]+?\|>", "[STRIPPED_TOKEN]", sanitized)
    sanitized = re.sub(r"\[/?(?:INST|SYS)\]", "[STRIPPED_TAG]", sanitized, flags=re.IGNORECASE)
    return sanitized.strip()


def check_for_secret_leakage(text: str) -> bool:
    """Detect whether output or log message contains potential API keys or canaries."""
    if not text:
        return False

    return any(p.search(text) is not None for p in _SECRET_CANARY_PATTERNS)
