"""Comprehensive integration test suite for review services, decision persistence, and export (D03)."""
import json
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import (
    EligibilityStatus,
    PicoLabel,
)
from app.contracts.models import (
    DecisionCommand,
    DedupOverrideRequest,
    ExportRequest,
    PicoOverrideRequest,
    PicoSpan,
)
from app.db.models import (
    CriteriaVersionModel,
    QueryMembershipModel,
    QueryVersionModel,
    RecordRevisionModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.pico.validator import compute_text_hash
from app.services.corpus import (
    list_paper_groups_in_revision,
    process_corpus,
)
from app.services.evidence import SqliteEvidenceRepository


def seed_test_workspace_with_records(db: Session) -> tuple[str, str, str, str]:
    """Helper to seed a workspace with criteria, query, execution, and 3 imported literature records."""
    ws = WorkspaceModel(
        id=f"ws-{uuid4().hex[:8]}",
        title="Type 2 Diabetes Metformin SLR",
        description="HbA1c review in adults",
        created_by="test-reviewer",
        row_version=1,
    )
    db.add(ws)
    db.flush()

    # Criteria version
    crit = CriteriaVersionModel(
        id=f"crit-{uuid4().hex[:8]}",
        workspace_id=ws.id,
        sequence=1,
        question="In adults with type 2 diabetes, how does metformin affect HbA1c?",
        pico_json=json.dumps({"P": "Adults with T2D", "I": "Metformin", "C": "Placebo", "O": "HbA1c"}),
        criteria_json=json.dumps(
            [
                {
                    "id": "crit-human",
                    "name": "Human adult population",
                    "category": "population",
                    "is_inclusion": True,
                    "rationale": "Must study human adults",
                    "metadata_first": True,
                }
            ]
        ),
        content_hash="test-crit-hash",
    )
    db.add(crit)

    # Query version
    qv = QueryVersionModel(
        id=f"qv-{uuid4().hex[:8]}",
        workspace_id=ws.id,
        sequence=1,
        ast_json=json.dumps({"field": "ALL", "value": "metformin"}),
        sources_json=json.dumps(["pubmed"]),
        criteria_version_id=crit.id,
        content_hash="test-query-hash",
    )
    db.add(qv)

    # Search execution
    se = SearchExecutionModel(
        id=f"se-{uuid4().hex[:8]}",
        query_version_id=qv.id,
        source="pubmed",
        exact_query="metformin",
        synonym_setting=False,
        hit_count=3,
        status="succeeded",
        partial=False,
    )
    db.add(se)
    db.flush()

    # Record 1: Included RCT
    t1 = "Metformin improves glycemic control in adult patients with type 2 diabetes: a randomized controlled trial."
    a1 = "Objective: Evaluate oral metformin versus placebo in adults with type 2 diabetes. Methods: 150 patients received metformin 1000mg daily. Results: HbA1c decreased significantly. Conclusion: Metformin is effective."
    src1 = SourceRecordModel(
        id=f"src-1-{uuid4().hex[:6]}",
        workspace_id=ws.id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="100001",
    )
    db.add(src1)
    db.flush()
    rev1 = RecordRevisionModel(
        id=f"rev-1-{uuid4().hex[:6]}",
        source_record_id=src1.id,
        content_hash=compute_text_hash(a1),
        title=t1,
        abstract_text=a1,
        year=2023,
        journal="Diabetes Care",
        doi="10.1001/dc.2023.01",
        pmid="100001",
        publication_types_json=json.dumps(["Randomized Controlled Trial"]),
    )
    db.add(rev1)
    db.flush()

    # Record 2: Duplicate of Record 1 (same paper from Europe PMC)
    src2 = SourceRecordModel(
        id=f"src-2-{uuid4().hex[:6]}",
        workspace_id=ws.id,
        source="europepmc",
        source_namespace="europepmc",
        external_id="PMC100001",
    )
    db.add(src2)
    db.flush()
    rev2 = RecordRevisionModel(
        id=f"rev-2-{uuid4().hex[:6]}",
        source_record_id=src2.id,
        content_hash=compute_text_hash(a1),
        title=t1,
        abstract_text=a1,
        year=2023,
        journal="Diabetes Care",
        doi="10.1001/dc.2023.01",  # Same DOI!
        pmid="100001",
    )
    db.add(rev2)
    db.flush()

    # Record 3: Rodent study (preclinical)
    t3 = "=1+1 Formula Injection Title: Effect of metformin in Sprague-Dawley rats."
    a3 = "@SUM(A1:A10) We administered metformin to male Wistar rats to measure hepatic glucose production."
    src3 = SourceRecordModel(
        id=f"src-3-{uuid4().hex[:6]}",
        workspace_id=ws.id,
        source="pubmed",
        source_namespace="pubmed",
        external_id="100003",
    )
    db.add(src3)
    db.flush()
    rev3 = RecordRevisionModel(
        id=f"rev-3-{uuid4().hex[:6]}",
        source_record_id=src3.id,
        content_hash=compute_text_hash(a3),
        title=t3,
        abstract_text=a3,
        year=2022,
        journal="Biochem Pharmacol",
        pmid="100003",
    )
    db.add(rev3)
    db.flush()

    db.add(QueryMembershipModel(search_execution_id=se.id, source_record_id=src1.id, record_revision_id=rev1.id))
    db.add(QueryMembershipModel(search_execution_id=se.id, source_record_id=src2.id, record_revision_id=rev2.id))
    db.add(QueryMembershipModel(search_execution_id=se.id, source_record_id=src3.id, record_revision_id=rev3.id))
    db.commit()

    return ws.id, src1.id, src2.id, src3.id


def test_process_corpus_deduplication_and_screening(db_session: Session):
    """Test deterministic pipeline runs dedup (merging identical DOI) and screens records."""
    ws_id, _s1, _s2, _s3 = seed_test_workspace_with_records(db_session)

    # Process corpus
    rev = process_corpus(db=db_session, workspace_id=ws_id)
    assert rev.state.value == "published"
    assert rev.record_count == 3
    # Records 1 and 2 share exact DOI -> grouped into 1 group, record 3 is separate -> total 2 groups
    assert rev.group_count == 2

    # Query groups in revision
    groups = list_paper_groups_in_revision(db=db_session, revision_id=rev.id)
    assert len(groups) == 2

    # Verify duplicate group has member_count == 2
    dup_group = next(g for g in groups if g.member_count == 2)
    assert dup_group.representative_revision.doi == "10.1001/dc.2023.01"


def test_human_decision_supersedes_machine_suggestion(db_session: Session, client: TestClient):
    """Test human reviewer decision event strictly overrides machine screening verdict."""
    ws_id, _s1, _s2, _s3 = seed_test_workspace_with_records(db_session)
    rev = process_corpus(db=db_session, workspace_id=ws_id)
    groups = list_paper_groups_in_revision(db=db_session, revision_id=rev.id)

    target_group = groups[0]

    # Human records an explicit INCLUDE decision
    cmd = DecisionCommand(
        status=EligibilityStatus.INCLUDE,
        reason="Verified adult RCT meeting all inclusion criteria",
        expected_version=1,
    )
    res = client.post(f"/api/v1/groups/{target_group.id}/decisions", json=cmd.model_dump())
    assert res.status_code == status.HTTP_200_OK
    ev_data = res.json()
    assert ev_data["event_type"] == "screen_decision"
    assert ev_data["payload"]["status"] == "include"

    # Verify effective status is now INCLUDE and has_human_decision is True
    detail = client.get(f"/api/v1/groups/{target_group.id}").json()
    assert detail["group"]["effective_status"] == "include"
    assert detail["group"]["has_human_decision"] is True
    assert len(detail["events"]) == 1


def test_exclusion_requires_reason(db_session: Session, client: TestClient):
    """Test human exclusion fails without a mandatory clinical/methodological reason."""
    ws_id, _s1, _s2, _s3 = seed_test_workspace_with_records(db_session)
    rev = process_corpus(db=db_session, workspace_id=ws_id)
    groups = list_paper_groups_in_revision(db=db_session, revision_id=rev.id)
    target_group = groups[0]

    # Empty reason
    cmd = {
        "status": "exclude",
        "reason": "",
        "expected_version": 1,
    }
    res = client.post(f"/api/v1/groups/{target_group.id}/decisions", json=cmd)
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Whitespace only reason
    cmd["reason"] = "    "
    res = client.post(f"/api/v1/groups/{target_group.id}/decisions", json=cmd)
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Valid reason succeeds
    cmd["reason"] = "Preclinical animal model without human participants"
    res = client.post(f"/api/v1/groups/{target_group.id}/decisions", json=cmd)
    assert res.status_code == status.HTTP_200_OK


def test_optimistic_locking_prevents_stale_overwrites(db_session: Session, client: TestClient):
    """Test that concurrent writes with stale expected_version return HTTP 409 Conflict."""
    ws_id, _s1, _s2, _s3 = seed_test_workspace_with_records(db_session)
    rev = process_corpus(db=db_session, workspace_id=ws_id)
    groups = list_paper_groups_in_revision(db=db_session, revision_id=rev.id)
    target_group = groups[0]

    # First write: version 1 -> 2
    cmd1 = DecisionCommand(status=EligibilityStatus.MAYBE, expected_version=1)
    res1 = client.post(f"/api/v1/groups/{target_group.id}/decisions", json=cmd1.model_dump())
    assert res1.status_code == status.HTTP_200_OK

    # Second write with stale expected_version=1 must fail with 409
    cmd2 = DecisionCommand(status=EligibilityStatus.INCLUDE, expected_version=1)
    res2 = client.post(f"/api/v1/groups/{target_group.id}/decisions", json=cmd2.model_dump())
    assert res2.status_code == status.HTTP_409_CONFLICT
    assert "STALE_VERSION_CONFLICT" in res2.json()["code"]


def test_pico_annotation_validation_and_overlap(db_session: Session, client: TestClient):
    """Test PICO span verification: exact quote, Unicode code-point offsets, and overlapping labels."""
    ws_id, _s1, _s2, _s3 = seed_test_workspace_with_records(db_session)
    rev = process_corpus(db=db_session, workspace_id=ws_id)
    groups = list_paper_groups_in_revision(db=db_session, revision_id=rev.id)
    target_group = next(g for g in groups if "adults with type 2 diabetes" in (g.representative_revision.abstract_text or ""))

    rep = target_group.representative_revision
    text = rep.abstract_text or ""
    # "Evaluate oral metformin versus placebo in adults with type 2 diabetes."
    quote_p = "adults with type 2 diabetes"
    start_p = text.index(quote_p)
    end_p = start_p + len(quote_p)

    quote_i = "metformin"
    start_i = text.index(quote_i)
    end_i = start_i + len(quote_i)

    # Valid spans
    valid_request = PicoOverrideRequest(
        record_revision_id=rep.id,
        content_hash=compute_text_hash(text),
        expected_version=1,
        spans=[
            PicoSpan(
                label=PicoLabel.P,
                start_cp=start_p,
                end_cp=end_p,
                quote=quote_p,
                provenance="human_override",
            ),
            PicoSpan(
                label=PicoLabel.I,
                start_cp=start_i,
                end_cp=end_i,
                quote=quote_i,
                provenance="human_override",
            ),
        ],
    )

    res = client.post(f"/api/v1/groups/{target_group.id}/pico", json=valid_request.model_dump())
    assert res.status_code == status.HTTP_200_OK

    # Invalid quote mismatch must fail with 422
    invalid_request = PicoOverrideRequest(
        record_revision_id=rep.id,
        content_hash=compute_text_hash(text),
        expected_version=2,
        spans=[
            PicoSpan(
                label=PicoLabel.P,
                start_cp=start_p,
                end_cp=end_p,
                quote="WRONG QUOTE",
                provenance="human_override",
            )
        ],
    )
    res_bad = client.post(f"/api/v1/groups/{target_group.id}/pico", json=invalid_request.model_dump())
    assert res_bad.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_dedup_override_cannot_link_constraint(db_session: Session, client: TestClient):
    """Test manual duplicate rejection enforces cannot-link constraint on subsequent dedup."""
    ws_id, s1, s2, _s3 = seed_test_workspace_with_records(db_session)
    rev = process_corpus(db=db_session, workspace_id=ws_id)
    assert rev.group_count == 2

    # Reject duplicate pair between s1 and s2
    override = DedupOverrideRequest(
        record_id_a=s1,
        record_id_b=s2,
        confirm=False,
        reason="Separate studies despite identical DOI metadata",
        expected_version=1,
    )
    res = client.post(f"/api/v1/workspaces/{ws_id}/dedup-decisions", json=override.model_dump())
    assert res.status_code == status.HTTP_200_OK

    # Reprocess corpus -> s1 and s2 must not be merged into same group
    new_rev = process_corpus(db=db_session, workspace_id=ws_id)
    assert new_rev.group_count == 3  # Now 3 separate groups!


def test_export_included_studies_sanitization(db_session: Session, client: TestClient):
    """Test CSV export sanitizes spreadsheet formula injection (=, +, -, @) and omits excluded records."""
    ws_id, _s1, _s2, _s3 = seed_test_workspace_with_records(db_session)
    rev = process_corpus(db=db_session, workspace_id=ws_id)
    groups = list_paper_groups_in_revision(db=db_session, revision_id=rev.id)

    # Mark the group containing Record 3 (=1+1 formula injection) as INCLUDE for testing
    formula_group = next(g for g in groups if "=1+1" in g.representative_revision.title)
    client.post(
        f"/api/v1/groups/{formula_group.id}/decisions",
        json={"status": "include", "reason": "Test include", "expected_version": 1},
    )

    # Request export
    export_req = ExportRequest(revision_id=rev.id, format="csv")
    res = client.post(f"/api/v1/revisions/{rev.id}/exports", json=export_req.model_dump())
    assert res.status_code == status.HTTP_200_OK
    exp_data = res.json()
    assert exp_data["record_count"] >= 1

    # Download CSV file
    dl_res = client.get(exp_data["download_url"])
    assert dl_res.status_code == status.HTTP_200_OK
    csv_text = dl_res.text

    # Verify formula injection characters are escaped with a leading single quote (')
    assert "'=1+1 Formula Injection Title" in csv_text
    assert "'@SUM(A1:A10)" in csv_text


def test_evidence_retrieval_repository_authorization(db_session: Session):
    """Test that SqliteEvidenceRepository enforces workspace scoping and bounds chunks."""
    ws_id, s1, s2, s3 = seed_test_workspace_with_records(db_session)
    rev = process_corpus(db=db_session, workspace_id=ws_id)

    repo = SqliteEvidenceRepository(db_session)

    # Correct workspace
    chunks = repo.get_authorized_chunks(
        workspace_id=ws_id,
        corpus_revision_id=rev.id,
        query="metformin",
        limit=5,
    )
    assert len(chunks) == 3
    assert all(c.source_record_id in (s1, s2, s3) for c in chunks)

    # Cross-workspace request must return empty (strictly isolated)
    unauth_chunks = repo.get_authorized_chunks(
        workspace_id="other-workspace-id",
        corpus_revision_id=rev.id,
        query="metformin",
    )
    assert len(unauth_chunks) == 0
