"""Unit tests for Search Evolution Time Machine domain service."""
import hashlib
import json
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.contracts.enums import (
    DecisionEventType,
    EffectiveDecisionState,
    SearchEvolutionCategory,
    SourceNamespace,
)
from app.db.models import (
    CriteriaVersionModel,
    GroupMemberModel,
    PaperGroupModel,
    QueryMembershipModel,
    QueryVersionModel,
    RecordRevisionModel,
    ReviewConflictModel,
    ReviewEventModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.search_evolution import (
    compute_search_evolution_diff,
    get_search_version_detail,
    list_search_versions,
    restore_search_configuration,
)


@pytest.fixture
def test_setup(db_session: Session):
    """Create test workspace and base criteria version."""
    ws = WorkspaceModel(created_by="test-researcher", id="ws-evo-test", title="Evolution SLR Review")
    crit = CriteriaVersionModel(
        id="crit-evo-1",
        workspace_id=ws.id,
        sequence=1,
        question="What is the efficacy of gene therapy in hemoglobinopathies?",
        pico_json=json.dumps({"p": "hemoglobinopathies", "i": "gene therapy", "c": "standard care", "o": "survival"}),
        criteria_json=json.dumps({"inclusion": ["human trials"], "exclusion": ["animal models"]}),
        content_hash="crit-hash-1",
    )
    db_session.add_all([ws, crit])
    db_session.commit()
    return ws, crit


def _create_source_and_revision(
    db: Session,
    workspace_id: str,
    external_id: str,
    title: str,
    abstract: str = "Test abstract",
    year: int = 2023,
    journal: str = "Lancet",
    doi: str | None = None,
    pmid: str | None = None,
    authors: list[str] | None = None,
) -> tuple[SourceRecordModel, RecordRevisionModel]:
    authors_json = json.dumps(authors or ["Author One", "Author Two"])
    content_hash = hashlib.sha256(f"{title}\n{abstract}\n{year}".encode()).hexdigest()

    rec = SourceRecordModel(
        workspace_id=workspace_id,
        source=SourceNamespace.PUBMED.value,
        source_namespace=SourceNamespace.PUBMED.value,
        external_id=external_id,
    )
    db.add(rec)
    db.flush()

    rev = RecordRevisionModel(
        source_record_id=rec.id,
        content_hash=content_hash,
        title=title,
        abstract_text=abstract,
        authors_json=authors_json,
        year=year,
        journal=journal,
        doi=doi,
        pmid=pmid or external_id,
    )
    db.add(rev)
    db.flush()
    return rec, rev


def _create_search_run(
    db: Session,
    workspace_id: str,
    criteria_id: str,
    sequence: int,
    ast_dict: dict,
    records_with_revisions: list[tuple[SourceRecordModel, RecordRevisionModel]],
    change_description: str | None = None,
    parent_id: str | None = None,
) -> tuple[QueryVersionModel, SearchExecutionModel]:
    ast_json = json.dumps(ast_dict, sort_keys=True)
    sources_json = json.dumps([SourceNamespace.PUBMED.value])
    content_hash = hashlib.sha256(f"{ast_json}\n{sequence}".encode()).hexdigest()

    qv = QueryVersionModel(
        workspace_id=workspace_id,
        parent_id=parent_id,
        sequence=sequence,
        ast_json=ast_json,
        sources_json=sources_json,
        criteria_version_id=criteria_id,
        content_hash=content_hash,
        change_description=change_description,
    )
    db.add(qv)
    db.flush()

    ex = SearchExecutionModel(
        query_version_id=qv.id,
        source=SourceNamespace.PUBMED.value,
        exact_query="test query",
        hit_count=len(records_with_revisions),
        status="succeeded",
    )
    db.add(ex)
    db.flush()

    for rec, rev in records_with_revisions:
        m = QueryMembershipModel(
            search_execution_id=ex.id,
            source_record_id=rec.id,
            record_revision_id=rev.id,
        )
        db.add(m)
    db.commit()
    return qv, ex


def test_search_evolution_diff_categories(db_session: Session, test_setup):
    """Test all 6 search evolution categories: newly discovered, repeated, missing from newer, metadata changed."""
    ws, crit = test_setup

    # Record 1: Present in v1 and v2, identical -> REPEATED
    rec1, rev1_v1 = _create_source_and_revision(
        db_session, ws.id, "PMID001", "CRISPR in thalassemia", year=2023
    )

    # Record 2: Present in v1 only -> MISSING_FROM_NEWER (absence without deletion)
    rec2, rev2_v1 = _create_source_and_revision(
        db_session, ws.id, "PMID002", "Old chemotherapy regimen", year=2015
    )

    # Record 3: Present in v1 and v2, but metadata changed -> METADATA_CHANGED
    rec3, rev3_v1 = _create_source_and_revision(
        db_session, ws.id, "PMID003", "Interim analysis: Lentiviral gene addition", year=2022, journal="Blood"
    )
    # Target revision with updated title and year for rec3
    rev3_v2 = RecordRevisionModel(
        source_record_id=rec3.id,
        content_hash="new-hash-3",
        title="Final phase 3 results: Lentiviral gene addition",
        abstract_text="Updated long term data",
        authors_json=rev3_v1.authors_json,
        year=2024,
        journal="Blood",
        pmid="PMID003",
    )
    db_session.add(rev3_v2)
    db_session.flush()

    # Build Version 1
    qv1, _ = _create_search_run(
        db_session,
        ws.id,
        crit.id,
        sequence=1,
        ast_dict={"term": "gene therapy"},
        records_with_revisions=[(rec1, rev1_v1), (rec2, rev2_v1), (rec3, rev3_v1)],
        change_description="Initial broad search",
    )

    # Record 4: Present in v2 only -> NEWLY_DISCOVERED
    rec4, rev4_v2 = _create_source_and_revision(
        db_session, ws.id, "PMID004", "Prime editing for sickle cell", year=2024
    )

    # Build Version 2
    qv2, _ = _create_search_run(
        db_session,
        ws.id,
        crit.id,
        sequence=2,
        ast_dict={"term": "CRISPR OR prime editing"},
        records_with_revisions=[(rec1, rev1_v1), (rec3, rev3_v2), (rec4, rev4_v2)],
        change_description="Refined query focusing on modern editing",
        parent_id=qv1.id,
    )

    # Compute Diff: v1 (base) -> v2 (target)
    diff = compute_search_evolution_diff(db_session, ws.id, target_version_id=qv2.id, base_version_id=qv1.id)

    assert diff.summary.base_sequence == 1
    assert diff.summary.target_sequence == 2
    assert diff.summary.total_base_records == 3
    assert diff.summary.total_target_records == 3
    assert diff.summary.newly_discovered_count == 1
    assert diff.summary.repeated_count == 1
    assert diff.summary.missing_from_newer_count == 1
    assert diff.summary.metadata_changed_count == 1

    records_by_cat = {r.category: r for r in diff.records}

    # 1. Newly discovered
    r_new = records_by_cat[SearchEvolutionCategory.NEWLY_DISCOVERED]
    assert r_new.external_id == "PMID004"
    assert r_new.title == "Prime editing for sickle cell"

    # 2. Repeated
    r_rep = records_by_cat[SearchEvolutionCategory.REPEATED]
    assert r_rep.external_id == "PMID001"

    # 3. Missing from newer (Absence without deletion)
    r_miss = records_by_cat[SearchEvolutionCategory.MISSING_FROM_NEWER]
    assert r_miss.external_id == "PMID002"
    assert r_miss.title == "Old chemotherapy regimen"

    # 4. Metadata changed (with field-level diffs)
    r_meta = records_by_cat[SearchEvolutionCategory.METADATA_CHANGED]
    assert r_meta.external_id == "PMID003"
    assert len(r_meta.field_diffs) == 3  # title, abstract, year
    field_names = [fd.field_name for fd in r_meta.field_diffs]
    assert "title" in field_names
    assert "year" in field_names
    title_diff = next(fd for fd in r_meta.field_diffs if fd.field_name == "title")
    assert title_diff.base_value == "Interim analysis: Lentiviral gene addition"
    assert title_diff.target_value == "Final phase 3 results: Lentiviral gene addition"


def test_screening_decision_preservation_and_stale_flag(db_session: Session, test_setup):
    """Test that human screening decisions are preserved and metadata changes trigger review warnings."""
    ws, crit = test_setup

    rec, rev_v1 = _create_source_and_revision(
        db_session, ws.id, "PMID099", "Initial clinical report", year=2021
    )

    # Create PaperGroup and Human Screening Decision on rec
    group = PaperGroupModel(
        workspace_id=ws.id,
        membership_fingerprint="fp-099",
    )
    db_session.add(group)
    db_session.flush()

    member = GroupMemberModel(
        group_id=group.id,
        source_record_id=rec.id,
    )
    db_session.add(member)

    # Human decides to INCLUDE with note
    event = ReviewEventModel(
        workspace_id=ws.id,
        group_id=group.id,
        sequence=1,
        actor_id="dr-smith",
        event_type=DecisionEventType.SCREEN_DECISION.value,
        payload_json=json.dumps({"decision": "include", "notes": "Solid phase 2 data meeting inclusion criteria"}),
    )
    db_session.add(event)
    db_session.commit()

    # Search v1
    qv1, _ = _create_search_run(
        db_session, ws.id, crit.id, sequence=1, ast_dict={"term": "query 1"}, records_with_revisions=[(rec, rev_v1)]
    )

    # Search v2: Same record, but updated title and journal
    rev_v2 = RecordRevisionModel(
        source_record_id=rec.id,
        content_hash="hash-v2",
        title="Initial clinical report: Withdrawn due to error",
        abstract_text="Study withdrawn",
        authors_json=rev_v1.authors_json,
        year=2022,
        journal="Retraction Watch",
        pmid="PMID099",
    )
    db_session.add(rev_v2)
    db_session.flush()

    qv2, _ = _create_search_run(
        db_session, ws.id, crit.id, sequence=2, ast_dict={"term": "query 2"}, records_with_revisions=[(rec, rev_v2)], parent_id=qv1.id
    )

    diff = compute_search_evolution_diff(db_session, ws.id, target_version_id=qv2.id, base_version_id=qv1.id)

    assert len(diff.records) == 1
    rec_diff = diff.records[0]

    # Invariant: Decision is preserved!
    assert rec_diff.screening_decision == EffectiveDecisionState.INCLUDE
    assert rec_diff.screening_reason == "Solid phase 2 data meeting inclusion criteria"
    assert rec_diff.category == SearchEvolutionCategory.METADATA_CHANGED
    # Invariant: Flagged because metadata changed since human decision
    assert rec_diff.metadata_changed_since_screening is True


def test_non_destructive_restore(db_session: Session, test_setup):
    """Test restoring an earlier search version without deleting history or review decisions."""
    ws, crit = test_setup

    rec, rev = _create_source_and_revision(db_session, ws.id, "PMID050", "Paper for test", year=2023)

    qv1, _ = _create_search_run(
        db_session,
        ws.id,
        crit.id,
        sequence=1,
        ast_dict={"term": "broad query"},
        records_with_revisions=[(rec, rev)],
        change_description="Original broad strategy",
    )

    qv2, _ = _create_search_run(
        db_session,
        ws.id,
        crit.id,
        sequence=2,
        ast_dict={"term": "overly restrictive query"},
        records_with_revisions=[],
        change_description="Too narrow",
        parent_id=qv1.id,
    )

    # Restore v1
    res = restore_search_configuration(
        db_session,
        workspace_id=ws.id,
        target_version_id=qv1.id,
        reason="Reverting to broad query after restrictive query yielded 0 hits",
        actor_id="researcher-1",
    )

    assert res.restored_from_version_id == qv1.id
    assert res.restored_query.sequence == 3
    assert res.restored_query.parent_id == qv1.id
    assert res.restored_query.restored_from_version_id == qv1.id
    assert "Restored search strategy from Version 1" in res.restored_query.change_description
    assert "Reverting to broad query" in res.restored_query.change_description

    # Verify linear history is preserved (v1 and v2 still exist!)
    versions = list_search_versions(db_session, ws.id)
    assert len(versions) == 3
    sequences = [v.sequence for v in versions]
    assert sequences == [3, 2, 1]  # descending
