"""Workspaces created through the API must be listable, so the Workspaces page survives a reload."""

from fastapi.testclient import TestClient


def test_created_workspaces_are_listed_newest_first(client: TestClient):
    assert client.get("/api/v1/workspaces").json() == []

    first = client.post("/api/v1/workspaces", json={"title": "Statins and stroke"}).json()
    second = client.post(
        "/api/v1/workspaces", json={"title": "Metformin and HbA1c", "description": "Adults with T2D"}
    ).json()

    listed = client.get("/api/v1/workspaces")
    assert listed.status_code == 200
    ids = [ws["id"] for ws in listed.json()]
    assert set(ids) == {first["id"], second["id"]}
    assert listed.json()[0]["created_at"] >= listed.json()[1]["created_at"]
    assert {ws["title"] for ws in listed.json()} == {"Statins and stroke", "Metformin and HbA1c"}


def _saved_query(client: TestClient, title: str) -> str:
    ws = client.post("/api/v1/workspaces", json={"title": title}).json()
    crit = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria",
        json={
            "question": title,
            "pico_description": {"population": "adults", "intervention": "metformin"},
            "criteria": [
                {
                    "id": "crit_adults",
                    "name": "Adult human participants",
                    "category": "population",
                    "is_inclusion": True,
                    "rationale": "Adults only",
                }
            ],
        },
    )
    assert crit.status_code == 201, crit.text
    q = client.post(
        f"/api/v1/workspaces/{ws['id']}/queries",
        json={
            "ast": {"operator": "AND", "children": [{"term": "metformin"}]},
            "sources": ["pubmed"],
            "criteria_version_id": crit.json()["id"],
        },
    )
    assert q.status_code in (200, 201), q.text
    return q.json()["id"]


def test_counting_the_same_search_twice_or_in_two_reviews_does_not_fail(client: TestClient):
    first = _saved_query(client, "Review one")
    second = _saved_query(client, "Review two")

    a1 = client.post(f"/api/v1/queries/{first}/searches", json={"source": "pubmed", "synonym_expansion": False, "cap": 50})
    a2 = client.post(f"/api/v1/queries/{first}/searches", json={"source": "pubmed", "synonym_expansion": False, "cap": 50})
    b1 = client.post(f"/api/v1/queries/{second}/searches", json={"source": "pubmed", "synonym_expansion": False, "cap": 50})

    assert a1.status_code == a2.status_code == b1.status_code == 202, (a1.text, a2.text, b1.text)
    assert a1.json()["id"] == a2.json()["id"]
    assert a1.json()["id"] != b1.json()["id"]
