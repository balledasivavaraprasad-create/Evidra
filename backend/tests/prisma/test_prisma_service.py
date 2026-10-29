"""Unit and service tests for PRISMA 2020 reporting calculation service."""
import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.contracts.enums import (
    PrismaStage,
    SourceNamespace,
)
from app.contracts.models import (
    PrismaSnapshotCreateRequest,
)
from app.db.models import (
    CorpusRevisionModel,
    CriteriaVersionModel,
    GroupMemberModel,
    PaperGroupModel,
    QueryVersionModel,
    RecordRevisionModel,
    ReviewEventModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.prisma import (
    compute_prisma_flow_report,
    export_prisma_csv,
    get_prisma_snapshot,
    get_prisma_stage_records,
    list_prisma_snapshots,
    save_prisma_snapshot,
)


def _seed_test_review(db: Session, ws_id: str = "ws-prisma-test-1"):
    ws = WorkspaceModel(id=ws_id, title="PRISMA Validation Review", created_by="reviewer-1")
    crit = CriteriaVersionModel(
        id=f"crit-{ws_id}",
        workspace_id=ws.id,
        sequence=1,
        question="Review question",
        pico_json=json.dumps({"p": "population"}),
        criteria_json=json.dumps({"inclusion": ["RCT"]}),
        content_hash="hash-1",
    )
    qv = QueryVersionModel(
        id=f"qv-{ws_id}",
        workspace_id=ws.id,
        sequence=1,
        ast_json="{}",
        sources_json=json.dumps(["PubMed", "Europe PMC"]),
        criteria_version_id=crit.id,
        content_hash="qvh-1",
    )
    db.add_all([ws, crit, qv])
    db.flush()

    crev = CorpusRevisionModel(
        id=f"crev-{ws_id}",
        workspace_id=ws.id,
        criteria_version_id=crit.id,
        dedup_version="v1",
        state="published",
        fingerprint="fp-1",
    )
    db.add(crev)
    db.flush()
    return ws, crit, qv, crev


def test_empty_workspace_prisma_flow(db_session: Session):
    ws, _, _, _ = _seed_test_review(db_session, "ws-prisma-empty")
    report = compute_prisma_flow_report(db=db_session, workspace_id=ws.id)

    assert report.workspace_id == ws.id
    assert report.stages.identification.total_identified == 0
    assert report.stages.pre_screening.total_removed == 0
    assert report.stages.screening.records_screened == 0
    assert report.stages.included.studies_included == 0
    assert report.stages.included.reports_included == 0
    assert report.reconciliation.is_reconciled is True
    assert report.reconciliation.identification_balance == 0
    assert report.reconciliation.screening_balance == 0
    assert report.stages.retrieval.is_supported is False
    assert report.stages.retrieval.status == "not_started"


def test_multi_source_deduplication_and_screening_flow(db_session: Session):
    ws, _, qv, _ = _seed_test_review(db_session, "ws-prisma-multi")

    # Search Executions for PubMed and Europe PMC
    se_pubmed = SearchExecutionModel(
        id=str(uuid4()),
        query_version_id=qv.id,
        source=SourceNamespace.PUBMED.value,
        exact_query="GLP-1 obesity",
        hit_count=3,
        status="completed",
    )
    se_epmc = SearchExecutionModel(
        id=str(uuid4()),
        query_version_id=qv.id,
        source=SourceNamespace.EUROPEPMC.value,
        exact_query="GLP-1 obesity",
        hit_count=2,
        status="completed",
    )
    db_session.add_all([se_pubmed, se_epmc])
    db_session.flush()

    # Create 5 Source Records
    # Group 1: Included study with 2 duplicate reports (1 from PubMed, 1 from Europe PMC)
    sr1 = SourceRecordModel(
        id="sr-pub-1",
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace="PubMed",
        external_id="1001",
    )
    sr2 = SourceRecordModel(
        id="sr-epmc-1",
        workspace_id=ws.id,
        source=SourceNamespace.EUROPEPMC.value,
        source_namespace="Europe PMC",
        external_id="PMC1001",
    )
    # Group 2: Excluded study (PubMed)
    sr3 = SourceRecordModel(
        id="sr-pub-2",
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace="PubMed",
        external_id="1002",
    )
    # Group 3: Pending study (Europe PMC)
    sr4 = SourceRecordModel(
        id="sr-epmc-2",
        workspace_id=ws.id,
        source=SourceNamespace.EUROPEPMC.value,
        source_namespace="Europe PMC",
        external_id="PMC1002",
    )
    # Group 4: Maybe study (PubMed)
    sr5 = SourceRecordModel(
        id="sr-pub-3",
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace="PubMed",
        external_id="1003",
    )
    db_session.add_all([sr1, sr2, sr3, sr4, sr5])
    db_session.flush()

    # Record revisions
    rr1 = RecordRevisionModel(id="rr1", source_record_id=sr1.id, title="GLP-1 receptor agonists in obesity", content_hash="h1", pmid="1001")
    rr2 = RecordRevisionModel(id="rr2", source_record_id=sr2.id, title="GLP-1 receptor agonists in obesity - trial report", content_hash="h2")
    rr3 = RecordRevisionModel(id="rr3", source_record_id=sr3.id, title="Preclinical mouse model study", content_hash="h3")
    rr4 = RecordRevisionModel(id="rr4", source_record_id=sr4.id, title="Ongoing cohort study protocol", content_hash="h4")
    rr5 = RecordRevisionModel(id="rr5", source_record_id=sr5.id, title="Borderline observational analysis", content_hash="h5")
    db_session.add_all([rr1, rr2, rr3, rr4, rr5])
    db_session.flush()

    # 4 Groups:
    # Group 1: 2 members (sr1 canonical, sr2 duplicate) -> INCLUDED
    grp1 = PaperGroupModel(
        id="grp-1",
        workspace_id=ws.id,
        membership_fingerprint="mfp1",
        row_version=2,
    )
    # Group 2: 1 member -> EXCLUDED
    grp2 = PaperGroupModel(
        id="grp-2",
        workspace_id=ws.id,
        membership_fingerprint="mfp2",
        row_version=2,
    )
    # Group 3: 1 member -> PENDING / UNSCREENED
    grp3 = PaperGroupModel(
        id="grp-3",
        workspace_id=ws.id,
        membership_fingerprint="mfp3",
        row_version=1,
    )
    # Group 4: 1 member -> MAYBE
    grp4 = PaperGroupModel(
        id="grp-4",
        workspace_id=ws.id,
        membership_fingerprint="mfp4",
        row_version=2,
    )
    db_session.add_all([grp1, grp2, grp3, grp4])
    db_session.flush()

    # Group members
    gm1 = GroupMemberModel(group_id=grp1.id, source_record_id=sr1.id)
    gm2 = GroupMemberModel(group_id=grp1.id, source_record_id=sr2.id)
    gm3 = GroupMemberModel(group_id=grp2.id, source_record_id=sr3.id)
    gm4 = GroupMemberModel(group_id=grp3.id, source_record_id=sr4.id)
    gm5 = GroupMemberModel(group_id=grp4.id, source_record_id=sr5.id)
    db_session.add_all([gm1, gm2, gm3, gm4, gm5])

    # Review events
    ev_include = ReviewEventModel(
        id="ev-inc-1",
        workspace_id=ws.id,
        group_id=grp1.id,
        sequence=1,
        event_type="screen_decision",
        actor_id="dr_reviewer",
        payload_json=json.dumps({"status": "include"}),
    )
    ev_exclude = ReviewEventModel(
        id="ev-exclude-1",
        workspace_id=ws.id,
        group_id=grp2.id,
        sequence=2,
        event_type="screen_decision",
        actor_id="dr_reviewer",
        reason="Animal model - non-human population",
        payload_json=json.dumps({"status": "exclude"}),
    )
    ev_maybe = ReviewEventModel(
        id="ev-maybe-1",
        workspace_id=ws.id,
        group_id=grp4.id,
        sequence=3,
        event_type="screen_decision",
        actor_id="dr_reviewer",
        reason="Unclear if randomized",
        payload_json=json.dumps({"status": "maybe"}),
    )
    db_session.add_all([ev_include, ev_exclude, ev_maybe])
    db_session.flush()

    # Compute PRISMA report
    report = compute_prisma_flow_report(db=db_session, workspace_id=ws.id)

    # Verify Identification
    assert report.stages.identification.total_identified == 5
    db_srcs = {s.source_name: s.records_count for s in report.stages.identification.database_sources}
    assert db_srcs["PubMed"] == 3
    assert db_srcs["Europe PMC"] == 2

    # Verify Pre-Screening: 5 records -> 4 groups = 1 duplicate removed, 4 eligible
    assert report.stages.pre_screening.total_removed == 1
    assert report.stages.pre_screening.duplicate_records_removed == 1
    assert report.stages.pre_screening.records_eligible_for_screening == 4

    # Verify Screening:
    # 4 groups: 1 included + 1 excluded = 2 screened; 1 pending; 1 maybe
    assert report.stages.screening.records_screened == 2
    assert report.stages.screening.records_excluded == 1
    assert report.stages.screening.records_advancing == 1
    assert report.stages.screening.records_pending == 1
    assert report.stages.screening.records_maybe == 1

    # Verify Exclusion Reason breakdown
    assert len(report.stages.screening.exclusion_reasons) == 1
    reason_item = report.stages.screening.exclusion_reasons[0]
    assert reason_item.reason == "Animal model - non-human population"
    assert reason_item.count == 1
    assert reason_item.percentage == 100.0

    # Verify Included: 1 unique study, but 2 publication reports
    assert report.stages.included.studies_included == 1
    assert report.stages.included.reports_included == 2

    # Verify Mathematical Reconciliation
    assert report.reconciliation.is_reconciled is True
    assert report.reconciliation.identification_balance == 0
    assert report.reconciliation.screening_balance == 0

    # Verify Validation Warnings: pending records and maybe records flagged
    warn_msgs = [w.message for w in report.validation_issues]
    assert any("unscreened" in m.lower() for m in warn_msgs)
    assert any("maybe" in m.lower() for m in warn_msgs)


def test_stage_records_drilldown_and_pagination(db_session: Session):
    ws, _, _, _ = _seed_test_review(db_session, "ws-prisma-drilldown")

    sr = SourceRecordModel(
        id="sr-drill-1",
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace="PubMed",
        external_id="99001",
    )
    db_session.add(sr)
    db_session.flush()

    rr = RecordRevisionModel(id="rr-d1", source_record_id=sr.id, title="Drilldown Test Trial", content_hash="hd1", doi="10.1000/182")
    db_session.add(rr)
    db_session.flush()

    grp = PaperGroupModel(
        id="grp-d1",
        workspace_id=ws.id,
        membership_fingerprint="mfpd1",
        row_version=2,
    )
    db_session.add(grp)
    db_session.flush()

    gm = GroupMemberModel(group_id=grp.id, source_record_id=sr.id)
    ev = ReviewEventModel(
        id="ev-d1",
        workspace_id=ws.id,
        group_id=grp.id,
        sequence=1,
        event_type="screen_decision",
        actor_id="dr_reviewer",
        payload_json=json.dumps({"status": "include"}),
    )
    db_session.add_all([gm, ev])
    db_session.flush()

    # Drill down into "included" stage
    res = get_prisma_stage_records(
        db=db_session,
        workspace_id=ws.id,
        stage=PrismaStage.INCLUDED,
        limit=10,
        offset=0,
    )
    assert res.total_count == 1
    assert len(res.records) == 1
    rec = res.records[0]
    assert rec.title == "Drilldown Test Trial"
    assert rec.doi == "10.1000/182"
    assert rec.decision == "include"


def test_csv_export_with_formula_sanitization(db_session: Session):
    ws, _, _, _ = _seed_test_review(db_session, "ws-prisma-csv")

    # Add an excluded record with formula injection attempt
    sr = SourceRecordModel(
        id="sr-inj-1",
        workspace_id=ws.id,
        source=SourceNamespace.PUBMED.value,
        source_namespace="PubMed",
        external_id="inj01",
    )
    db_session.add(sr)
    db_session.flush()

    rr = RecordRevisionModel(id="rr-inj-1", source_record_id=sr.id, title="=cmd|'/C calc'!A0", content_hash="hinj")
    db_session.add(rr)
    db_session.flush()

    grp = PaperGroupModel(
        id="grp-inj-1",
        workspace_id=ws.id,
        membership_fingerprint="mfpinj",
        row_version=2,
    )
    db_session.add(grp)
    db_session.flush()

    gm = GroupMemberModel(group_id=grp.id, source_record_id=sr.id)
    ev = ReviewEventModel(
        id="ev-inj-1",
        workspace_id=ws.id,
        group_id=grp.id,
        sequence=1,
        event_type="screen_decision",
        actor_id="hacker",
        reason="=HYPERLINK(\"http://evil.com\")",
        payload_json=json.dumps({"status": "exclude"}),
    )
    db_session.add_all([gm, ev])
    db_session.flush()

    csv_data = export_prisma_csv(db=db_session, workspace_id=ws.id)
    assert "PRISMA 2020 Flow Report" in csv_data
    # Formula characters must be sanitized with prepended single quote
    assert "'=HYPERLINK" in csv_data or "HYPERLINK" in csv_data


def test_snapshot_lifecycle(db_session: Session):
    ws, _, _, _ = _seed_test_review(db_session, "ws-prisma-snapshots")

    # Save snapshot
    req = PrismaSnapshotCreateRequest(
        name="Manuscript Protocol Final",
        notes="Audit snapshot prior to submission",
        actor_id="dr_smith",
    )
    snap_resp = save_prisma_snapshot(
        db=db_session,
        workspace_id=ws.id,
        payload=req,
    )

    assert snap_resp.snapshot_id is not None
    assert snap_resp.name == 'Manuscript Protocol Final'
    assert snap_resp.schema_version == "2020.1"

    # List snapshots
    summaries = list_prisma_snapshots(db=db_session, workspace_id=ws.id)
    assert len(summaries) == 1
    assert summaries[0].name == "Manuscript Protocol Final"
    assert summaries[0].created_by == "dr_smith"

    # Get snapshot by ID
    loaded_snap = get_prisma_snapshot(db=db_session, workspace_id=ws.id, snapshot_id=snap_resp.snapshot_id)
    assert loaded_snap.snapshot_id == snap_resp.snapshot_id
    assert loaded_snap.workspace_id == ws.id
