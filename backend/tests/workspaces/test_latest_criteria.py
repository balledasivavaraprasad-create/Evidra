"""GET /criteria returns the newest saved version so the UI can resume without re-saving."""

from fastapi.testclient import TestClient

CRITERION = {
    "id": "crit_adults",
    "name": "Adult human participants",
    "category": "population",
    "is_inclusion": True,
    "rationale": "Adults only",
}


def _save(client: TestClient, workspace_id: str, question: str) -> dict:
    resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/criteria",
        json={
            "question": question,
            "pico_description": {"population": "adults", "intervention": "metformin"},
            "criteria": [CRITERION],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_returns_the_latest_saved_version(client: TestClient):
    ws = client.post("/api/v1/workspaces", json={"title": "Metformin"}).json()
    first = _save(client, ws["id"], "First question")
    second = _save(client, ws["id"], "Second question")

    resp = client.get(f"/api/v1/workspaces/{ws['id']}/criteria")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == second["id"] != first["id"]
    assert body["sequence"] == 2
    assert body["question"] == "Second question"
    assert body["pico_description"] == {"population": "adults", "intervention": "metformin"}
    assert body["criteria"] == [
        {
            **CRITERION,
            "metadata_first": True,
            "keywords": [],
            "exclude_keywords": [],
            "source": "custom",
            "ai_suggested_keywords": [],
        }
    ]


def test_404_when_nothing_saved_yet(client: TestClient):
    ws = client.post("/api/v1/workspaces", json={"title": "Empty"}).json()

    resp = client.get(f"/api/v1/workspaces/{ws['id']}/criteria")

    assert resp.status_code == 404


def test_404_for_unknown_workspace(client: TestClient):
    resp = client.get("/api/v1/workspaces/does-not-exist/criteria")

    assert resp.status_code == 404
