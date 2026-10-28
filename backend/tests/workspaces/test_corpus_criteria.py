"""process_corpus: per-workspace fallback criteria and an explicit criteria_version_id."""
import json

from fastapi.testclient import TestClient

from app.db.models import CriteriaVersionModel, CorpusRevisionModel
from app.services.corpus import process_corpus

PICO = {"population": "adults with asthma", "intervention": "inhaled corticosteroid"}


def test_fallback_criteria_are_topic_neutral_and_belong_to_each_workspace(client: TestClient, db_session):
    first = client.post("/api/v1/workspaces", json={"title": "Asthma review"}).json()
    second = client.post("/api/v1/workspaces", json={"title": "Stroke review"}).json()

    rev1 = process_corpus(db=db_session, workspace_id=first["id"])
    rev2 = process_corpus(db=db_session, workspace_id=second["id"])

    ids = {rev1.criteria_version_id, rev2.criteria_version_id}
    assert ids == {f"crit-default-{first['id']}", f"crit-default-{second['id']}"}
    row = db_session.get(CriteriaVersionModel, f"crit-default-{first['id']}")
    assert row.workspace_id == first["id"]
    assert row.question == "Asthma review"
    text = (row.criteria_json + row.pico_json).lower()
    assert "metformin" not in text and "diabet" not in text and "hba1c" not in text


def test_an_explicit_criteria_version_is_used_over_the_newest(client: TestClient, db_session):
    ws = client.post("/api/v1/workspaces", json={"title": "Asthma review"}).json()
    rules = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json={"question": "q", "pico": PICO}
    ).json()["criteria"]
    older = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria", json={"question": "old", "pico_description": PICO, "criteria": rules}
    ).json()
    client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria", json={"question": "new", "pico_description": PICO, "criteria": rules[:1]}
    )

    chosen = client.post(f"/api/v1/workspaces/{ws['id']}/process-corpus?criteria_version_id={older['id']}")
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["criteria_version_id"] == older["id"]

    default = client.post(f"/api/v1/workspaces/{ws['id']}/process-corpus")
    assert default.json()["criteria_version_id"] != older["id"]  # newest saved version

    stored = db_session.query(CorpusRevisionModel).filter_by(workspace_id=ws["id"]).count()
    assert stored >= 2


def test_a_criteria_version_from_another_workspace_is_refused(client: TestClient):
    a = client.post("/api/v1/workspaces", json={"title": "A"}).json()
    b = client.post("/api/v1/workspaces", json={"title": "B"}).json()
    rules = client.post(f"/api/v1/workspaces/{a['id']}/criteria/suggest", json={"question": "q", "pico": PICO}).json()["criteria"]
    crit = client.post(
        f"/api/v1/workspaces/{a['id']}/criteria",
        json={"question": "q", "pico_description": PICO, "criteria": rules},
    ).json()
    resp = client.post(f"/api/v1/workspaces/{b['id']}/process-corpus?criteria_version_id={crit['id']}")
    assert resp.status_code == 404
