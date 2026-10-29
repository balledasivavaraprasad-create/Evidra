"""Source counts replayed from responses recorded from the real PubMed and Europe PMC services.

The fixture (tests/fixtures/sources/recorded_counts.json) holds the exact query each service was
asked and its real answer, so these tests run offline but prove the translated queries are ones
the services accept and answer with hits.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.contracts.models import QueryASTNode
from app.settings import settings
from app.sources.europepmc import EUROPEPMC_SEARCH_URL, EuropePMCAdapter
from app.sources.pubmed import ESEARCH_URL, PubMedAdapter
from app.sources.translator import build_europepmc_query, build_pubmed_query

RECORDED = json.loads((Path(__file__).parents[1] / "fixtures" / "sources" / "recorded_counts.json").read_text(encoding="utf-8"))

SENTENCE = "adults with type 2 diabetes who were hospitalized for heart failure"


def term(text: str) -> QueryASTNode:
    return QueryASTNode(term=text)


TERMS_AST = QueryASTNode(
    operator="AND",
    children=[
        QueryASTNode(
            operator="OR",
            children=[term("SGLT2 inhibitor"), term("empagliflozin"), term("dapagliflozin"), term("canagliflozin")],
        ),
        term("adults with type 2 diabetes"),
    ],
)
SENTENCE_AST = QueryASTNode(operator="AND", children=[term("empagliflozin"), term(SENTENCE)])


@pytest.fixture
def live_sources(monkeypatch):
    """Tests normally use built-in fixture counts; route them through the real adapters instead."""
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "source_mode", "live")
    monkeypatch.setattr(settings, "ci_offline", False)


class TestTranslation:
    def test_a_pico_sentence_is_not_one_exact_phrase(self):
        for query in (build_pubmed_query(SENTENCE_AST, "2019", "2026"), build_europepmc_query(SENTENCE_AST, "2019", "2026")):
            assert SENTENCE not in query
            assert '"heart failure"' in query and '"type 2 diabetes"' in query

    def test_leading_adults_with_is_dropped_and_short_terms_stay_exact(self):
        query = build_pubmed_query(TERMS_AST, "2019", "2026")
        assert '"type 2 diabetes"[Title/Abstract]' in query
        assert "adults with" not in query
        assert '"SGLT2 inhibitor"[Title/Abstract]' in query

    @pytest.mark.parametrize("name,ast", [("pico_terms", TERMS_AST), ("pico_sentence", SENTENCE_AST)])
    def test_queries_match_what_was_sent_to_the_real_services(self, name, ast):
        assert build_pubmed_query(ast, "2019", "2026") == RECORDED[name]["pubmed"]["query"]
        assert build_europepmc_query(ast, "2019", "2026") == RECORDED[name]["europepmc"]["query"]


class TestReplay:
    @pytest.mark.parametrize("name", ["pico_terms", "pico_sentence"])
    def test_pubmed_count_from_a_recorded_response(self, live_sources, name):
        rec = RECORDED[name]["pubmed"]
        with respx.mock(assert_all_called=True) as mock:
            route = mock.get(ESEARCH_URL).mock(return_value=httpx.Response(rec["status"], json=rec["body"]))
            result = PubMedAdapter().search_count("qv-1", rec["query"])
        assert route.calls.last.request.url.params["term"] == rec["query"]
        assert result.hit_count == int(rec["body"]["esearchresult"]["count"]) > 0

    @pytest.mark.parametrize("name", ["pico_terms", "pico_sentence"])
    def test_europepmc_count_from_a_recorded_response(self, live_sources, name):
        rec = RECORDED[name]["europepmc"]
        with respx.mock(assert_all_called=True) as mock:
            route = mock.get(EUROPEPMC_SEARCH_URL).mock(return_value=httpx.Response(rec["status"], json=rec["body"]))
            result = EuropePMCAdapter().search_count("qv-1", rec["query"])
        assert route.calls.last.request.url.params["query"] == rec["query"]
        assert result.hit_count == int(rec["body"]["hitCount"]) > 0


def saved_query(client, ast: dict) -> tuple[str, str]:
    ws = client.post("/api/v1/workspaces", json={"title": "SGLT2i review"}).json()
    rules = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria/suggest",
        json={"question": "q", "pico": {"population": "adults with type 2 diabetes", "intervention": "empagliflozin"}},
    ).json()["criteria"]
    crit = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria",
        json={"question": "q", "pico_description": {"population": "adults with type 2 diabetes"}, "criteria": rules},
    ).json()
    q = client.post(
        f"/api/v1/workspaces/{ws['id']}/queries",
        json={"ast": ast, "sources": ["pubmed", "europepmc"], "criteria_version_id": crit["id"]},
    )
    assert q.status_code in (200, 201), q.text
    return q.json()["id"], ws["id"]


AST = {"operator": "AND", "children": [{"term": "empagliflozin"}, {"term": "heart failure"}]}


class TestCountRoute:
    def test_europepmc_failures_become_a_readable_502(self, client, live_sources):
        qid, _ = saved_query(client, AST)
        for failure, expected in [
            (httpx.ConnectTimeout("slow"), "the request timed out"),
            (httpx.ConnectError("refused"), "could not connect"),
            (httpx.Response(503), "it answered with HTTP 503"),
        ]:
            with respx.mock() as mock:
                route = mock.get(EUROPEPMC_SEARCH_URL)
                route.mock(side_effect=failure) if isinstance(failure, Exception) else route.mock(return_value=failure)
                resp = client.post(f"/api/v1/queries/{qid}/searches", json={"source": "europepmc", "synonym_expansion": False})
            assert resp.status_code == 502, resp.text
            body = resp.json()
            assert body["code"] == "SOURCE_UNAVAILABLE"
            assert body["message"] == f"Europe PMC didn't respond: {expected}"
            assert body["retryable"] is True

    def test_pubmed_failures_name_pubmed(self, client, live_sources):
        qid, _ = saved_query(client, AST)
        with respx.mock() as mock:
            mock.get(ESEARCH_URL).mock(side_effect=httpx.ReadTimeout("slow"))
            resp = client.post(f"/api/v1/queries/{qid}/searches", json={"source": "pubmed", "synonym_expansion": False})
        assert resp.status_code == 502
        assert resp.json()["message"].startswith("PubMed didn't respond:")

    def test_an_unreadable_answer_is_a_502_not_a_crash(self, client, live_sources):
        qid, _ = saved_query(client, AST)
        with respx.mock() as mock:
            mock.get(EUROPEPMC_SEARCH_URL).mock(return_value=httpx.Response(200, text="<html>not json</html>"))
            resp = client.post(f"/api/v1/queries/{qid}/searches", json={"source": "europepmc", "synonym_expansion": False})
        assert resp.status_code == 502
        assert resp.json()["code"] == "SOURCE_UNAVAILABLE"

    def test_a_count_with_hits_is_ticked_and_one_with_none_is_not(self, client, live_sources):
        qid, ws_id = saved_query(client, AST)
        rec = RECORDED["pico_terms"]
        with respx.mock() as mock:
            mock.get(ESEARCH_URL).mock(return_value=httpx.Response(200, json=rec["pubmed"]["body"]))
            mock.get(EUROPEPMC_SEARCH_URL).mock(return_value=httpx.Response(200, json={"hitCount": 0, "resultList": {"result": []}}))
            found = client.post(f"/api/v1/queries/{qid}/searches", json={"source": "pubmed", "synonym_expansion": False}).json()
            nothing = client.post(f"/api/v1/queries/{qid}/searches", json={"source": "europepmc", "synonym_expansion": False}).json()

        assert found["hit_count"] > 0 and found["selected_for_import"] is True
        assert nothing["hit_count"] == 0 and nothing["selected_for_import"] is False
        listed = {e["id"]: e["selected_for_import"] for e in client.get(f"/api/v1/workspaces/{ws_id}/executions").json()}
        assert listed == {found["id"]: True, nothing["id"]: False}

        refused = client.patch(f"/api/v1/executions/{nothing['id']}", json={"selected_for_import": True})
        assert refused.status_code == 400
        assert client.patch(f"/api/v1/executions/{nothing['id']}", json={"selected_for_import": False}).status_code == 200
