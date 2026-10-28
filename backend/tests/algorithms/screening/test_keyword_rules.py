"""Screening rules built from the review's own question: keyword evaluation and rule generation."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.contracts.enums import CriterionVerdict, EligibilityStatus, SourceNamespace
from app.contracts.models import CriteriaVersionResponse, CriterionDefinition, RecordRevisionResponse
from app.gateway.protocol import GatewayErrorCode, GatewayRequest, GatewayResponse
from app.gateway.synonyms import SynonymProvider
from app.screening import ScreeningEngine
from app.screening.defaults import compute_criteria_hash
from app.screening.generate import GENERIC_RULE_IDS, rules_from_pico, split_keywords
from app.screening.rules import evaluate_keywords

LONG_ABSTRACT = (
    "BACKGROUND: Heart failure is common. METHODS: We compared empagliflozin with DPP-4 inhibitors in "
    "adults with type 2 diabetes. RESULTS: Empagliflozin lowered hospitalization for heart failure. "
    "CONCLUSION: Benefits were consistent."
)


def record(title: str = "A cohort study", abstract: str | None = LONG_ABSTRACT, rid: str = "r1") -> RecordRevisionResponse:
    return RecordRevisionResponse(
        id=rid,
        source_record_id=f"src-{rid}",
        source=SourceNamespace.PUBMED,
        source_namespace="pubmed",
        external_id=f"pmid-{rid}",
        content_hash=f"hash-{rid}",
        title=title,
        abstract_text=abstract,
        year=2021,
        journal="J",
        authors=["Smith A"],
        publication_types=["Journal Article"],
        language=["eng"],
        fetched_at=datetime(2026, 10, 28, tzinfo=UTC),
    )


def rule(keywords: list[str], *, exclude: list[str] | None = None, inclusion: bool = True) -> CriterionDefinition:
    return CriterionDefinition(
        id="kw",
        name="Keyword rule",
        category="intervention",
        is_inclusion=inclusion,
        rationale="test",
        metadata_first=False,
        keywords=keywords,
        exclude_keywords=exclude or [],
    )


class TestEvaluateKeywords:
    def test_inclusion_passes_on_any_keyword_and_quotes_the_matched_sentence(self):
        ev = evaluate_keywords(rule(["dapagliflozin", "empagliflozin"]), record())
        assert ev.verdict == CriterionVerdict.PASS
        assert ev.evidence_snippet is not None
        assert "empagliflozin" in ev.evidence_snippet.lower()
        assert ev.evidence_snippet.startswith("METHODS") or ev.evidence_snippet.startswith("RESULTS")
        assert "." not in ev.evidence_snippet[:-1] or len(ev.evidence_snippet) < len(LONG_ABSTRACT)

    def test_inclusion_fails_when_no_keyword_matches(self):
        ev = evaluate_keywords(rule(["metformin", "sitagliptin"]), record())
        assert ev.verdict == CriterionVerdict.FAIL
        assert ev.reason_code == "NO_KEYWORD_MATCH"

    def test_case_insensitive_and_phrase_with_any_spacing(self):
        assert evaluate_keywords(rule(["HEART  FAILURE"]), record()).verdict == CriterionVerdict.PASS

    def test_whole_word_only(self):
        rec = record(abstract="The placebo group and T2DM patients were followed for twelve months in clinics.")
        assert evaluate_keywords(rule(["placebo"]), rec).verdict == CriterionVerdict.PASS
        assert evaluate_keywords(rule(["T2D"]), rec).verdict == CriterionVerdict.FAIL  # not inside T2DM
        assert evaluate_keywords(rule(["place"]), rec).verdict == CriterionVerdict.FAIL  # not inside placebo

    def test_a_plural_still_matches(self):
        assert evaluate_keywords(rule(["DPP-4 inhibitor"]), record()).verdict == CriterionVerdict.PASS

    def test_the_title_counts_too(self):
        rec = record(title="Empagliflozin outcomes", abstract="Short unrelated text about something else entirely here.")
        assert evaluate_keywords(rule(["empagliflozin"]), rec).verdict == CriterionVerdict.PASS

    def test_exclude_keywords_fail_the_rule_even_if_a_keyword_matches(self):
        ev = evaluate_keywords(rule(["empagliflozin"], exclude=["DPP-4 inhibitors"]), record())
        assert ev.verdict == CriterionVerdict.FAIL
        assert ev.reason_code == "EXCLUDE_KEYWORD_MATCH"
        assert ev.evidence_snippet and "DPP-4" in ev.evidence_snippet

    def test_exclusion_rule_fails_on_a_match_and_passes_otherwise(self):
        assert evaluate_keywords(rule(["empagliflozin"], inclusion=False), record()).verdict == CriterionVerdict.FAIL
        assert evaluate_keywords(rule(["rats"], inclusion=False), record()).verdict == CriterionVerdict.PASS

    def test_no_abstract_is_unknown_not_an_invented_fail(self):
        ev = evaluate_keywords(rule(["empagliflozin"]), record(title="Untitled", abstract=None))
        assert ev.verdict == CriterionVerdict.UNKNOWN


class TestEngineRouting:
    def _criteria(self, criteria: list[CriterionDefinition]) -> CriteriaVersionResponse:
        return CriteriaVersionResponse(
            id="c1",
            workspace_id="w1",
            sequence=1,
            question="q",
            pico_description={},
            criteria=criteria,
            content_hash=compute_criteria_hash(criteria),
            created_at=datetime(2026, 10, 28, tzinfo=UTC),
        )

    def test_keyword_rules_decide_include_and_exclude(self):
        criteria = self._criteria([rule(["empagliflozin"])])
        assert ScreeningEngine().screen_record(record(), criteria).status == EligibilityStatus.INCLUDE
        other = record(abstract="Statins were studied in a large population of adults over many years of follow-up.")
        assert ScreeningEngine().screen_record(other, criteria).status == EligibilityStatus.EXCLUDE

    def test_old_criteria_without_keywords_still_use_their_id_evaluators(self):
        old = CriterionDefinition(
            id="exclude_animal_only", name="No animal-only", category="species", is_inclusion=False, rationale="r"
        )
        rats = record(abstract="Wistar rats were studied for twelve weeks. Wistar rats only were used throughout.")
        ev = ScreeningEngine().evaluate_criterion(rats, old)
        assert ev.verdict == CriterionVerdict.FAIL
        assert ev.reason_code == "ANIMAL_STUDY_EXCLUDED"  # from the old evaluator, not a keyword rule

    def test_keywords_change_the_criteria_hash(self):
        a = [rule(["empagliflozin"])]
        b = [rule(["dapagliflozin"])]
        assert compute_criteria_hash(a) != compute_criteria_hash(b)
        plain = [CriterionDefinition(id="x", name="n", category="c", is_inclusion=True, rationale="r")]
        assert compute_criteria_hash(plain) == compute_criteria_hash(
            [CriterionDefinition(id="x", name="n", category="c", is_inclusion=True, rationale="r")]
        )


class TestSplitKeywords:
    def test_splits_on_commas_or_semicolons_slashes_and_parentheses(self):
        assert split_keywords("SGLT2 inhibitor, empagliflozin; dapagliflozin / canagliflozin (Invokana) or ertugliflozin") == [
            "SGLT2 inhibitor",
            "empagliflozin",
            "dapagliflozin",
            "canagliflozin",
            "Invokana",
            "ertugliflozin",
        ]

    def test_drops_stop_words_and_duplicates(self):
        assert split_keywords("the placebo, Placebo, of, and") == ["placebo"]
        assert split_keywords("  ") == []
        assert split_keywords(None) == []

    def test_population_lead_is_removed_so_the_condition_is_matched(self):
        assert split_keywords("patients with type 2 diabetes", population=True) == ["type 2 diabetes"]
        assert split_keywords("adults with heart failure or older adults with kidney disease", population=True) == [
            "heart failure",
            "kidney disease",
        ]

    def test_outcome_word_order_variant_is_added(self):
        assert "heart failure hospitalization" in split_keywords("hospitalization for heart failure")


PICO = {
    "population": "adults with type 2 diabetes",
    "intervention": "SGLT2 inhibitor, empagliflozin, dapagliflozin",
    "comparator": "placebo",
    "outcome": "heart failure hospitalization",
}


class TestRulesFromPico:
    def test_one_inclusion_rule_per_filled_field_then_generic_rules(self):
        rules = rules_from_pico("t", "q", PICO)
        assert [r.id for r in rules[:4]] == ["pico_population", "pico_intervention", "pico_comparator", "pico_outcome"]
        assert all(r.source == "pico" and r.is_inclusion and r.keywords for r in rules[:4])
        assert [r.id for r in rules[4:]] == list(GENERIC_RULE_IDS)
        assert all(r.source == "generic" and not r.keywords for r in rules[4:])
        assert rules[1].keywords == ["SGLT2 inhibitor", "empagliflozin", "dapagliflozin"]

    def test_empty_fields_get_no_rule(self):
        rules = rules_from_pico("t", "q", {"population": "adults with asthma", "intervention": "  "})
        assert [r.id for r in rules if r.source == "pico"] == ["pico_population"]

    def test_short_pico_keys_work_too(self):
        rules = rules_from_pico("t", "q", {"P": "women with breast cancer", "I": "tamoxifen"})
        assert [r.id for r in rules if r.source == "pico"] == ["pico_population", "pico_intervention"]

    def test_generic_rules_never_mention_a_condition_or_drug(self):
        rules = rules_from_pico("Breast cancer", "q", {"population": "women with breast cancer", "intervention": "tamoxifen"})
        text = json.dumps([r.model_dump() for r in rules if r.source == "generic"]).lower()
        for word in ("diabet", "metformin", "hba1c", "t2d", "glucose"):
            assert word not in text
        assert not any("metformin" in json.dumps(r.model_dump()).lower() for r in rules)

    def test_no_pico_gives_only_the_generic_rules(self):
        assert [r.id for r in rules_from_pico("t", "q", {})] == list(GENERIC_RULE_IDS)

    def test_deterministic(self):
        assert rules_from_pico("t", "q", PICO) == rules_from_pico("t", "q", PICO)

    def test_generated_rules_screen_a_matching_abstract_in_and_a_mismatch_out(self):
        rules = rules_from_pico("t", "q", {**PICO, "comparator": "", "outcome": ""})
        criteria = CriteriaVersionResponse(
            id="c1", workspace_id="w1", sequence=1, question="q", pico_description=PICO, criteria=rules,
            content_hash=compute_criteria_hash(rules), created_at=datetime(2026, 10, 28, tzinfo=UTC),
        )
        hit = record(title="Empagliflozin versus DPP-4 inhibitors: a randomized comparative cohort study")
        assert ScreeningEngine().screen_record(hit, criteria).status == EligibilityStatus.INCLUDE
        miss = record(title="Statins in stroke", abstract="Statins were compared in a randomized trial of adults after stroke, with follow-up.")
        assert ScreeningEngine().screen_record(miss, criteria).status == EligibilityStatus.EXCLUDE


class FakeGateway:
    def __init__(self, response: GatewayResponse):
        self.response = response
        self.requests: list[GatewayRequest] = []

    def is_enabled(self) -> bool:
        return True

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        self.requests.append(request)
        return self.response


class TestAiSynonyms:
    def test_synonyms_are_added_to_p_and_i_only_and_marked(self):
        gw = FakeGateway(GatewayResponse(success=True, data={"synonyms": ["canagliflozin", "empagliflozin", "ertugliflozin", "<script>"]}))
        provider = SynonymProvider(gateway=gw, model_alias="gemini-2.5-flash")
        rules = {r.id: r for r in rules_from_pico("t", "q", PICO, synonyms=provider)}
        assert rules["pico_intervention"].keywords[-2:] == ["canagliflozin", "ertugliflozin"]
        assert rules["pico_intervention"].ai_suggested_keywords == ["canagliflozin", "ertugliflozin"]
        assert rules["pico_comparator"].ai_suggested_keywords == []
        assert rules["pico_outcome"].ai_suggested_keywords == []
        assert "<script>" not in json.dumps(rules["pico_intervention"].model_dump())
        assert {req.task_name for req in gw.requests} == {"keyword_synonyms"}
        assert len(gw.requests) == 2  # population and intervention

    def test_a_failing_model_leaves_the_deterministic_rules_untouched(self):
        gw = FakeGateway(GatewayResponse(success=False, error_code=GatewayErrorCode.PROVIDER_ERROR, error_message="quota exceeded"))
        provider = SynonymProvider(gateway=gw, model_alias="gemini-2.5-flash")
        assert rules_from_pico("t", "q", PICO, synonyms=provider) == rules_from_pico("t", "q", PICO)
        assert provider.problems and "quota exceeded" in provider.problems[0]

    def test_garbage_answers_are_ignored(self):
        for data in ({"synonyms": "empagliflozin"}, {"other": []}, {"synonyms": [1, None, "x" * 200]}):
            provider = SynonymProvider(gateway=FakeGateway(GatewayResponse(success=True, data=data)), model_alias="m")
            assert rules_from_pico("t", "q", PICO, synonyms=provider) == rules_from_pico("t", "q", PICO)


class TestSuggestEndpoint:
    def test_suggest_returns_rules_and_saves_nothing(self, client):
        ws = client.post("/api/v1/workspaces", json={"title": "SGLT2i and HF"}).json()
        resp = client.post(
            f"/api/v1/workspaces/{ws['id']}/criteria/suggest",
            json={"question": "Do SGLT2 inhibitors reduce HF hospitalization?", "pico": PICO},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ai_synonyms_used"] is False
        ids = [c["id"] for c in body["criteria"]]
        assert ids[:4] == ["pico_population", "pico_intervention", "pico_comparator", "pico_outcome"]
        assert "metformin" not in json.dumps(body).lower()
        assert client.get(f"/api/v1/workspaces/{ws['id']}/criteria").status_code == 404  # nothing saved

    def test_suggested_rules_can_be_saved_as_a_criteria_version(self, client):
        ws = client.post("/api/v1/workspaces", json={"title": "Review"}).json()
        rules = client.post(f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json={"question": "q", "pico": PICO}).json()["criteria"]
        saved = client.post(
            f"/api/v1/workspaces/{ws['id']}/criteria",
            json={"question": "q", "pico_description": PICO, "criteria": rules},
        )
        assert saved.status_code == 201, saved.text
        latest = client.get(f"/api/v1/workspaces/{ws['id']}/criteria").json()
        assert latest["criteria"][1]["keywords"] == ["SGLT2 inhibitor", "empagliflozin", "dapagliflozin"]

    def test_unknown_workspace_is_404(self, client):
        assert client.post("/api/v1/workspaces/nope/criteria/suggest", json={"question": "q", "pico": {}}).status_code == 404

    @pytest.mark.parametrize("body", [{"question": "q", "pico": {}, "extra": 1}, {"pico": "not a dict"}])
    def test_bad_bodies_are_rejected(self, client, body):
        ws = client.post("/api/v1/workspaces", json={"title": "Review"}).json()
        assert client.post(f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json=body).status_code == 422
