"""After a reload the UI rebuilds the Query page and dashboard purely from these endpoints."""
from fastapi.testclient import TestClient

AST = {
    "operator": "AND",
    "children": [
        {"operator": "OR", "children": [{"term": "SGLT2 inhibitor"}, {"term": "empagliflozin"}]},
        {"operator": "OR", "children": [{"term": "type 2 diabetes"}]},
        {"operator": "OR", "children": [{"term": "heart failure hospitalization"}]},
    ],
}


def _review_with_query(client: TestClient) -> tuple[str, dict]:
    ws = client.post("/api/v1/workspaces", json={"title": "SGLT2i and HF hospitalization in T2D"}).json()
    crit = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria",
        json={
            "question": "In adults with T2D, do SGLT2 inhibitors reduce HF hospitalization?",
            "pico_description": {"population": "adults with type 2 diabetes"},
            "criteria": [
                {
                    "id": "crit_population",
                    "name": "Adults with type 2 diabetes",
                    "category": "population",
                    "is_inclusion": True,
                    "rationale": "Population",
                }
            ],
        },
    ).json()
    query = client.post(
        f"/api/v1/workspaces/{ws['id']}/queries",
        json={
            "ast": AST,
            "start_date": "2015",
            "end_date": "2025",
            "sources": ["pubmed", "europepmc"],
            "criteria_version_id": crit["id"],
        },
    )
    assert query.status_code == 201, query.text
    return ws["id"], query.json()


def test_latest_query_version_is_restorable(client: TestClient):
    ws_id, saved = _review_with_query(client)
    res = client.get(f"/api/v1/workspaces/{ws_id}/queries/latest")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == saved["id"]
    assert body["ast"] == saved["ast"]
    assert body["start_date"] == "2015"


def test_latest_query_404_when_none(client: TestClient):
    ws = client.post("/api/v1/workspaces", json={"title": "Empty"}).json()
    assert client.get(f"/api/v1/workspaces/{ws['id']}/queries/latest").status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws['id']}/executions").json() == []


def test_executions_and_import_ticks_survive_reload(client: TestClient):
    ws_id, saved = _review_with_query(client)
    pub = client.post(f"/api/v1/queries/{saved['id']}/searches", json={"source": "pubmed"}).json()
    epmc = client.post(f"/api/v1/queries/{saved['id']}/searches", json={"source": "europepmc"}).json()

    listed = client.get(f"/api/v1/workspaces/{ws_id}/executions").json()
    assert {e["id"] for e in listed} == {pub["id"], epmc["id"]}
    assert all(e["selected_for_import"] for e in listed)

    # Untick only the PubMed row: the other row must stay ticked
    res = client.patch(f"/api/v1/executions/{pub['id']}", json={"selected_for_import": False})
    assert res.status_code == 200
    after = {e["id"]: e["selected_for_import"] for e in client.get(f"/api/v1/workspaces/{ws_id}/executions").json()}
    assert after == {pub["id"]: False, epmc["id"]: True}


def test_recent_jobs_listed_for_resume(client: TestClient):
    ws_id, saved = _review_with_query(client)
    pub = client.post(f"/api/v1/queries/{saved['id']}/searches", json={"source": "pubmed"}).json()
    job = client.post(
        f"/api/v1/workspaces/{ws_id}/imports",
        json={"search_execution_ids": [pub["id"]], "cap": 20, "idempotency_key": "resume-1"},
    ).json()

    jobs = client.get(f"/api/v1/workspaces/{ws_id}/jobs", params={"kind": "import_records", "limit": 1}).json()
    assert [j["id"] for j in jobs] == [job["id"]]


def test_dashboard_lists_reviews_with_question(client: TestClient):
    ws_id, _ = _review_with_query(client)
    cards = client.get("/api/v1/dashboard").json()
    card = next(c for c in cards if c["id"] == ws_id)
    assert card["title"] == "SGLT2i and HF hospitalization in T2D"
    assert card["question"].startswith("In adults with T2D")
    assert card["group_count"] == 0 and card["awaiting_review"] == 0
