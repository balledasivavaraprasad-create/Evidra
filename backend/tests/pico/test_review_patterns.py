"""PICO spans found with the review's own P/I/C/O words, tested on a real abstract (EMPRISE East Asia)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import PicoLabel as L
from app.pico.extractor import METHOD_VERSION, RuleBasedPicoExtractor
from app.screening.generate import pico_terms_from_criteria, rules_from_pico
from app.worker import poll_and_execute_next

# PMID 33532619, fetched from PubMed (tests/fixtures/sources/emprise_33532619.json)
EMPRISE = json.loads((Path(__file__).parents[1] / "fixtures" / "sources" / "emprise_33532619.json").read_text(encoding="utf-8"))
ABSTRACT = EMPRISE["abstract_text"]

# The review the EMPRISE paper answers
EMPRISE_PICO = {
    "population": "patients with type 2 diabetes",
    "intervention": "empagliflozin",
    "comparator": "DPP-4 inhibitors",
    "outcome": "hospitalization for heart failure",
}
# The review used in the Phase 1 walkthrough
SGLT2_PICO = {
    "population": "adults with type 2 diabetes",
    "intervention": "SGLT2 inhibitor, empagliflozin, dapagliflozin, canagliflozin",
    "comparator": "placebo",
    "outcome": "heart failure hospitalization",
}


def extractor_for(pico: dict[str, str]) -> RuleBasedPicoExtractor:
    rules = rules_from_pico("review", "question", pico)
    return RuleBasedPicoExtractor(review_terms=pico_terms_from_criteria(pico, rules))


def spans_by_label(result) -> dict[L, list[str]]:
    out: dict[L, list[str]] = {}
    for s in result.spans:
        out.setdefault(s.label, []).append(s.quote)
    return out


class TestEmpriseAbstract:
    def test_all_four_elements_are_found_from_the_reviews_own_words(self):
        result = extractor_for(EMPRISE_PICO).extract_from_text(ABSTRACT, "emprise")
        found = spans_by_label(result)
        assert any("type 2 diabetes" in q for q in found[L.P])
        assert any(q.lower() == "empagliflozin" for q in found[L.I])
        assert any(q.lower().startswith("dpp-4 inhibitor") for q in found[L.C])
        assert any(q.lower() == "hospitalization for heart failure" for q in found[L.O])
        assert (result.has_population, result.has_intervention, result.has_comparator, result.has_outcome) == (True,) * 4

    def test_every_span_is_the_exact_slice_of_the_abstract(self):
        result = extractor_for(EMPRISE_PICO).extract_from_text(ABSTRACT, "emprise")
        assert result.spans
        for s in result.spans:
            assert ABSTRACT[s.start_cp : s.end_cp] == s.quote
            assert 0 <= s.start_cp < s.end_cp <= len(ABSTRACT)

    def test_the_phase_one_review_finds_population_intervention_and_outcome_in_other_wording(self):
        # Its outcome is worded "heart failure hospitalization"; the paper says "hospitalization for heart failure"
        found = spans_by_label(extractor_for(SGLT2_PICO).extract_from_text(ABSTRACT, "emprise"))
        assert any("type 2 diabetes" in q for q in found[L.P])
        assert any(q.lower() == "empagliflozin" for q in found[L.I])
        assert any(q.lower() == "hospitalization for heart failure" for q in found[L.O])

    def test_a_comparator_the_paper_does_not_state_is_not_invented(self):
        found = spans_by_label(extractor_for(SGLT2_PICO).extract_from_text(ABSTRACT, "emprise"))
        assert L.C not in found  # the review compares with placebo; this paper compares with DPP-4 inhibitors


class TestOtherReviewsAndGenericPatterns:
    def test_a_review_that_has_nothing_to_do_with_diabetes_is_found_in_its_own_words(self):
        text = "Adults with hypertension received ramipril or placebo. Stroke occurred in 4% of patients."
        pico = {"population": "adults with hypertension", "intervention": "ramipril", "comparator": "placebo", "outcome": "stroke"}
        found = spans_by_label(extractor_for(pico).extract_from_text(text))
        assert found[L.P] == ["Adults with hypertension"]
        assert found[L.I] == ["ramipril"]
        assert found[L.C] == ["placebo"]
        assert found[L.O] == ["Stroke"]

    def test_generic_patterns_still_work_without_review_terms(self):
        result = RuleBasedPicoExtractor().extract_from_text("Metformin versus placebo lowered HbA1c in adults with type 2 diabetes.")
        found = spans_by_label(result)
        assert L.I in found and L.C in found and L.O in found and L.P in found

    def test_no_review_terms_is_the_original_method_version(self):
        assert RuleBasedPicoExtractor().method_version == METHOD_VERSION


class TestMethodVersionIsTheCacheKey:
    def test_other_keywords_are_a_different_method_so_cached_pico_is_not_reused(self):
        a = extractor_for(EMPRISE_PICO).method_version
        b = extractor_for({**EMPRISE_PICO, "intervention": "dapagliflozin"}).method_version
        assert a != b
        assert a.startswith(METHOD_VERSION + "+review:")

    def test_the_same_keywords_are_the_same_method_whatever_else_changes(self):
        base = rules_from_pico("t", "q", EMPRISE_PICO)
        a = RuleBasedPicoExtractor(review_terms=pico_terms_from_criteria(EMPRISE_PICO, base))
        # a criteria change that drops the generic rules but keeps the PICO keywords
        fewer = [r for r in base if r.source == "pico"]
        b = RuleBasedPicoExtractor(review_terms=pico_terms_from_criteria(EMPRISE_PICO, fewer))
        assert a.method_version == b.method_version

    def test_keywords_edited_on_the_saved_rules_are_what_is_looked_for(self):
        rules = rules_from_pico("t", "q", EMPRISE_PICO)
        edited = [r.model_copy(update={"keywords": ["empagliflozin", "Jardiance"]}) if r.id == "pico_intervention" else r for r in rules]
        terms = pico_terms_from_criteria(EMPRISE_PICO, edited)
        assert terms[L.I] == ["empagliflozin", "Jardiance"]
        found = spans_by_label(RuleBasedPicoExtractor(review_terms=terms).extract_from_text("Jardiance was compared with a DPP-4 inhibitor."))
        assert found[L.I] == ["Jardiance"]


def make_processed_review(client: TestClient, db_session: Session) -> tuple[str, str]:
    """A review whose imported records have been processed, using the built-in fixture records."""
    pico = {"population": "adults with type 2 diabetes", "intervention": "metformin", "comparator": "placebo", "outcome": "HbA1c"}
    ws = client.post("/api/v1/workspaces", json={"title": "Metformin review"}).json()
    rules = client.post(f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json={"question": "q", "pico": pico}).json()["criteria"]
    crit = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria", json={"question": "q", "pico_description": pico, "criteria": rules}
    ).json()
    q = client.post(
        f"/api/v1/workspaces/{ws['id']}/queries",
        json={"ast": {"term": "metformin"}, "sources": ["pubmed"], "criteria_version_id": crit["id"]},
    ).json()
    execution = client.post(f"/api/v1/queries/{q['id']}/searches", json={"source": "pubmed", "synonym_expansion": False, "cap": 50}).json()
    client.post(
        f"/api/v1/workspaces/{ws['id']}/imports",
        json={"search_execution_ids": [execution["id"]], "cap": 20, "idempotency_key": "pico-test"},
    )
    poll_and_execute_next(db=db_session)  # import (queues processing)
    poll_and_execute_next(db=db_session)  # processing
    revision = client.get(f"/api/v1/workspaces/{ws['id']}/revisions").json()[0]
    return ws["id"], revision["id"]


class TestGroupDetailPico:
    def test_processing_finds_pico_in_the_imported_papers(self, client: TestClient, db_session: Session):
        _, revision_id = make_processed_review(client, db_session)
        groups = client.get(f"/api/v1/revisions/{revision_id}/groups").json()
        details = [client.get(f"/api/v1/groups/{g['id']}").json() for g in groups]
        with_spans = [d for d in details if d["pico_result"] and d["pico_result"]["spans"]]
        assert with_spans, "at least one processed paper should have PICO spans"
        for d in with_spans:
            assert d["human_pico"] is None  # nobody has edited anything
            rep = d["group"]["representative_revision"]
            for span in d["pico_result"]["spans"]:
                assert rep["abstract_text"][span["start_cp"] : span["end_cp"]] == span["quote"]

    def test_a_saved_edit_comes_back_with_the_group(self, client: TestClient, db_session: Session):
        _, revision_id = make_processed_review(client, db_session)
        groups = client.get(f"/api/v1/revisions/{revision_id}/groups").json()
        detail = next(
            d for d in (client.get(f"/api/v1/groups/{g['id']}").json() for g in groups) if d["pico_result"] and d["pico_result"]["spans"]
        )
        rep = detail["group"]["representative_revision"]
        keep = detail["pico_result"]["spans"][:1]
        saved = client.post(
            f"/api/v1/groups/{detail['group']['id']}/pico",
            json={
                "record_revision_id": rep["id"],
                "content_hash": detail["pico_result"]["content_hash"],
                "expected_version": detail["group"]["row_version"],
                "spans": keep,
            },
        )
        assert saved.status_code == 200, saved.text

        reloaded = client.get(f"/api/v1/groups/{detail['group']['id']}").json()
        assert [(s["label"], s["start_cp"], s["end_cp"], s["quote"]) for s in reloaded["human_pico"]] == [
            (s["label"], s["start_cp"], s["end_cp"], s["quote"]) for s in keep
        ]

    def test_the_latest_edit_replaces_the_one_before_and_an_empty_edit_is_kept(self, client: TestClient, db_session: Session):
        _, revision_id = make_processed_review(client, db_session)
        groups = client.get(f"/api/v1/revisions/{revision_id}/groups").json()
        detail = next(
            d for d in (client.get(f"/api/v1/groups/{g['id']}").json() for g in groups) if d["pico_result"] and d["pico_result"]["spans"]
        )
        rep = detail["group"]["representative_revision"]
        gid = detail["group"]["id"]

        def save(spans, version):
            return client.post(
                f"/api/v1/groups/{gid}/pico",
                json={"record_revision_id": rep["id"], "content_hash": detail["pico_result"]["content_hash"], "expected_version": version, "spans": spans},
            )

        first = save(detail["pico_result"]["spans"], detail["group"]["row_version"])
        assert first.status_code == 200, first.text
        version = client.get(f"/api/v1/groups/{gid}").json()["group"]["row_version"]
        assert save([], version).status_code == 200  # the reviewer removed every span
        assert client.get(f"/api/v1/groups/{gid}").json()["human_pico"] == []  # saved as empty, not "never edited"
