"""Imports flow straight into screening: the corpus is processed by a job, not a blocking request."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import JobModel
from app.worker import poll_and_execute_next

PICO = {"population": "adults with type 2 diabetes", "intervention": "metformin"}


def make_review(client: TestClient) -> tuple[str, str]:
    ws = client.post("/api/v1/workspaces", json={"title": "Metformin review"}).json()
    rules = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria/suggest", json={"question": "q", "pico": PICO}
    ).json()["criteria"]
    crit = client.post(
        f"/api/v1/workspaces/{ws['id']}/criteria",
        json={"question": "Metformin in T2D", "pico_description": PICO, "criteria": rules},
    ).json()
    return ws["id"], crit["id"]


def count_and_queue_import(client: TestClient, ws_id: str, crit_id: str) -> str:
    q = client.post(
        f"/api/v1/workspaces/{ws_id}/queries",
        json={
            "ast": {"operator": "AND", "children": [{"term": "metformin"}, {"term": "type 2 diabetes"}]},
            "sources": ["pubmed"],
            "criteria_version_id": crit_id,
        },
    ).json()
    execution = client.post(
        f"/api/v1/queries/{q['id']}/searches", json={"source": "pubmed", "synonym_expansion": False, "cap": 50}
    ).json()
    imp = client.post(
        f"/api/v1/workspaces/{ws_id}/imports",
        json={"search_execution_ids": [execution["id"]], "cap": 20, "idempotency_key": "async-test-1"},
    )
    assert imp.status_code == 202, imp.text
    return imp.json()["id"]


def screen_jobs(client: TestClient, ws_id: str) -> list[dict]:
    return client.get(f"/api/v1/workspaces/{ws_id}/jobs?kind=screen&limit=10").json()


class TestProcessCorpusRoute:
    def test_returns_a_queued_job_to_poll_instead_of_blocking(self, client: TestClient):
        ws_id, _ = make_review(client)
        resp = client.post(f"/api/v1/workspaces/{ws_id}/process-corpus")
        assert resp.status_code == 202, resp.text
        job = resp.json()
        assert job["kind"] == "screen" and job["state"] == "queued" and job["stage"] == "queued"
        assert client.get(f"/api/v1/jobs/{job['id']}").json()["id"] == job["id"]

    def test_a_second_click_reuses_the_queued_job(self, client: TestClient):
        ws_id, _ = make_review(client)
        first = client.post(f"/api/v1/workspaces/{ws_id}/process-corpus").json()
        second = client.post(f"/api/v1/workspaces/{ws_id}/process-corpus").json()
        assert second["id"] == first["id"]
        assert len(screen_jobs(client, ws_id)) == 1

    def test_unknown_workspace_and_foreign_criteria_are_404(self, client: TestClient):
        assert client.post("/api/v1/workspaces/nope/process-corpus").status_code == 404
        ws_id, _ = make_review(client)
        assert client.post(f"/api/v1/workspaces/{ws_id}/process-corpus?criteria_version_id=nope").status_code == 404


class TestImportQueuesProcessing:
    def test_a_finished_import_queues_processing_by_itself_and_the_stages_read_in_order(
        self, client: TestClient, db_session: Session
    ):
        ws_id, crit_id = make_review(client)
        import_id = count_and_queue_import(client, ws_id, crit_id)
        assert screen_jobs(client, ws_id) == []  # nothing yet: the import has not run

        assert poll_and_execute_next(db=db_session)  # runs the import
        imported = client.get(f"/api/v1/jobs/{import_id}").json()
        assert imported["state"] == "succeeded" and imported["stage"] == "done"
        assert imported["processed_items"] > 0

        queued = screen_jobs(client, ws_id)
        assert len(queued) == 1, "processing must be queued as soon as the import succeeds"
        assert queued[0]["state"] == "queued" and queued[0]["stage"] == "queued"
        assert queued[0]["created_at"] <= imported["updated_at"]

        assert poll_and_execute_next(db=db_session)  # runs the processing
        done = client.get(f"/api/v1/jobs/{queued[0]['id']}").json()
        # waiting_human means processed, with uncertain papers left for the reviewer to confirm
        assert done["state"] in ("succeeded", "waiting_human")
        assert done["stage"] in ("done", "waiting_human_review")

    def test_the_processed_papers_are_there_afterwards(self, client: TestClient, db_session: Session):
        ws_id, crit_id = make_review(client)
        count_and_queue_import(client, ws_id, crit_id)
        poll_and_execute_next(db=db_session)
        poll_and_execute_next(db=db_session)

        revisions = client.get(f"/api/v1/workspaces/{ws_id}/revisions").json()
        assert revisions, "processing should publish a corpus revision"
        groups = client.get(f"/api/v1/revisions/{revisions[0]['id']}/groups").json()
        assert len(groups) > 0
        assert revisions[0]["criteria_version_id"] == crit_id

    def test_a_click_while_processing_is_queued_does_not_stack_jobs(self, client: TestClient, db_session: Session):
        ws_id, crit_id = make_review(client)
        count_and_queue_import(client, ws_id, crit_id)
        poll_and_execute_next(db=db_session)
        before = db_session.query(JobModel).filter_by(workspace_id=ws_id, kind="screen").count()
        client.post(f"/api/v1/workspaces/{ws_id}/process-corpus")
        assert db_session.query(JobModel).filter_by(workspace_id=ws_id, kind="screen").count() == before
