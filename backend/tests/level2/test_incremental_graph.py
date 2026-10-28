"""Level 2 Incremental Graph Execution & Snapshot-Aware Replay Test Suite (C04).

Observable Verification Requirements:
1. Unchanged records do not rerun screen/PICO; changed criteria/text/method invalidates exactly affected outputs.
2. Known source record gains new query membership without redundant source fetch.
3. Exact restore makes zero source/model/algorithm calls and reproduces original snapshot.
4. Human decisions and old PICO annotations remain intact across incremental rerun and group changes.
5. Crash/retry during selective processing cannot publish incomplete state or duplicate review events.
6. Checkpoint version compatibility validation.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.contracts.enums import (
    EligibilityStatus,
)
from app.contracts.models import (
    DecisionCommand,
)
from app.db.models import (
    PicoAnnotationModel,
    QueryMembershipModel,
    QueryVersionModel,
    RecordRevisionModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.pico.validator import compute_text_hash
from app.services.corpus import (
    get_default_criteria_version,
    list_paper_groups_in_revision,
    process_corpus,
)
from app.services.review_decisions import record_screening_decision
from app.workflows.pipeline import run_review_pipeline


def create_test_workspace(db: Session, title: str = "C04 Incremental Workspace") -> WorkspaceModel:
    """Helper to create an active test workspace."""
    ws = WorkspaceModel(
        id=f"ws-{uuid4().hex[:8]}",
        title=title,
        description="Workspace for C04 incremental graph tests",
        created_by="user-test-c04",
        row_version=1,
    )
    db.add(ws)
    db.flush()

    default_crit = get_default_criteria_version(workspace_id=ws.id)
    import json

    from app.db.models import CriteriaVersionModel
    from app.services.corpus import utc_now

    crit_model = CriteriaVersionModel(
        id=default_crit.id,
        workspace_id=ws.id,
        sequence=1,
        question=default_crit.question,
        pico_json=json.dumps(default_crit.pico_description),
        criteria_json=json.dumps([c.model_dump() for c in default_crit.criteria]),
        content_hash=default_crit.content_hash,
        created_at=utc_now(),
    )
    db.add(crit_model)

    sqv = QueryVersionModel(
        id=f"sqv-{uuid4().hex[:8]}",
        workspace_id=ws.id,
        sequence=1,
        ast_json=json.dumps({"field": "ALL", "value": "diabetes"}),
        sources_json=json.dumps(["pubmed"]),
        criteria_version_id=crit_model.id,
        content_hash="qv-hash-c04",
    )
    db.add(sqv)
    db.flush()

    se = SearchExecutionModel(
        id=f"se-{uuid4().hex[:8]}",
        query_version_id=sqv.id,
        source="pubmed",
        exact_query="diabetes",
        synonym_setting=False,
        hit_count=2,
        status="completed",
    )
    db.add(se)
    db.flush()
    return ws


def add_record(
    db: Session,
    workspace_id: str,
    search_execution_id: str,
    pmid: str,
    title: str,
    abstract: str,
) -> tuple[SourceRecordModel, RecordRevisionModel]:
    """Helper to add source record and revision linked to search execution."""
    from app.services.corpus import utc_now

    src = SourceRecordModel(
        id=f"src-{uuid4().hex[:8]}",
        workspace_id=workspace_id,
        source="pubmed",
        source_namespace="pubmed",
        external_id=pmid,
    )
    db.add(src)
    db.flush()

    content_hash = compute_text_hash(abstract)
    rev = RecordRevisionModel(
        id=f"rev-{uuid4().hex[:8]}",
        source_record_id=src.id,
        content_hash=content_hash,
        title=title,
        abstract_text=abstract,
        year=2024,
        journal="Diabetes Care",
        doi=f"10.1000/{pmid}",
        pmid=pmid,
        metadata_json="{}",
        fetched_at=utc_now(),
    )
    db.add(rev)
    db.flush()

    db.add(
        QueryMembershipModel(
            search_execution_id=search_execution_id,
            source_record_id=src.id,
            record_revision_id=rev.id,
        )
    )
    db.flush()
    return src, rev


def test_unchanged_records_reuse_outputs_and_new_records_compute(db_session: Session):
    """Test that unchanged records reuse existing screening and PICO outputs, and new records compute."""
    ws = create_test_workspace(db_session)
    se = db_session.query(SearchExecutionModel).filter(
        SearchExecutionModel.query_version.has(workspace_id=ws.id)
    ).first()

    # Add 2 initial records
    add_record(
        db_session,
        ws.id,
        se.id,
        "101",
        "Metformin for Type 2 Diabetes",
        "A double-blind randomized clinical trial of metformin in adults with type 2 diabetes.",
    )
    add_record(
        db_session,
        ws.id,
        se.id,
        "102",
        "Pioglitazone for Glycemic Control",
        "A double-blind randomized clinical trial of pioglitazone in adults with type 2 diabetes.",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_path = str(Path(tmp_dir) / "ckpt.sqlite")

        # Initial execution: both records must be computed
        res1 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        assert res1["stage"] == "completed"
        assert res1["group_count"] == 2
        assert res1["recomputed_screening_count"] == 2
        assert res1["reused_screening_count"] == 0
        assert res1["recomputed_pico_count"] == 2
        assert res1["reused_pico_count"] == 0

        # Add 1 new record (total 3)
        add_record(
            db_session,
            ws.id,
            se.id,
            "103",
            "Empagliflozin Cardiovascular Safety",
            "A double-blind randomized clinical trial of empagliflozin in adults with type 2 diabetes.",
        )

        # Second incremental run: 2 existing records must be reused; only 1 newly added record recomputed
        res2 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        assert res2["stage"] == "completed"
        assert res2["group_count"] == 3
        assert res2["recomputed_screening_count"] == 1
        assert res2["reused_screening_count"] == 2
        assert res2["recomputed_pico_count"] == 1
        assert res2["reused_pico_count"] == 2
        assert res2["invalidation_fingerprint"] is not None


def test_criteria_change_invalidates_screening_but_preserves_pico_reuse(db_session: Session):
    """Test that modifying criteria version invalidates screening outputs while preserving PICO extraction reuse."""
    ws = create_test_workspace(db_session)
    se = db_session.query(SearchExecutionModel).filter(
        SearchExecutionModel.query_version.has(workspace_id=ws.id)
    ).first()

    add_record(
        db_session,
        ws.id,
        se.id,
        "201",
        "Sulfonylurea Monotherapy in Seniors",
        "Clinical study of glipizide in elderly diabetes patients.",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_path = str(Path(tmp_dir) / "ckpt.sqlite")

        # Initial run
        res1 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        assert res1["recomputed_screening_count"] == 1
        assert res1["recomputed_pico_count"] == 1

        # Create updated criteria version with strict exclusion
        import json

        from app.db.models import CriteriaVersionModel
        from app.services.corpus import utc_now

        crit_v2 = CriteriaVersionModel(
            id=f"crit-v2-{uuid4().hex[:6]}",
            workspace_id=ws.id,
            sequence=2,
            question="Is sulfonylurea safe in elderly patients?",
            pico_json='{"population": "elderly diabetes"}',
            criteria_json=json.dumps([
                {
                    "id": "crit-seniors",
                    "name": "Senior population",
                    "category": "population",
                    "is_inclusion": True,
                    "rationale": "Must be elderly diabetes patients",
                    "metadata_first": True,
                }
            ]),
            content_hash=compute_text_hash("Is sulfonylurea safe in elderly patients?"),
            created_at=utc_now(),
        )
        db_session.add(crit_v2)
        db_session.flush()

        # Run with criteria_version_id=crit_v2.id
        res2 = run_review_pipeline(
            workspace_id=ws.id,
            criteria_version_id=crit_v2.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )

        # Screening was invalidated by new criteria content_hash -> recomputed
        assert res2["recomputed_screening_count"] == 1
        assert res2["reused_screening_count"] == 0

        # PICO does NOT depend on criteria -> reused 100%!
        assert res2["reused_pico_count"] == 1
        assert res2["recomputed_pico_count"] == 0


def test_known_source_record_gains_new_query_membership_without_duplicate_fetch(db_session: Session):
    """Test that a known source record linked to a new search execution shares source identity."""
    ws = create_test_workspace(db_session)
    se1 = db_session.query(SearchExecutionModel).filter(
        SearchExecutionModel.query_version.has(workspace_id=ws.id)
    ).first()

    src, rev = add_record(
        db_session,
        ws.id,
        se1.id,
        "301",
        "Insulin Glargine Versus Degludec",
        "Comparative trial of basal insulin analogs.",
    )

    # Create second search execution in same workspace
    from app.db.models import CriteriaVersionModel
    crit_ver = db_session.query(CriteriaVersionModel).filter_by(workspace_id=ws.id).first()

    sqv2 = QueryVersionModel(
        id=f"sqv-2-{uuid4().hex[:6]}",
        workspace_id=ws.id,
        sequence=2,
        ast_json=json.dumps({"field": "ALL", "value": "insulin"}),
        sources_json=json.dumps(["pubmed"]),
        criteria_version_id=crit_ver.id,
        content_hash="qv2-hash-c04",
    )
    db_session.add(sqv2)
    db_session.flush()

    se2 = SearchExecutionModel(
        id=f"se-2-{uuid4().hex[:6]}",
        query_version_id=sqv2.id,
        source="pubmed",
        exact_query="insulin",
        synonym_setting=False,
        hit_count=1,
        status="completed",
    )
    db_session.add(se2)
    db_session.flush()

    # Link existing source record to execution 2
    db_session.add(
        QueryMembershipModel(
            search_execution_id=se2.id,
            source_record_id=src.id,
            record_revision_id=rev.id,
        )
    )
    db_session.flush()

    # Verify database has exactly 1 SourceRecordModel and 1 RecordRevisionModel
    src_count = db_session.query(SourceRecordModel).filter_by(workspace_id=ws.id).count()
    assert src_count == 1

    # But QueryMembershipModel has 2 memberships
    mem_count = db_session.query(QueryMembershipModel).filter_by(source_record_id=src.id).count()
    assert mem_count == 2

    # Corpus processing produces exactly 1 group for this shared record
    rev_corpus = process_corpus(db_session, workspace_id=ws.id)
    assert rev_corpus.record_count == 1
    assert rev_corpus.group_count == 1


def test_exact_restore_makes_zero_algorithm_calls_and_reproduces_snapshot(db_session: Session):
    """Test that exact restore bypasses retrieval, dedup, screening, and PICO, making zero calls."""
    ws = create_test_workspace(db_session)
    se = db_session.query(SearchExecutionModel).filter(
        SearchExecutionModel.query_version.has(workspace_id=ws.id)
    ).first()

    add_record(
        db_session,
        ws.id,
        se.id,
        "401",
        "Pioglitazone in Nonalcoholic Steatohepatitis",
        "A randomized trial of pioglitazone in diabetic steatohepatitis.",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_path = str(Path(tmp_dir) / "ckpt.sqlite")

        # 1. Create Revision 1
        res1 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        rev1_id = res1["corpus_revision_id"]

        # 2. Add second record to create Revision 2
        add_record(
            db_session,
            ws.id,
            se.id,
            "402",
            "GLP-1 Receptor Agonists in Weight Loss",
            "Semaglutide administration in obese prediabetic patients.",
        )
        res2 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        assert res2["record_count"] == 2

        # 3. Restore to Revision 1 via workflow mode="restore"
        res_restore = run_review_pipeline(
            workspace_id=ws.id,
            mode="restore",
            restore_snapshot_id=rev1_id,
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )

        assert res_restore["stage"] == "completed"
        assert res_restore["corpus_revision_id"] == rev1_id
        assert res_restore["record_count"] == 1
        assert res_restore["group_count"] == 1
        assert "restore_snapshot:succeeded" in res_restore["trace_steps"]

        # 0 calls to screening and 0 calls to PICO during restore
        assert res_restore["reused_screening_count"] == 0
        assert res_restore["recomputed_screening_count"] == 0
        assert res_restore["reused_pico_count"] == 0
        assert res_restore["recomputed_pico_count"] == 0


def test_human_decisions_and_pico_annotations_remain_intact_across_incremental_rerun(db_session: Session):
    """Test that reviewer decisions and PICO spans remain intact and carry over across incremental updates."""
    ws = create_test_workspace(db_session)
    se = db_session.query(SearchExecutionModel).filter(
        SearchExecutionModel.query_version.has(workspace_id=ws.id)
    ).first()

    _src1, rev1 = add_record(
        db_session,
        ws.id,
        se.id,
        "501",
        "Acarbose for Diabetes",
        "A double-blind randomized clinical trial of acarbose in adults with type 2 diabetes.",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_path = str(Path(tmp_dir) / "ckpt.sqlite")

        # Run 1
        res1 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        groups_v1 = list_paper_groups_in_revision(db_session, res1["corpus_revision_id"])
        assert len(groups_v1) == 1
        g1 = groups_v1[0]

        # Reviewer manually confirms INCLUDE with reason
        record_screening_decision(
            db=db_session,
            group_id=g1.id,
            command=DecisionCommand(
                status=EligibilityStatus.INCLUDE,
                reason="Directly addresses alpha-glucosidase target in type 2 diabetes.",
                expected_version=1,
            ),
            actor_id="dr-reviewer-1",
        )

        # Add second paper and rerun incrementally
        add_record(
            db_session,
            ws.id,
            se.id,
            "502",
            "Colesevelam for Diabetes",
            "A double-blind randomized clinical trial of colesevelam in adults with type 2 diabetes.",
        )

        res2 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        groups_v2 = list_paper_groups_in_revision(db_session, res2["corpus_revision_id"])
        assert len(groups_v2) == 2

        # Group 1 retains human decision INCLUDE
        g1_v2 = next(g for g in groups_v2 if g.id == g1.id)
        assert g1_v2.effective_status == EligibilityStatus.INCLUDE
        assert g1_v2.has_human_decision is True

        # PICO annotations for rev1 are verified intact
        annos = db_session.query(PicoAnnotationModel).filter_by(record_revision_id=rev1.id).all()
        assert len(annos) >= 1
        for a in annos:
            assert a.quote is not None
            assert a.start_cp < a.end_cp


def test_crash_during_selective_processing_does_not_publish_incomplete_state(db_session: Session):
    """Test that a failure during selective processing rolls back atomically, preserving last good snapshot."""
    ws = create_test_workspace(db_session)
    se = db_session.query(SearchExecutionModel).filter(
        SearchExecutionModel.query_version.has(workspace_id=ws.id)
    ).first()

    add_record(
        db_session,
        ws.id,
        se.id,
        "601",
        "Bromocriptine Quick-Release for Diabetes",
        "Dopamine receptor agonist effects on metabolic control.",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_path = str(Path(tmp_dir) / "ckpt.sqlite")

        # Initial successful publish
        res1 = run_review_pipeline(
            workspace_id=ws.id,
            mode="incremental",
            checkpoint_db_path=ckpt_path,
            db=db_session,
        )
        initial_rev_id = res1["corpus_revision_id"]
        assert ws.current_revision_id == initial_rev_id

        # Add another record
        add_record(
            db_session,
            ws.id,
            se.id,
            "602",
            "Pramlintide Amylin Analog Injections",
            "Synthetic amylin analog in postprandial glucose regulation.",
        )

        # Simulate unexpected crash in screening engine during selective rerun
        with patch("app.screening.engine.ScreeningEngine.screen_record", side_effect=RuntimeError("Simulated LLM/Engine Crash")):
            res_fail = run_review_pipeline(
                workspace_id=ws.id,
                mode="incremental",
                checkpoint_db_path=ckpt_path,
                db=db_session,
            )

            assert res_fail["stage"] == "failed"
            assert "Simulated LLM/Engine Crash" in res_fail["error"]

            # Workspace current_revision_id MUST still point to initial_rev_id!
            db_session.refresh(ws)
            assert ws.current_revision_id == initial_rev_id


def test_incompatible_checkpoint_version_produces_controlled_error(db_session: Session):
    """Test that an incompatible checkpoint layout or graph version produces a controlled error."""
    ws = create_test_workspace(db_session)

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_path = str(Path(tmp_dir) / "ckpt.sqlite")

        # Execute with an invalid / obsolete graph version
        initial_state = {
            "workspace_id": ws.id,
            "job_id": None,
            "criteria_version_id": None,
            "corpus_revision_id": None,
            "group_count": 0,
            "record_count": 0,
            "included_count": 0,
            "excluded_count": 0,
            "uncertain_count": 0,
            "stage": "starting",
            "pending_human_review": None,
            "human_approved": False,
            "human_event_id": None,
            "error": None,
            "trace_steps": ["start"],
            "graph_version": "review_graph:v999.0.0-incompatible",
            "mode": "incremental",
            "restore_snapshot_id": None,
            "reused_screening_count": 0,
            "recomputed_screening_count": 0,
            "reused_pico_count": 0,
            "recomputed_pico_count": 0,
            "invalidation_fingerprint": None,
            "affected_group_ids": [],
        }

        from langgraph.checkpoint.sqlite import SqliteSaver

        from app.workflows.pipeline import build_review_graph

        with SqliteSaver.from_conn_string(ckpt_path) as saver:
            graph = build_review_graph(checkpointer=saver)
            res = graph.invoke(initial_state, config={"configurable": {"thread_id": f"test-th-{ws.id}", "db": db_session}})

            assert res["stage"] == "failed"
            assert "Incompatible checkpoint graph version" in res["error"]
            assert "validate_input:incompatible_version" in res["trace_steps"]
