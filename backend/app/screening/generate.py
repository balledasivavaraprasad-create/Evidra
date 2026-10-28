"""Build screening rules from a review's own question and PICO.

Everything here is deterministic. The optional AI synonym step lives in the caller, which passes
a provider in; with no provider the output depends only on the inputs.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from app.contracts.enums import PicoLabel
from app.contracts.models import CriterionDefinition
from app.screening.defaults import DEFAULT_CRITERIA_DEFINITIONS
from app.terms import POPULATION_LEAD_RE, keyword_variants, trim_stop_words

# One-letter and long PICO keys both accepted
_PICO_KEYS: tuple[tuple[str, str, str], ...] = (
    ("population", "P", "Population"),
    ("intervention", "I", "Intervention"),
    ("comparator", "C", "Comparator"),
    ("outcome", "O", "Outcome"),
)

_SPLIT_RE = re.compile(r"[,;/()]|\s+or\s+", re.IGNORECASE)

# Topic-neutral rules (study design, animals, simulation, case reports, language, abstract)
GENERIC_RULE_IDS = (
    "comparative_clinical_design",
    "exclude_animal_only",
    "exclude_simulation_only",
    "exclude_case_reports",
    "english_language",
    "abstract_available",
)

SynonymProvider = Callable[[str, list[str]], list[str]]

_PICO_LABELS = {
    "population": PicoLabel.P,
    "intervention": PicoLabel.I,
    "comparator": PicoLabel.C,
    "outcome": PicoLabel.O,
}


def pico_terms_from_criteria(
    pico: Mapping[str, str] | None,
    criteria: list[CriterionDefinition],
) -> dict[PicoLabel, list[str]]:
    """The review's own words for P, I, C and O, used to find them in each abstract.

    The keywords on the saved PICO rules win, so the reviewer's edits (and any synonyms they kept)
    are what is looked for. A PICO field with no rule falls back to splitting its text.
    """
    fields = normalise_pico(pico)
    by_id = {c.id: c for c in criteria}
    terms: dict[PicoLabel, list[str]] = {}
    for long, label in _PICO_LABELS.items():
        rule = by_id.get(f"pico_{long}")
        words = list(rule.keywords) if rule and rule.keywords else split_keywords(fields[long], population=(long == "population"))
        if words:
            terms[label] = words
    return terms


def split_keywords(field: str | None, *, population: bool = False) -> list[str]:
    """Turn one PICO field into search keywords.

    Splits on commas, " or ", ";", "/" and parentheses, trims, drops stop-words and duplicates.
    For a population, a leading "patients with" / "adults with" is removed so that the condition
    itself is matched. A phrase like "hospitalization for heart failure" also yields
    "heart failure hospitalization".
    """
    seen: set[str] = set()
    out: list[str] = []

    def add(term: str) -> None:
        term = trim_stop_words(re.sub(r"\s+", " ", term).strip(" .:-–—\"'"))
        if term and term.lower() not in seen:
            seen.add(term.lower())
            out.append(term)

    for raw in _SPLIT_RE.split(field or ""):
        term = raw.strip()
        if population:
            term = POPULATION_LEAD_RE.sub("", term)
        add(term)
        if not population:
            for variant in keyword_variants(trim_stop_words(term)):
                add(variant)
    return out


def normalise_pico(pico: Mapping[str, str] | None) -> dict[str, str]:
    """population / intervention / comparator / outcome, accepting P / I / C / O too."""
    raw = pico or {}
    return {
        long: (raw.get(long) or raw.get(short) or "").strip()
        for long, short, _label in _PICO_KEYS
    }


def _short(text: str, limit: int = 70) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def generic_rules() -> list[CriterionDefinition]:
    """The topic-neutral rules, with no mention of any condition or drug."""
    wanted = set(GENERIC_RULE_IDS)
    by_id = {c.id: c for c in DEFAULT_CRITERIA_DEFINITIONS if c.id in wanted}
    return [by_id[i].model_copy(update={"source": "generic"}) for i in GENERIC_RULE_IDS if i in by_id]


def rules_from_pico(
    title: str,
    question: str,
    pico: Mapping[str, str] | None,
    *,
    synonyms: SynonymProvider | None = None,
) -> list[CriterionDefinition]:
    """One inclusion rule per non-empty PICO field, then the topic-neutral rules.

    ``synonyms(label, keywords)`` may return extra terms for the population and intervention
    rules (an AI step run by the caller); they are added to ``keywords`` and listed in
    ``ai_suggested_keywords`` so the UI can show where they came from.
    """
    fields = normalise_pico(pico)
    rules: list[CriterionDefinition] = []
    for long, _short_key, label in _PICO_KEYS:
        text = fields[long]
        if not text:
            continue
        keywords = split_keywords(text, population=(long == "population"))
        if not keywords:
            continue
        added: list[str] = []
        if synonyms is not None and long in ("population", "intervention"):
            known = {k.lower() for k in keywords}
            for extra in synonyms(label, keywords):
                extra = extra.strip()
                if extra and extra.lower() not in known:
                    known.add(extra.lower())
                    added.append(extra)
        rules.append(
            CriterionDefinition(
                id=f"pico_{long}",
                name=f"{label}: {_short(text)}",
                category=long,
                is_inclusion=True,
                rationale=f"The title or abstract should mention the review's {label.lower()}.",
                metadata_first=False,
                keywords=keywords + added,
                source="pico",
                ai_suggested_keywords=added,
            )
        )
    return rules + generic_rules()
