"""Adversarial and boundary regression test suite for deduplication and screening algorithms (B03).

Covers edge cases, punctuation and unicode variance, contradictory identifiers,
same-study vs same-paper separation, cannot-link partitioning, negation handling,
and order permutation invariance.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.contracts.enums import CriterionVerdict, EligibilityStatus, SourceNamespace
from app.contracts.models import RecordRevisionResponse
from app.dedup import find_candidate_pairs, partition_groups
from app.screening import ScreeningEngine, get_default_criteria_version


def create_record(
    record_id: str,
    title: str,
    abstract: str | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    authors: list[str] | None = None,
    year: int | None = 2024,
    journal: str | None = "Journal of Clinical Medicine",
    pub_types: list[str] | None = None,
    language: list[str] | None = None,
) -> RecordRevisionResponse:
    """Helper to construct strongly-typed RecordRevisionResponse for testing."""
    return RecordRevisionResponse(
        id=record_id,
        source_record_id=f"src-{record_id}",
        source=SourceNamespace.PUBMED,
        source_namespace="pubmed",
        external_id=f"pmid-{record_id}",
        content_hash=f"hash-{record_id}",
        title=title,
        abstract_text=abstract,
        year=year,
        journal=journal,
        doi=doi,
        pmid=pmid,
        authors=authors or ["Smith A", "Jones B"],
        publication_types=pub_types or ["Clinical Trial"],
        language=language or ["eng"],
        fetched_at=datetime(2026, 10, 28, 0, 0, 0, tzinfo=UTC),
    )


class TestDeduplicationAdversarial:
    """Adversarial tests for deterministic deduplication matcher and partitioner."""

    def test_unicode_and_punctuation_title_matching_without_doi(self):
        """Title with accents, curly quotes, and em-dashes should match normalized counterpart."""
        rec_a = create_record(
            "rec-adv-001",
            title="Efficacy of Metformin—A Double-Blind “Placebo-Controlled” Trial in Résumé Patients",
            abstract="Adult patients received metformin over 24 weeks. HbA1c improved.",
            authors=["Müller J", "O'Connor R", "Saint-Clair P"],
            year=2023,
        )
        rec_b = create_record(
            "rec-adv-002",
            title="Efficacy of Metformin - A Double-Blind \"Placebo-Controlled\" Trial in Resume Patients",
            abstract="Adult patients received metformin over 24 weeks. HbA1c improved.",
            authors=["Muller J", "O'Connor R", "Saint-Clair P"],
            year=2023,
        )
        proposals = find_candidate_pairs([rec_a, rec_b])
        assert len(proposals) == 1
        assert proposals[0].score >= 0.80
        assert proposals[0].evidence.get("title_token_similarity", 0) >= 90.0

    def test_contradictory_doi_strictly_prevents_merge(self):
        """Even with identical title and authors, differing valid DOIs must never be proposed as duplicate."""
        rec_a = create_record(
            "rec-adv-003",
            title="Safety and Efficacy of Sodium-Glucose Cotransporter 2 Inhibitors in Type 2 Diabetes",
            doi="10.1001/jama.2023.1001",
            authors=["Smith A", "Jones B"],
            year=2023,
        )
        rec_b = create_record(
            "rec-adv-004",
            title="Safety and Efficacy of Sodium-Glucose Cotransporter 2 Inhibitors in Type 2 Diabetes",
            doi="10.1001/jama.2023.1002",  # Different DOI
            authors=["Smith A", "Jones B"],
            year=2023,
        )
        proposals = find_candidate_pairs([rec_a, rec_b])
        assert len(proposals) == 0

    def test_same_study_protocol_vs_results_separation(self):
        """Trial protocol and final trial results sharing NCT registry ID are NOT duplicate papers."""
        rec_proto = create_record(
            "rec-adv-005",
            title="Design and Rationale of the EMPA-REG Trial: Study Protocol",
            abstract="Clinical trial registration NCT01131676. Study design and methodology protocol.",
            year=2012,
        )
        rec_results = create_record(
            "rec-adv-006",
            title="Empagliflozin, Cardiovascular Outcomes, and Mortality in Type 2 Diabetes",
            abstract="Final results of trial NCT01131676. Significant reduction in cardiovascular deaths.",
            year=2015,
        )
        proposals = find_candidate_pairs([rec_proto, rec_results])
        assert len(proposals) == 0

    def test_order_permutation_invariance(self):
        """The candidate detection and grouping results must be identical regardless of input order."""
        records = [
            create_record("rec-01", "Paper Alpha: Phase 3 Trial of Metformin", doi="10.1000/alpha"),
            create_record("rec-02", "Paper Alpha: Phase 3 Trial of Metformin", doi="10.1000/alpha"),
            create_record("rec-03", "Paper Beta: Longitudinal Cohort Study", doi="10.1000/beta"),
            create_record("rec-04", "Paper Gamma: Observational Study", doi="10.1000/gamma"),
        ]

        proposals_fwd = find_candidate_pairs(records)
        proposals_rev = find_candidate_pairs(list(reversed(records)))

        assert len(proposals_fwd) == len(proposals_rev)
        assert proposals_fwd[0].record_id_a == proposals_rev[0].record_id_a
        assert proposals_fwd[0].record_id_b == proposals_rev[0].record_id_b

    def test_cannot_link_constraint_partitioning(self):
        """Partitioning enforces cannot-link constraint even when transitive similarity exists."""
        rec_a = create_record("rec-cl-01", "Clinical trial report of Metformin in type 2 diabetes")
        rec_b = create_record("rec-cl-02", "Clinical trial report of Metformin in type 2 diabetes")
        rec_c = create_record("rec-cl-03", "Clinical trial report of Metformin in type 2 diabetes")

        # Propose all pairwise
        proposals = find_candidate_pairs([rec_a, rec_b, rec_c])
        assert len(proposals) > 0

        # Add explicit cannot-link between A and C
        cannot_link = {("rec-cl-01", "rec-cl-03"), ("rec-cl-03", "rec-cl-01")}

        groups = partition_groups([rec_a, rec_b, rec_c], proposals, cannot_link_pairs=cannot_link)

        # Ensure A and C are in distinct groups
        group_a = next(g for g in groups if "rec-cl-01" in g["member_ids"])
        group_c = next(g for g in groups if "rec-cl-03" in g["member_ids"])
        assert group_a["group_id"] != group_c["group_id"]


class TestScreeningAdversarial:
    """Adversarial tests for context-aware and explainable screening rules."""

    def setup_method(self):
        self.engine = ScreeningEngine()
        self.criteria = get_default_criteria_version()

    def test_negation_in_abstract_does_not_trigger_false_exclusion(self):
        """Phrases like 'no animal models were used' must not trigger animal study exclusion."""
        record = create_record(
            "rec-scr-adv-01",
            title="Randomized evaluation of oral metformin in adults with type 2 diabetes",
            abstract=(
                "Unlike in animal models where rodents showed toxic reactions, this human clinical trial "
                "evaluated 200 human participants with type 2 diabetes. No rodents or animals were utilized. "
                "Patients were randomized to receive metformin 500mg or placebo. HbA1c reduced by 1.2%."
            ),
        )
        verdict = self.engine.screen_record(record, self.criteria)
        assert verdict.status == EligibilityStatus.INCLUDE
        assert "ANIMAL_STUDY_EXCLUDED" not in verdict.reasons

    def test_cohort_of_cases_distinguished_from_single_case_report(self):
        """Cohort of 500 cases in observational study should NOT be excluded as a single case report."""
        record = create_record(
            "rec-scr-adv-02",
            title="Metformin and lactic acidosis: analysis of 450 incident cases in clinical practice",
            abstract=(
                "We conducted a retrospective cohort study analyzing 450 incident cases and matched controls "
                "in adult patients with type 2 diabetes receiving metformin over 10 years. "
                "Results demonstrated an incidence of 3.3 cases per 100,000 patient-years."
            ),
        )
        verdict = self.engine.screen_record(record, self.criteria)
        assert verdict.status == EligibilityStatus.INCLUDE
        assert "CASE_REPORT_EXCLUDED" not in verdict.reasons

    def test_empty_or_truncated_abstract_yields_honest_maybe(self):
        """Missing or very short abstract text must yield MAYBE with missing abstract explanation."""
        record_empty = create_record(
            "rec-scr-adv-03",
            title="Clinical utility of metformin in type 2 diabetes mellitus",
            abstract=None,
        )
        verdict_empty = self.engine.screen_record(record_empty, self.criteria)
        assert verdict_empty.status == EligibilityStatus.MAYBE
        assert any(e.verdict == CriterionVerdict.UNKNOWN for e in verdict_empty.criteria_evidence)

        record_short = create_record(
            "rec-scr-adv-04",
            title="Brief update on metformin",
            abstract="Study in progress.",
        )
        verdict_short = self.engine.screen_record(record_short, self.criteria)
        assert verdict_short.status == EligibilityStatus.MAYBE

    def test_non_english_article_exclusion(self):
        """Articles flagged with non-English language tag must be excluded with clear reason."""
        record_foreign = create_record(
            "rec-scr-adv-05",
            title="Therapie des Diabetes mellitus Typ 2 mit Metformin: eine Übersicht",
            abstract="Eine randomisierte klinische Studie bei Patienten mit Typ-2-Diabetes.",
            language=["ger"],
        )
        verdict = self.engine.screen_record(record_foreign, self.criteria)
        assert verdict.status == EligibilityStatus.EXCLUDE
        assert "NON_ENGLISH_LANGUAGE" in verdict.reasons
