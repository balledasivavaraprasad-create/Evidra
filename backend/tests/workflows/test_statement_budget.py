"""How many database statements processing issues per paper.

Every statement is a network round trip to a hosted database (about 280 ms from a far-away laptop),
so the number of statements, not CPU, is what makes processing slow. This pins it so it can't grow
unnoticed. Phase 3 should lower these budgets.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.worker import poll_and_execute_next
from tests.workflows.test_async_processing import count_and_queue_import, make_review


class Counter:
    def __init__(self, engine):
        self.n = 0
        self._engine = engine

    def __enter__(self):
        event.listen(self._engine, "before_cursor_execute", self._hit)
        return self

    def __exit__(self, *exc):
        event.remove(self._engine, "before_cursor_execute", self._hit)

    def _hit(self, *args):
        self.n += 1


def test_statements_per_paper(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys):
    import app.services.derived as derived

    ws_id, crit_id = make_review(client)
    count_and_queue_import(client, ws_id, crit_id)
    engine = db_session.get_bind()

    prepared = {"statements": 0}
    real = derived.precompute_review_artifacts

    def counted(*args, **kwargs):
        with Counter(engine) as part:
            try:
                return real(*args, **kwargs)
            finally:
                prepared["statements"] = part.n

    monkeypatch.setattr(derived, "precompute_review_artifacts", counted)

    with Counter(engine) as import_run:
        poll_and_execute_next(db=db_session)  # the import (and it queues processing)
    with Counter(engine) as processing_run:
        poll_and_execute_next(db=db_session)

    revision_id = client.get(f"/api/v1/workspaces/{ws_id}/revisions").json()[0]["id"]
    papers = len(client.get(f"/api/v1/revisions/{revision_id}/groups").json())
    pipeline = processing_run.n - prepared["statements"]
    with capsys.disabled():
        print(
            f"\n[statement budget] {papers} papers: import {import_run.n} ({import_run.n / papers:.0f}/paper); "
            f"processing {processing_run.n} = pipeline {pipeline} ({pipeline / papers:.0f}/paper) "
            f"+ evidence prepared {prepared['statements']} ({prepared['statements'] / papers:.0f}/paper)"
        )
    # Generous ceilings: they exist to notice growth, and Phase 3 should bring them down
    assert import_run.n / papers < 40
    assert processing_run.n / papers < 200
