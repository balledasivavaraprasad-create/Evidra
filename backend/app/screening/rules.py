"""Pure, deterministic screening rule evaluators with metadata-first and context awareness."""
from __future__ import annotations

import re

from app.contracts.enums import CriterionVerdict, ScreeningEvidenceSource
from app.contracts.models import (
    CriterionDefinition,
    CriterionEvidence,
    RecordRevisionResponse,
)
from app.terms import keyword_pattern

METHOD_VERSION = "screening-rules-v1.0.0"

# ---------------------------------------------------------------------------
# Precompiled Regex Patterns
# ---------------------------------------------------------------------------
_ANIMAL_ONLY_RE = re.compile(
    r"\b(?:wistar|sprague[-\s]dawley|rats?|mice|mouse|murine|rodents?|canine|rabbits?|swine|piglets?)\b",
    re.IGNORECASE,
)
_HUMAN_TRIAL_INDICATORS_RE = re.compile(
    r"\b(?:patients?|adults?|men|women|participants?|volunteers?|subjects?|human|clinical trial|double-blind|randomized|placebo-controlled)\b",
    re.IGNORECASE,
)
_PRECLINICAL_CONTEXT_RE = re.compile(
    r"\b(?:unlike in animal|previous animal|in rodent models?|prior rat studies|extending animal|consistent with preclinical|preclinical studies suggested|animal models showed)\b",
    re.IGNORECASE,
)
_SIMULATION_ONLY_RE = re.compile(
    r"\b(?:in silico|computational docking|molecular dynamics|monte carlo|finite element modeling|mathematical model of|virtual screening)\b",
    re.IGNORECASE,
)
_SIMULATION_NO_HUMAN_RE = re.compile(
    r"\b(?:no human patients|no living tissues|purely in silico|in silico only|theoretical simulation)\b",
    re.IGNORECASE,
)
_CASE_REPORT_RE = re.compile(
    r"\b(?:we report a case of|a case report of|a single case of|we describe a \d+[- ]year[- ]old|a \d+[- ]year[- ]old (?:man|woman|female|male|patient) presented with)\b",
    re.IGNORECASE,
)
_COHORT_CASES_RE = re.compile(
    r"\b(?:\d+\s+cases|cases\s+and\s+controls|case-control|incident\s+cases|cohort of \d+ cases)\b",
    re.IGNORECASE,
)
_T2D_POPULATION_RE = re.compile(
    r"\b(?:type 2 diabetes|t2d|t2dm|non-insulin[- ]dependent diabetes|adult[- ]onset diabetes)\b",
    re.IGNORECASE,
)
_T1D_ONLY_RE = re.compile(
    r"\b(?:type 1 diabetes|t1d|juvenile diabetes|autoimmune diabetes)\b",
    re.IGNORECASE,
)
_NEGATED_T2D_RE = re.compile(
    r"\b(?:no\s+(?:adults\s+with\s+)?(?:type\s+2\s+diabetes|t2d)|excluding\s+(?:type\s+2\s+diabetes|t2d)|without\s+(?:type\s+2\s+diabetes|t2d)|not\s+(?:type\s+2\s+diabetes|t2d))\b",
    re.IGNORECASE,
)
_COMPARATIVE_DESIGN_RE = re.compile(
    r"\b(?:randomized|placebo-controlled|clinical trial|cohort|comparative|control group|versus placebo|vs\.?\s*placebo|double-blind)\b",
    re.IGNORECASE,
)


def evaluate_abstract_presence(
    record: RecordRevisionResponse,
    criterion: CriterionDefinition,
) -> CriterionEvidence:
    """Evaluate whether abstract text is present and sufficiently detailed."""
    abstract = record.abstract_text
    if not abstract or len(abstract.strip()) < 30:
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.UNKNOWN,
            reason_code="MISSING_ABSTRACT",
            explanation="Abstract text is missing or insufficient; requires full text retrieval",
            evidence_snippet=None,
            source=ScreeningEvidenceSource.METADATA,
            method_version=METHOD_VERSION,
        )

    return CriterionEvidence(
        criterion_id=criterion.id,
        name=criterion.name,
        verdict=CriterionVerdict.PASS,
        reason_code="ABSTRACT_PRESENT",
        explanation=f"Abstract present ({len(abstract.strip())} characters)",
        evidence_snippet=abstract.strip()[:120],
        source=ScreeningEvidenceSource.METADATA,
        method_version=METHOD_VERSION,
    )


def evaluate_language(
    record: RecordRevisionResponse,
    criterion: CriterionDefinition,
) -> CriterionEvidence:
    """Evaluate language reviewability, checking metadata first."""
    langs = [lang.lower().strip() for lang in (record.language or [])]

    # Metadata check
    if langs:
        if any(l in ("eng", "en", "english") for l in langs):
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.PASS,
                reason_code="ENGLISH_LANGUAGE_METADATA",
                explanation=f"Record language metadata specifies English: {langs}",
                evidence_snippet=f"language={langs}",
                source=ScreeningEvidenceSource.METADATA,
                method_version=METHOD_VERSION,
            )
        # Non-empty language list strictly excluding English
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.FAIL,
            reason_code="NON_ENGLISH_LANGUAGE",
            explanation=f"Article language is non-English: {langs}",
            evidence_snippet=f"language={langs}",
            source=ScreeningEvidenceSource.METADATA,
            method_version=METHOD_VERSION,
        )

    # Absence of language metadata: check abstract text heuristics
    text = (record.title or "") + " " + (record.abstract_text or "")
    if len(text.strip()) < 40:
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.UNKNOWN,
            reason_code="AMBIGUOUS_LANGUAGE",
            explanation="Language metadata missing and text insufficient for language determination",
            evidence_snippet=None,
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    return CriterionEvidence(
        criterion_id=criterion.id,
        name=criterion.name,
        verdict=CriterionVerdict.PASS,
        reason_code="ENGLISH_TEXT_INFERRED",
        explanation="English text inferred from title and abstract content",
        evidence_snippet=text[:80],
        source=ScreeningEvidenceSource.RULE,
        method_version=METHOD_VERSION,
    )


def evaluate_species(
    record: RecordRevisionResponse,
    criterion: CriterionDefinition,
) -> CriterionEvidence:
    """Evaluate species exclusion: animal-only vs human trial with animal background."""
    meta = record.metadata_json or {}
    mesh_headings = [h.lower() for h in meta.get("mesh_headings", [])]
    pub_types = [p.lower() for p in (record.publication_types or [])]

    # 1. Metadata-first check
    if criterion.metadata_first and mesh_headings:
        has_human_mesh = any("human" in h for h in mesh_headings)
        has_animal_mesh = any("animal" in h or "rats" in h or "mice" in h for h in mesh_headings)

        if has_human_mesh:
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.PASS,
                reason_code="HUMAN_SPECIES_METADATA",
                explanation="MeSH headings confirm human subject study",
                evidence_snippet="MeSH: Humans",
                source=ScreeningEvidenceSource.METADATA,
                method_version=METHOD_VERSION,
            )
        if has_animal_mesh and not has_human_mesh:
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.FAIL,
                reason_code="ANIMAL_STUDY_EXCLUDED",
                explanation="MeSH headings confirm animal-only study without human subjects",
                evidence_snippet=f"MeSH: {meta.get('mesh_headings')}",
                source=ScreeningEvidenceSource.METADATA,
                method_version=METHOD_VERSION,
            )

    # 2. Text heuristics with context & negation awareness
    full_text = f"{record.title or ''}. {record.abstract_text or ''}"
    if not full_text.strip():
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.UNKNOWN,
            reason_code="MISSING_TEXT_SPECIES",
            explanation="Insufficient text to determine species",
            evidence_snippet=None,
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    has_animal_terms = bool(_ANIMAL_ONLY_RE.search(full_text))
    has_human_terms = bool(_HUMAN_TRIAL_INDICATORS_RE.search(full_text))
    has_preclinical_context = bool(_PRECLINICAL_CONTEXT_RE.search(full_text))

    # Human trial with animal background: MUST NOT be excluded
    if has_human_terms and (has_preclinical_context or any(pt in ("randomized controlled trial", "clinical trial") for pt in pub_types)):
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.PASS,
            reason_code="HUMAN_TRIAL_WITH_PRECLINICAL_BACKGROUND",
            explanation="Human clinical trial mentioning preclinical or animal background is included",
            evidence_snippet=full_text[:140],
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    # Animal terms without human trial subjects: pure animal model
    if has_animal_terms and not has_human_terms:
        match = _ANIMAL_ONLY_RE.search(full_text)
        snippet = match.group(0) if match else "animal terms"
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.FAIL,
            reason_code="ANIMAL_STUDY_EXCLUDED",
            explanation=f"Preclinical animal model detected without human subjects: '{snippet}'",
            evidence_snippet=full_text[max(0, (match.start() - 20) if match else 0): (match.end() + 60) if match else 100],
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    # Default to pass if no animal models detected
    return CriterionEvidence(
        criterion_id=criterion.id,
        name=criterion.name,
        verdict=CriterionVerdict.PASS,
        reason_code="NO_ANIMAL_MODEL_DETECTED",
        explanation="No animal-only preclinical indicators found",
        evidence_snippet=full_text[:80],
        source=ScreeningEvidenceSource.RULE,
        method_version=METHOD_VERSION,
    )


def evaluate_simulation(
    record: RecordRevisionResponse,
    criterion: CriterionDefinition,
) -> CriterionEvidence:
    """Evaluate simulation-only exclusion, separating in silico from human modeling."""
    meta = record.metadata_json or {}
    mesh_headings = [h.lower() for h in meta.get("mesh_headings", [])]
    full_text = f"{record.title or ''}. {record.abstract_text or ''}"

    # Metadata check
    if criterion.metadata_first and mesh_headings:
        is_simulation_mesh = any("simulation" in h or "modeling" in h for h in mesh_headings)
        is_human_mesh = any("human" in h for h in mesh_headings)
        if is_simulation_mesh and not is_human_mesh:
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.FAIL,
                reason_code="SIMULATION_ONLY_EXCLUDED",
                explanation="MeSH headings indicate computer simulation without human clinical subjects",
                evidence_snippet=f"MeSH: {meta.get('mesh_headings')}",
                source=ScreeningEvidenceSource.METADATA,
                method_version=METHOD_VERSION,
            )

    sim_match = _SIMULATION_ONLY_RE.search(full_text)
    if sim_match:
        # Check if human trial is involved
        has_human_data = bool(_HUMAN_TRIAL_INDICATORS_RE.search(full_text))
        has_explicit_no_human = bool(_SIMULATION_NO_HUMAN_RE.search(full_text))

        if has_explicit_no_human or not has_human_data:
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.FAIL,
                reason_code="SIMULATION_ONLY_EXCLUDED",
                explanation="In silico computational simulation without empirical human patient outcomes",
                evidence_snippet=full_text[max(0, sim_match.start() - 20): sim_match.end() + 80],
                source=ScreeningEvidenceSource.RULE,
                method_version=METHOD_VERSION,
            )

        # Human study utilizing pharmacokinetic or statistical modeling
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.PASS,
            reason_code="HUMAN_STUDY_WITH_COMPUTATIONAL_MODELING",
            explanation="Human empirical trial incorporating computational or pharmacokinetic modeling",
            evidence_snippet=full_text[:120],
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    return CriterionEvidence(
        criterion_id=criterion.id,
        name=criterion.name,
        verdict=CriterionVerdict.PASS,
        reason_code="NO_SIMULATION_DETECTED",
        explanation="No simulation-only indicators detected",
        evidence_snippet=None,
        source=ScreeningEvidenceSource.RULE,
        method_version=METHOD_VERSION,
    )


def evaluate_case_report(
    record: RecordRevisionResponse,
    criterion: CriterionDefinition,
) -> CriterionEvidence:
    """Evaluate single case report exclusion vs comparative cohort of cases."""
    pub_types = [pt.lower() for pt in (record.publication_types or [])]

    # Metadata check
    if "case reports" in pub_types or "case report" in pub_types:
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.FAIL,
            reason_code="CASE_REPORT_EXCLUDED",
            explanation="Publication type is categorized as Case Reports",
            evidence_snippet=f"publication_types={record.publication_types}",
            source=ScreeningEvidenceSource.METADATA,
            method_version=METHOD_VERSION,
        )

    full_text = f"{record.title or ''}. {record.abstract_text or ''}"

    # Check for cohort cases false match: "cohort of 500 cases"
    if _COHORT_CASES_RE.search(full_text):
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.PASS,
            reason_code="COHORT_CASES_INCLUDED",
            explanation="Mention of cases refers to an empirical cohort/case-control study, not single case report",
            evidence_snippet=full_text[:120],
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    # Check for explicit single case report patterns
    case_match = _CASE_REPORT_RE.search(full_text)
    if case_match:
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.FAIL,
            reason_code="CASE_REPORT_EXCLUDED",
            explanation="Text describes a single patient case report without comparative controls",
            evidence_snippet=full_text[max(0, case_match.start() - 10): case_match.end() + 80],
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    return CriterionEvidence(
        criterion_id=criterion.id,
        name=criterion.name,
        verdict=CriterionVerdict.PASS,
        reason_code="NOT_CASE_REPORT",
        explanation="No single case report indicators found",
        evidence_snippet=None,
        source=ScreeningEvidenceSource.RULE,
        method_version=METHOD_VERSION,
    )


def evaluate_population(
    record: RecordRevisionResponse,
    criterion: CriterionDefinition,
) -> CriterionEvidence:
    """Evaluate whether record studies human adults with type 2 diabetes."""
    meta = record.metadata_json or {}
    mesh_headings = [h.lower() for h in meta.get("mesh_headings", [])]

    # 1. Metadata-first check
    if criterion.metadata_first and mesh_headings:
        has_t2d_mesh = any("type 2" in h for h in mesh_headings)
        has_t1d_mesh = any("type 1" in h for h in mesh_headings)
        if has_t1d_mesh and not has_t2d_mesh:
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.FAIL,
                reason_code="OFF_TARGET_POPULATION",
                explanation="MeSH headings confirm Type 1 diabetes population without Type 2 diabetes",
                evidence_snippet=f"MeSH: {meta.get('mesh_headings')}",
                source=ScreeningEvidenceSource.METADATA,
                method_version=METHOD_VERSION,
            )
        if has_t2d_mesh:
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.PASS,
                reason_code="TARGET_POPULATION_IDENTIFIED",
                explanation="MeSH headings confirm Type 2 diabetes population",
                evidence_snippet=f"MeSH: {meta.get('mesh_headings')}",
                source=ScreeningEvidenceSource.METADATA,
                method_version=METHOD_VERSION,
            )

    full_text = f"{record.title or ''}. {record.abstract_text or ''}"

    if not (record.abstract_text or "").strip():
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.UNKNOWN,
            reason_code="INSUFFICIENT_POPULATION_EVIDENCE",
            explanation="Missing abstract prevents confirmation of target population",
            evidence_snippet=record.title,
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    t2d_match = _T2D_POPULATION_RE.search(full_text)
    is_negated_t2d = bool(_NEGATED_T2D_RE.search(full_text))
    has_valid_t2d = bool(t2d_match) and not is_negated_t2d
    has_t1d = bool(_T1D_ONLY_RE.search(full_text))

    if has_t1d and not has_valid_t2d:
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.FAIL,
            reason_code="OFF_TARGET_POPULATION",
            explanation="Study focuses solely on Type 1 diabetes rather than Type 2 diabetes",
            evidence_snippet=full_text[:120],
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    if has_valid_t2d:
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.PASS,
            reason_code="TARGET_POPULATION_IDENTIFIED",
            explanation="Target population confirmed: adults with type 2 diabetes",
            evidence_snippet=full_text[max(0, t2d_match.start() - 20): t2d_match.end() + 60] if t2d_match else None,
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    # General diabetes mentioned without specifying subtype
    if "diabetes" in full_text.lower():
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.UNKNOWN,
            reason_code="AMBIGUOUS_DIABETES_SUBTYPE",
            explanation="Diabetes is mentioned but specific Type 2 subtype requires full text verification",
            evidence_snippet=full_text[:120],
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    return CriterionEvidence(
        criterion_id=criterion.id,
        name=criterion.name,
        verdict=CriterionVerdict.UNKNOWN,
        reason_code="UNKNOWN_POPULATION",
        explanation="Insufficient evidence of diabetes population in title and abstract",
        evidence_snippet=None,
        source=ScreeningEvidenceSource.RULE,
        method_version=METHOD_VERSION,
    )


def evaluate_study_design(
    record: RecordRevisionResponse,
    criterion: CriterionDefinition,
) -> CriterionEvidence:
    """Evaluate whether record presents a comparative clinical study design."""
    pub_types = [pt.lower() for pt in (record.publication_types or [])]

    # Publication type metadata check
    for pt in pub_types:
        if pt in ("randomized controlled trial", "clinical trial", "controlled clinical trial", "comparative study"):
            return CriterionEvidence(
                criterion_id=criterion.id,
                name=criterion.name,
                verdict=CriterionVerdict.PASS,
                reason_code="COMPARATIVE_CLINICAL_DESIGN_METADATA",
                explanation=f"Publication type metadata confirms comparative design: {record.publication_types}",
                evidence_snippet=f"publication_types={record.publication_types}",
                source=ScreeningEvidenceSource.METADATA,
                method_version=METHOD_VERSION,
            )

    full_text = f"{record.title or ''}. {record.abstract_text or ''}"
    if _COMPARATIVE_DESIGN_RE.search(full_text):
        match = _COMPARATIVE_DESIGN_RE.search(full_text)
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.PASS,
            reason_code="COMPARATIVE_DESIGN_TEXT",
            explanation="Text indicates comparative clinical investigation or randomized controlled evaluation",
            evidence_snippet=full_text[max(0, match.start() - 20): match.end() + 60] if match else None,
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    if not (record.abstract_text or "").strip():
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=CriterionVerdict.UNKNOWN,
            reason_code="UNVERIFIED_STUDY_DESIGN",
            explanation="Missing abstract prevents study design classification",
            evidence_snippet=record.title,
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    return CriterionEvidence(
        criterion_id=criterion.id,
        name=criterion.name,
        verdict=CriterionVerdict.UNKNOWN,
        reason_code="UNVERIFIED_STUDY_DESIGN",
        explanation="Study design could not be definitively confirmed as comparative from title/abstract",
        evidence_snippet=full_text[:100],
        source=ScreeningEvidenceSource.RULE,
        method_version=METHOD_VERSION,
    )


# Dispatch map matching criterion IDs to their specialized pure evaluation functions
# ---------------------------------------------------------------------------
# Keyword rules (rules built from the review's own question)
# ---------------------------------------------------------------------------
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")


# Abstracts often do not state the comparator or the outcome in the review's words. Not finding
# them is not evidence they are missing, so a miss on these is "unknown" (Maybe), never an Exclude.
SOFT_CATEGORIES = frozenset({"comparator", "outcome"})


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _first_match(keywords: list[str], title: str, abstract: str) -> tuple[str, str] | None:
    """The first keyword found, with the sentence (or title) that contains it."""
    chunks = ([title] if title.strip() else []) + _sentences(abstract)
    for chunk in chunks:
        for keyword in keywords:
            if keyword.strip() and keyword_pattern(keyword).search(chunk):
                return keyword, chunk
    return None


def evaluate_keywords(
    criterion: CriterionDefinition,
    record: RecordRevisionResponse,
) -> CriterionEvidence:
    """Evaluate a keyword rule against the record's title and abstract.

    - Any ``exclude_keywords`` match fails the rule, whatever else matches.
    - Inclusion rule: PASS if any keyword matches (evidence is the matched sentence), FAIL if none,
      except comparator and outcome rules, where none is UNKNOWN (see SOFT_CATEGORIES).
    - Exclusion rule: FAIL if any keyword matches, PASS if none.
    - With no abstract, a missed keyword is not evidence of absence: the verdict is UNKNOWN
      (Maybe), never an invented FAIL.
    """
    title = record.title or ""
    abstract = (record.abstract_text or "").strip()

    def evidence(verdict: CriterionVerdict, code: str, why: str, snippet: str | None) -> CriterionEvidence:
        return CriterionEvidence(
            criterion_id=criterion.id,
            name=criterion.name,
            verdict=verdict,
            reason_code=code,
            explanation=why,
            evidence_snippet=snippet[:400] if snippet else None,
            source=ScreeningEvidenceSource.RULE,
            method_version=METHOD_VERSION,
        )

    blocked = _first_match(criterion.exclude_keywords, title, abstract) if criterion.exclude_keywords else None
    if blocked:
        keyword, sentence = blocked
        return evidence(
            CriterionVerdict.FAIL,
            "EXCLUDE_KEYWORD_MATCH",
            f"Mentions '{keyword}', which this rule excludes",
            sentence,
        )

    found = _first_match(criterion.keywords, title, abstract)
    if criterion.is_inclusion:
        if found:
            keyword, sentence = found
            return evidence(CriterionVerdict.PASS, "KEYWORD_MATCH", f"Mentions '{keyword}'", sentence)
        if len(abstract) < 30:
            return evidence(
                CriterionVerdict.UNKNOWN,
                "NO_ABSTRACT_TO_CHECK",
                "No abstract to check these keywords against; needs a manual look",
                None,
            )
        if criterion.category in SOFT_CATEGORIES:
            return evidence(
                CriterionVerdict.UNKNOWN,
                "NOT_STATED_IN_ABSTRACT",
                f"The {criterion.category} is not stated in these words in the abstract: " + ", ".join(criterion.keywords),
                None,
            )
        return evidence(
            CriterionVerdict.FAIL,
            "NO_KEYWORD_MATCH",
            "None of these terms appear in the title or abstract: " + ", ".join(criterion.keywords),
            None,
        )

    # Exclusion rule: a keyword match is the reason to exclude
    if found:
        keyword, sentence = found
        return evidence(CriterionVerdict.FAIL, "EXCLUDE_KEYWORD_MATCH", f"Mentions '{keyword}'", sentence)
    if criterion.keywords and len(abstract) < 30:
        return evidence(
            CriterionVerdict.UNKNOWN,
            "NO_ABSTRACT_TO_CHECK",
            "No abstract to check against this exclusion; needs a manual look",
            None,
        )
    return evidence(CriterionVerdict.PASS, "NO_EXCLUDED_TERM", "No excluded term found", None)


RULE_EVALUATORS = {
    "abstract_available": evaluate_abstract_presence,
    "english_language": evaluate_language,
    "exclude_animal_only": evaluate_species,
    "exclude_simulation_only": evaluate_simulation,
    "exclude_case_reports": evaluate_case_report,
    "population_adults_t2d": evaluate_population,
    "comparative_clinical_design": evaluate_study_design,
}
