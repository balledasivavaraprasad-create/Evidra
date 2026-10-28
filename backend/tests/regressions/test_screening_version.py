"""Regression tests for consecutive screening decisions and optimistic locking.

Invariant:
- Two decisions in a row on the same group, each using the row_version returned
  in between, both succeed.
- A stale expected_version returns HTTP 409 STALE_VERSION_CONFLICT.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import EligibilityStatus
from app.contracts.models import DecisionCommand
from app.db.models import PaperGroupModel
from app.demo_data import seed_synthetic_slr_workspace
from app.services.review_decisions import record_screening_decision


def test_two_consecutive_decisions_succeed_with_updated_version(db_session: Session):
    ws_id = seed_synthetic_slr_workspace(db_session)
    group = db_session.query(PaperGroupModel).filter_by(workspace_id=ws_id).first()
    assert group is not None, "Workspace must contain seeded paper groups"

    v1 = group.row_version

    # First decision: INCLUDE with v1
    cmd1 = DecisionCommand(
        status=EligibilityStatus.INCLUDE,
        reason="Meets clinical population and outcome criteria",
        expected_version=v1,
    )
    res1 = record_screening_decision(db_session, group.id, cmd1, actor_id="reviewer-1")
    assert res1.sequence >= 1
    assert group.row_version == v1 + 1

    # Second decision: EXCLUDE with v2
    v2 = group.row_version
    cmd2 = DecisionCommand(
        status=EligibilityStatus.EXCLUDE,
        reason="Preclinical model without human clinical trial endpoints",
        expected_version=v2,
    )
    res2 = record_screening_decision(db_session, group.id, cmd2, actor_id="reviewer-1")
    assert res2.sequence > res1.sequence
    assert group.row_version == v2 + 1


def test_stale_expected_version_raises_409(db_session: Session):
    ws_id = seed_synthetic_slr_workspace(db_session)
    group = db_session.query(PaperGroupModel).filter_by(workspace_id=ws_id).first()
    assert group is not None

    v1 = group.row_version

    # First decision advances row_version to v1 + 1
    cmd1 = DecisionCommand(
        status=EligibilityStatus.INCLUDE,
        reason="Initial inclusion",
        expected_version=v1,
    )
    record_screening_decision(db_session, group.id, cmd1, actor_id="reviewer-1")
    assert group.row_version == v1 + 1

    # Stale decision: using v1 again must raise HTTP 409
    cmd_stale = DecisionCommand(
        status=EligibilityStatus.EXCLUDE,
        reason="Out of scope",
        expected_version=v1,
    )
    with pytest.raises(HTTPException) as exc_info:
        record_screening_decision(db_session, group.id, cmd_stale, actor_id="reviewer-2")

    assert exc_info.value.status_code == 409
    assert "STALE_VERSION_CONFLICT" in str(exc_info.value.detail)


def test_consecutive_decisions_via_api_endpoints(client: TestClient, db_session: Session):
    ws_id = seed_synthetic_slr_workspace(db_session)
    group = db_session.query(PaperGroupModel).filter_by(workspace_id=ws_id).first()
    assert group is not None

    # 1. Fetch group detail via API
    get_res = client.get(f"/api/v1/groups/{group.id}")
    assert get_res.status_code == 200
    group_data = get_res.json()["group"]
    v1 = group_data["row_version"]

    # 2. First decision via POST
    post_res1 = client.post(
        f"/api/v1/groups/{group.id}/decisions",
        json={
            "status": "include",
            "reason": "Meets study protocol",
            "expected_version": v1,
        },
    )
    assert post_res1.status_code == 200

    # 3. Refetch group detail via API -> row_version must have incremented
    get_res2 = client.get(f"/api/v1/groups/{group.id}")
    assert get_res2.status_code == 200
    group_data2 = get_res2.json()["group"]
    v2 = group_data2["row_version"]
    assert v2 == v1 + 1

    # 4. Second decision using new row_version v2 succeeds
    post_res2 = client.post(
        f"/api/v1/groups/{group.id}/decisions",
        json={
            "status": "exclude",
            "reason": "Wrong comparator used in study",
            "expected_version": v2,
        },
    )
    assert post_res2.status_code == 200

    # 5. Third decision with stale version v1 returns 409
    post_stale = client.post(
        f"/api/v1/groups/{group.id}/decisions",
        json={
            "status": "include",
            "reason": "Attempting stale write",
            "expected_version": v1,
        },
    )
    assert post_stale.status_code == 409
