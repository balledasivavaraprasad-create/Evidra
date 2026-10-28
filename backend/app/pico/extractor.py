"""Deterministic rule-based PICO span extractor implementing PicoPort."""
import re

from app.contracts.enums import PicoLabel
from app.contracts.models import PicoResult, PicoSpan, RecordRevisionResponse
import hashlib
from collections.abc import Mapping, Sequence

from app.pico.patterns import COMPILED_RULES, PicoRule, build_review_rules
from app.pico.validator import compute_text_hash

METHOD_VERSION = "pico_extractor:v1.0"
DEFAULT_PROVENANCE = "rule:pico:v1.0"

# Strict clinical negation detector to prevent extracting negated comparator mentions
# (e.g. "No comparator or control group was included")
COMPARATOR_NEGATION_REGEX = re.compile(
    r"\b(?:no|without|neither|lacked|lacking|absence of|devoid of)\s+(?:[a-zA-Z0-9\-]+\s+){0,4}(?:or\s+)?\s*$",
    re.IGNORECASE,
)


class RuleBasedPicoExtractor:
    """Deterministic, pure-function PICO extractor implementing PicoPort.

    Zero LLM required, zero external dependencies, zero database writes.
    Outputs exact Unicode code-point offsets [start_cp, end_cp) matching
    exact slices of the canonical abstract text.
    """

    def __init__(
        self,
        rules: list[PicoRule] | None = None,
        method_version: str = METHOD_VERSION,
        provenance: str = DEFAULT_PROVENANCE,
        review_terms: Mapping[PicoLabel, Sequence[str]] | None = None,
    ) -> None:
        """``review_terms`` adds patterns for the review's own P/I/C/O keywords to the generic ones.

        The terms are part of the method version, so a change to them is a different method: cached
        results made with other keywords are never reused for this one.
        """
        base = rules if rules is not None else COMPILED_RULES
        extra = build_review_rules(review_terms) if review_terms else []
        self.rules = [*extra, *base]
        self.method_version = method_version
        if extra:
            digest = hashlib.sha256(
                "|".join(
                    f"{label.value}:{','.join(sorted(k.lower() for k in kws))}"
                    for label, kws in sorted(review_terms.items(), key=lambda kv: kv[0].value)
                ).encode("utf-8")
            ).hexdigest()[:10]
            self.method_version = f"{method_version}+review:{digest}"
        self.provenance = provenance

    def extract_from_text(
        self,
        abstract_text: str | None,
        record_revision_id: str = "temp-record-id",
    ) -> PicoResult:
        """Extract exact PICO spans from raw abstract text."""
        # 1. Handle missing, None, or empty abstract text explicitly
        if abstract_text is None or len(abstract_text.strip()) == 0:
            return PicoResult(
                record_revision_id=record_revision_id,
                content_hash=compute_text_hash(abstract_text),
                spans=[],
                has_population=False,
                has_intervention=False,
                has_comparator=False,
                has_outcome=False,
                method_version=self.method_version,
            )

        content_hash = compute_text_hash(abstract_text)
        candidate_spans: list[tuple[int, int, PicoLabel, str, int]] = []

        # 2. Match rules against canonical abstract text
        for rule in self.rules:
            for match in rule.regex.finditer(abstract_text):
                start_cp = match.start(rule.capture_group)
                end_cp = match.end(rule.capture_group)
                quote = abstract_text[start_cp:end_cp]

                if not quote or not quote.strip():
                    continue

                # Clinical invariant: if this is a comparator cue but preceded by negation,
                # do not extract it as an active comparator (e.g. "No comparator or control group")
                if rule.label == PicoLabel.C:
                    preceding_window = abstract_text[max(0, start_cp - 60) : start_cp]
                    if COMPARATOR_NEGATION_REGEX.search(preceding_window):
                        continue

                candidate_spans.append((start_cp, end_cp, rule.label, quote, rule.priority))

        # 3. Disambiguate within same label (prefer higher priority and longer specific spans),
        # while preserving justified cross-label overlaps and distinct repeated occurrences.
        filtered_spans: list[PicoSpan] = []

        # Group by label to deduplicate within label
        by_label: dict[PicoLabel, list[tuple[int, int, PicoLabel, str, int]]] = {}
        for item in candidate_spans:
            by_label.setdefault(item[2], []).append(item)

        for items in by_label.values():
            # Sort by start_cp ascending, then length descending, then priority descending
            items.sort(key=lambda x: (x[0], -(x[1] - x[0]), -x[4]))
            kept: list[tuple[int, int, PicoLabel, str, int]] = []

            for cand in items:
                cand_start, cand_end, _, _, cand_prio = cand
                # Check if this candidate is subsumed by an already kept span of the same label
                subsumed = False
                for k in kept:
                    k_start, k_end, _, _, k_prio = k
                    # Identical span
                    if cand_start == k_start and cand_end == k_end:
                        subsumed = True
                        break
                    # Strictly subsumed within a longer higher/equal priority span of same label
                    if k_start <= cand_start and cand_end <= k_end and k_prio >= cand_prio:
                        subsumed = True
                        break

                if not subsumed:
                    kept.append(cand)

            for s_start, s_end, s_label, s_quote, _ in kept:
                filtered_spans.append(
                    PicoSpan(
                        label=s_label,
                        start_cp=s_start,
                        end_cp=s_end,
                        quote=s_quote,
                        provenance=self.provenance,
                    )
                )

        # 4. Sort all spans deterministically by start offset, end offset, then label
        filtered_spans.sort(key=lambda s: (s.start_cp, s.end_cp, s.label.value))

        return PicoResult(
            record_revision_id=record_revision_id,
            content_hash=content_hash,
            spans=filtered_spans,
            has_population=any(s.label == PicoLabel.P for s in filtered_spans),
            has_intervention=any(s.label == PicoLabel.I for s in filtered_spans),
            has_comparator=any(s.label == PicoLabel.C for s in filtered_spans),
            has_outcome=any(s.label == PicoLabel.O for s in filtered_spans),
            method_version=self.method_version,
        )

    def extract_pico_spans(self, record: RecordRevisionResponse) -> PicoResult:
        """PicoPort implementation: extract PICO spans for a normalized literature record."""
        return self.extract_from_text(
            abstract_text=record.abstract_text,
            record_revision_id=record.id,
        )


# Global default instance and functional entry point
_default_extractor = RuleBasedPicoExtractor()


def extract_pico_spans(record: RecordRevisionResponse) -> PicoResult:
    """Functional convenience wrapper implementing PicoPort."""
    return _default_extractor.extract_pico_spans(record)
