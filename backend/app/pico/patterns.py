"""Deterministic regular expression patterns and keywords for baseline PICO extraction."""
import re
from typing import NamedTuple

from app.contracts.enums import PicoLabel


class PicoRule(NamedTuple):
    """Named rule specification for pattern-based PICO span matching."""

    label: PicoLabel
    regex: re.Pattern[str]
    capture_group: int = 0
    priority: int = 10


# ---------------------------------------------------------------------------
# Population (P) Patterns
# ---------------------------------------------------------------------------
POPULATION_PATTERNS = [
    # Demographics + Condition combinations
    r"\b(?:adults?|patients?|subjects?|participants?|individuals?|elderly|children|neonates?|infants?|women|men)\s+with\s+(?:type\s*2\s*diabetes|type\s*1\s*diabetes|diabetes(?:\s+mellitus)?|hypertension|acute\s+(?:renal\s+failure|kidney\s+injury)|heart\s+failure|lactic\s+acidosis)\b",
    r"\b(?:adult|elderly|pediatric|neonatal|pregnant)\s+(?:diabetic\s+patients?|diabetics?|patients?|subjects?|participants?)\b",
    r"\btype\s*2\s*diabetes(?:\s*\([A-Z0-9]+\))?\b",
    r"\btype\s*1\s*diabetes\b",
    r"\b(?:male\s+)?Sprague-Dawley\s+rats\b",
    r"\bstreptozotocin-induced\s+diabetic\s+rats\b",
    r"\b(?:8[0-9]|9[0-9]|[1-7][0-9])-year-old\s+(?:female|male|woman|man|patient)\b",
]

# ---------------------------------------------------------------------------
# Intervention (I) Patterns
# ---------------------------------------------------------------------------
INTERVENTION_PATTERNS = [
    # Metformin and formulation variants
    r"\bmetformin\s+extended-release\b",
    r"\bmetformin\s+monotherapy\b",
    r"\boral\s+metformin\b",
    r"\bmetformin\s+\d+\s*(?:mg/kg|mg|g)\s*(?:daily|twice daily)?\b",
    r"\bmetformin\b",
    r"\bbiguanides\b",
    r"\binsulin\s+sensitizers?\b",
    r"\blifestyle\s+intervention\b",
    r"\bhemodialysis\b",
]

# ---------------------------------------------------------------------------
# Comparator (C) Patterns
# ---------------------------------------------------------------------------
# C must be strictly grounded; absent cues mean NO comparator span
COMPARATOR_PATTERNS = [
    r"\bplacebo\b",
    r"\bcontrol\s+group\b",
    r"\blifestyle\s+intervention\s+alone\b",
    r"\bsulfonylurea\b",
    r"\bactive\s+comparator\b",
    r"\bstandard\s+of\s+care\b",
    r"\busual\s+care\b",
    r"\buntreated\s+controls?\b",
]

# ---------------------------------------------------------------------------
# Outcome (O) Patterns
# ---------------------------------------------------------------------------
OUTCOME_PATTERNS = [
    r"\breduction\s+in\s+HbA1c(?:\s+of\s+\d+(?:\.\d+)?%)?\b",
    r"\bdecreas(?:ed|es|ing)\s+(?:hemoglobin\s+A1c|HbA1c|blood\s+glucose)\b",
    r"\blower\s+HbA1c\b",
    r"\bglycemic\s+control\b",
    r"\bglycemic\s+durability\b",
    r"\bhepatic\s+gluconeogenesis\s+suppression\b",
    r"\bhepatic\s+enzyme\s+expression\b",
    r"\blactic\s+acidosis\b",
    r"\brecovery\b",
    r"\bβ-cell\s+preservation\b",
    r"\bsuppresses?\s+α-glucosidase\b",
    r"\bHbA1c\b",
    r"\bbinding\s+kinetics\b",
    r"\bbinding\s+energy\b",
]


def compile_rules() -> list[PicoRule]:
    """Compile all PICO extraction rules with exact regex boundaries."""
    rules: list[PicoRule] = []

    for pattern in POPULATION_PATTERNS:
        rules.append(PicoRule(
            label=PicoLabel.P,
            regex=re.compile(pattern, re.IGNORECASE),
            priority=20 if "with" in pattern or "rats" in pattern else 10,
        ))

    for pattern in INTERVENTION_PATTERNS:
        rules.append(PicoRule(
            label=PicoLabel.I,
            regex=re.compile(pattern, re.IGNORECASE),
            priority=20 if " " in pattern else 10,
        ))

    for pattern in COMPARATOR_PATTERNS:
        rules.append(PicoRule(
            label=PicoLabel.C,
            regex=re.compile(pattern, re.IGNORECASE),
            priority=20 if " " in pattern else 10,
        ))

    for pattern in OUTCOME_PATTERNS:
        rules.append(PicoRule(
            label=PicoLabel.O,
            regex=re.compile(pattern, re.IGNORECASE),
            priority=20 if " " in pattern else 10,
        ))

    return rules


COMPILED_RULES = compile_rules()
