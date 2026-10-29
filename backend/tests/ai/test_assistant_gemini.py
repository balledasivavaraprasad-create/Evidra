"""The assistant route, the Gemini adapter settings and plain-language AI errors (no real calls: respx)."""
from __future__ import annotations

import json
from typing import ClassVar

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.gateway.adapter import HTTPXModelAdapter
from app.gateway.protocol import GatewayErrorCode, GatewayRequest
from app.services.evidence import SqliteEvidenceRepository
from app.settings import settings
from tests.pico.test_review_patterns import make_processed_review

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
KEY = "test-key-not-a-real-secret"


@pytest.fixture
def ai_on(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "rag_enabled", True)
    monkeypatch.setattr(settings, "llm_api_key", KEY)
    monkeypatch.setattr(settings, "llm_model_alias", "gemini-2.5-flash")
    monkeypatch.delenv("LLM_ENABLED", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)


def reply(content: str | dict, status: int = 200) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(status, json={"choices": [{"message": {"content": text}}], "usage": {"total_tokens": 120}})


def first_group(client: TestClient, db_session: Session) -> tuple[str, dict]:
    ws_id, revision_id = make_processed_review(client, db_session)
    groups = client.get(f"/api/v1/revisions/{revision_id}/groups").json()
    return ws_id, groups[0]


def ask(client: TestClient, ws_id: str, group_id: str, prompt: str = "Why should this paper be included?"):
    return client.post(
        f"/api/v1/workspaces/{ws_id}/assistant",
        json={"task": "explain_screening", "target_id": group_id, "user_prompt": prompt},
    )


class TestAssistantRoute:
    def test_it_no_longer_crashes_and_answers_with_a_verified_citation(self, client, db_session, ai_on):
        ws_id, group = first_group(client, db_session)
        handle = None
        with respx.mock(assert_all_called=True) as mock:
            def answer(request: httpx.Request) -> httpx.Response:
                body = json.loads(request.content)
                chunks = json.loads(body["messages"][1]["content"])["evidence_chunks"]
                nonlocal handle
                handle = chunks[0]["citation_handle"]  # the paper the question is about comes first
                return reply({"proposal_text": f"Include it: it studies the review's topic {handle}.", "cited_handles": [handle], "confidence_rationale": "The abstract matches."})

            route = mock.post(GEMINI_URL).mock(side_effect=answer)
            resp = ask(client, ws_id, group["id"])

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["model_error"] is None
        assert body["proposal_text"].startswith("Include it")
        assert [c["citation_handle"] for c in body["citations"]] == [handle]
        sent = route.calls.last.request
        assert json.loads(sent.content)["model"] == "gemini-2.5-flash"
        assert sent.headers["authorization"] == f"Bearer {KEY}"
        assert KEY not in resp.text  # the key never goes back to the browser

    def test_the_selected_paper_is_the_first_evidence_not_just_the_first_in_the_corpus(self, client, db_session):
        ws_id, revision_id = make_processed_review(client, db_session)
        groups = client.get(f"/api/v1/revisions/{revision_id}/groups").json()
        repo = SqliteEvidenceRepository(db_session)
        for g in groups[:4]:
            rep = g["representative_revision"]
            chunk = repo.chunk_for_target(ws_id, revision_id, g["id"])
            assert chunk is not None and chunk.record_revision_id == rep["id"]

    def test_another_reviews_paper_is_never_returned(self, client, db_session):
        _, revision_id = make_processed_review(client, db_session)
        other = client.post("/api/v1/workspaces", json={"title": "Another review"}).json()
        gid = client.get(f"/api/v1/revisions/{revision_id}/groups").json()[0]["id"]
        assert SqliteEvidenceRepository(db_session).chunk_for_target(other["id"], revision_id, gid) is None

    def test_model_failures_come_back_as_plain_language_with_the_papers_own_text(self, client, db_session, ai_on):
        ws_id, group = first_group(client, db_session)
        cases = [
            (httpx.Response(400, json={"error": {"message": "API key not valid. Please pass a valid API key."}}), "rejected the API key"),
            (httpx.Response(429, json={"error": {"message": "Resource has been exhausted (e.g. check quota)."}}), "quota or rate limit"),
            (httpx.Response(503, text="overloaded"), "problem on its side"),
        ]
        for response, expected in cases:
            with respx.mock() as mock:
                mock.post(GEMINI_URL).mock(return_value=response)
                body = ask(client, ws_id, group["id"]).json()
            assert expected in body["model_error"], body
            assert body["citations"], "the paper's own text is still shown"
            assert KEY not in json.dumps(body)

    def test_a_timeout_is_explained(self, client, db_session, ai_on):
        ws_id, group = first_group(client, db_session)
        with respx.mock() as mock:
            mock.post(GEMINI_URL).mock(side_effect=httpx.ReadTimeout("slow"))
            body = ask(client, ws_id, group["id"]).json()
        assert "too long" in body["model_error"]

    def test_with_no_key_ai_is_off_and_nothing_is_sent(self, client, db_session, ai_on, monkeypatch):
        monkeypatch.setattr(settings, "llm_api_key", None)
        ws_id, group = first_group(client, db_session)
        with respx.mock(assert_all_called=False) as mock:
            route = mock.post(GEMINI_URL)
            resp = ask(client, ws_id, group["id"])
        assert resp.status_code == 200
        assert "no API key" in resp.json()["model_error"]
        assert not route.called
        assert client.get("/api/v1/capabilities").json()["llm_enabled"] is False

    def test_an_answer_in_a_json_code_fence_is_accepted(self, client, db_session, ai_on):
        ws_id, group = first_group(client, db_session)
        with respx.mock() as mock:
            def answer(request: httpx.Request) -> httpx.Response:
                handle = json.loads(json.loads(request.content)["messages"][1]["content"])["evidence_chunks"][0]["citation_handle"]
                fenced = "```json\n" + json.dumps({"proposal_text": f"Include {handle}", "cited_handles": [handle]}) + "\n```"
                return reply(fenced)

            mock.post(GEMINI_URL).mock(side_effect=answer)
            body = ask(client, ws_id, group["id"]).json()
        assert body["model_error"] is None and body["proposal_text"].startswith("Include")

    def test_an_uncited_answer_is_not_trusted(self, client, db_session, ai_on):
        ws_id, group = first_group(client, db_session)
        with respx.mock() as mock:
            mock.post(GEMINI_URL).mock(return_value=reply({"proposal_text": "Include it, trust me.", "cited_handles": ["[PUBMED:0]"]}))
            body = ask(client, ws_id, group["id"]).json()
        assert body["citations"] == []
        assert "Abstaining" in body["proposal_text"]


class TestAdapterSettings:
    REQUEST = GatewayRequest(task_name="corpus_qa", model_alias="gemini-2.5-flash", prompt_context={"q": "hello"})

    def test_key_url_and_model_come_from_settings(self, ai_on):
        adapter = HTTPXModelAdapter(default_model=settings.llm_model_alias)
        assert adapter.api_key == KEY
        assert adapter.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
        assert adapter.is_enabled()
        with respx.mock(assert_all_called=True) as mock:
            mock.post(GEMINI_URL).mock(return_value=reply({"ok": True}))
            assert adapter.invoke(self.REQUEST).success

    def test_blank_ai_settings_mean_unset_not_empty(self, monkeypatch):
        """An empty LLM_BASE_URL= line copied from .env.example must not blank out the default endpoint."""
        from app.settings import Settings

        monkeypatch.setenv("LLM_BASE_URL", "")
        monkeypatch.setenv("LLM_MODEL_ALIAS", "  ")
        monkeypatch.setenv("LLM_API_KEY", "")
        loaded = Settings()
        assert loaded.llm_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
        assert loaded.llm_model_alias == "gemini-3.8-flash"
        assert loaded.llm_api_key is None

    def test_no_key_means_disabled(self, ai_on, monkeypatch):
        monkeypatch.setattr(settings, "llm_api_key", None)
        adapter = HTTPXModelAdapter(default_model="gemini-2.5-flash")
        assert adapter.is_enabled() is False
        assert adapter.invoke(self.REQUEST).error_code == GatewayErrorCode.DISABLED

    def test_the_mock_model_is_never_sent_to_a_real_endpoint(self, ai_on):
        adapter = HTTPXModelAdapter(default_model="mock-research-model")
        with respx.mock(assert_all_called=False) as mock:
            route = mock.post(GEMINI_URL)
            result = adapter.invoke(GatewayRequest(task_name="corpus_qa", model_alias="mock-research-model", prompt_context={"q": "x"}))
        assert result.success is False and result.error_code == GatewayErrorCode.UNAUTHORIZED_MODEL
        assert not route.called

    def test_an_unapproved_model_is_refused(self, ai_on):
        adapter = HTTPXModelAdapter(default_model="gemini-2.5-flash")
        result = adapter.invoke(GatewayRequest(task_name="corpus_qa", model_alias="some-other-model", prompt_context={"q": "x"}))
        assert result.error_code == GatewayErrorCode.UNAUTHORIZED_MODEL


class TestAiSynonymsThroughTheRoute:
    PICO: ClassVar[dict[str, str]] = {"population": "adults with type 2 diabetes", "intervention": "SGLT2 inhibitor"}

    def test_synonyms_are_added_and_marked_when_ai_is_on(self, client, ai_on):
        ws = client.post("/api/v1/workspaces", json={"title": "SGLT2i"}).json()
        with respx.mock() as mock:
            mock.post(GEMINI_URL).mock(return_value=reply({"synonyms": ["empagliflozin", "dapagliflozin"]}))
            body = client.post(f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json={"question": "q", "pico": self.PICO}).json()
        assert body["ai_synonyms_used"] is True
        intervention = next(c for c in body["criteria"] if c["id"] == "pico_intervention")
        assert intervention["ai_suggested_keywords"] == ["empagliflozin", "dapagliflozin"]
        assert intervention["keywords"][0] == "SGLT2 inhibitor"

    def test_a_failing_model_still_returns_the_rules_with_a_notice(self, client, ai_on):
        ws = client.post("/api/v1/workspaces", json={"title": "SGLT2i"}).json()
        with respx.mock() as mock:
            mock.post(GEMINI_URL).mock(return_value=httpx.Response(429, json={"error": {"message": "quota"}}))
            resp = client.post(f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json={"question": "q", "pico": self.PICO})
        body = resp.json()
        assert resp.status_code == 200
        assert body["ai_synonyms_used"] is False and body["notice"]
        assert [c["id"] for c in body["criteria"]][:2] == ["pico_population", "pico_intervention"]

    def test_with_ai_off_nothing_is_sent_and_the_result_is_deterministic(self, client, monkeypatch):
        monkeypatch.setattr(settings, "llm_enabled", False)
        monkeypatch.delenv("LLM_ENABLED", raising=False)
        ws = client.post("/api/v1/workspaces", json={"title": "SGLT2i"}).json()
        payload = {"question": "q", "pico": self.PICO}
        with respx.mock(assert_all_called=False) as mock:
            route = mock.post(GEMINI_URL)
            first = client.post(f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json=payload).json()
            second = client.post(f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json=payload).json()
        assert not route.called
        assert first == second and first["ai_synonyms_used"] is False and first["notice"] is None
