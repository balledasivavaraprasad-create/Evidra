"""Evidence claims, radar and challenges are made when the corpus is processed; GETs only read them."""
from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    DevilsAdvocateChallengeModel,
    EvidencePassportModel,
    PicoAnnotationModel,
    ReviewEventModel,
)
from tests.pico.test_review_patterns import make_processed_review

WATCHED = (EvidencePassportModel, DevilsAdvocateChallengeModel, PicoAnnotationModel, ReviewEventModel)


def fingerprint(db: Session) -> dict[str, str]:
    """A hash of every watched table's rows (ids and every column), to notice any write at all."""
    db.expire_all()
    out = {}
    for model in WATCHED:
        cols = [c.name for c in model.__table__.columns]
        rows = sorted(tuple(str(getattr(r, c)) for c in cols) for r in db.query(model).all())
        out[model.__tablename__] = hashlib.sha256(repr(rows).encode()).hexdigest() + f":{len(rows)}"
    return out


def test_processing_prepares_the_evidence_and_the_gets_only_read_it(client: TestClient, db_session: Session):
    ws_id, revision_id = make_processed_review(client, db_session)

    # Made during processing, before anyone opened a page
    assert db_session.query(EvidencePassportModel).filter_by(workspace_id=ws_id).count() > 0

    groups = client.get(f"/api/v1/revisions/{revision_id}/groups").json()
    assert groups
    before = fingerprint(db_session)

    for g in groups:
        gid = g["id"]
        assert client.get(f"/api/v1/groups/{gid}").status_code == 200
        assert client.get(f"/api/v1/workspaces/{ws_id}/groups/{gid}/evidence").status_code == 200
        assert client.get(f"/api/v1/workspaces/{ws_id}/groups/{gid}/pico-radar").status_code == 200
        assert client.get(f"/api/v1/workspaces/{ws_id}/groups/{gid}/devils-advocate").status_code in (200, 404)
    for path in ("pico-radar", "devils-advocate", "evidence/summary"):
        assert client.get(f"/api/v1/workspaces/{ws_id}/{path}").status_code == 200

    assert fingerprint(db_session) == before, "a GET changed the database"


def test_a_read_before_processing_writes_nothing_and_still_answers(client: TestClient, db_session: Session):
    """A group with no prepared evidence (for example older data) is shown empty, not generated on read."""
    ws_id, revision_id = make_processed_review(client, db_session)
    gid = client.get(f"/api/v1/revisions/{revision_id}/groups").json()[0]["id"]
    db_session.query(EvidencePassportModel).delete()
    db_session.query(DevilsAdvocateChallengeModel).delete()
    db_session.commit()
    before = fingerprint(db_session)

    assert client.get(f"/api/v1/groups/{gid}").json()["evidence_bundle"]["items"] == []
    assert client.get(f"/api/v1/workspaces/{ws_id}/groups/{gid}/pico-radar").status_code == 200
    client.get(f"/api/v1/workspaces/{ws_id}/groups/{gid}/devils-advocate")

    assert fingerprint(db_session) == before


def test_asking_for_a_challenge_is_what_saves_one(client: TestClient, db_session: Session):
    ws_id, revision_id = make_processed_review(client, db_session)
    gid = client.get(f"/api/v1/revisions/{revision_id}/groups").json()[0]["id"]
    db_session.query(DevilsAdvocateChallengeModel).delete()
    db_session.commit()

    resp = client.post(f"/api/v1/workspaces/{ws_id}/groups/{gid}/devils-advocate/generate", json={"force_refresh": False})
    assert resp.status_code == 200, resp.text
    assert db_session.query(DevilsAdvocateChallengeModel).filter_by(group_id=gid).count() == 1
