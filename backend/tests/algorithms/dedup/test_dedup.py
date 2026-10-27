"""Comprehensive tests for deterministic deduplication engine (B01)."""
import random

from app.contracts.enums import DedupEdgeStatus
from app.contracts.models import DedupProposal, RecordRevisionResponse
from app.contracts.ports import DeduplicationPort
from app.dedup import DeduplicationEngine, find_candidate_pairs, partition_groups
from tests.fixtures.synthetic_records import (
    RECORD_EXACT_EUROPEPMC,
    RECORD_EXACT_PUBMED,
    RECORD_MISSING_METADATA,
    RECORD_SAME_STUDY_PROTOCOL,
    RECORD_SAME_STUDY_RESULTS,
    RECORD_UNCERTAIN_A,
    RECORD_UNCERTAIN_B,
)


def make_record(raw: dict) -> RecordRevisionResponse:
    """Helper to instantiate RecordRevisionResponse from synthetic fixture dictionary."""
    return RecordRevisionResponse.model_validate(raw)


def test_engine_satisfies_port():
    """Engine must implement runtime checkable DeduplicationPort protocol."""
    engine = DeduplicationEngine()
    assert isinstance(engine, DeduplicationPort)


def test_exact_doi_match():
    """Identical DOIs across PubMed and Europe PMC must yield a 1.0 confidence proposal."""
    rec_a = make_record(RECORD_EXACT_PUBMED)
    rec_b = make_record(RECORD_EXACT_EUROPEPMC)

    proposals = find_candidate_pairs([rec_a, rec_b])
    assert len(proposals) == 1
    prop = proposals[0]
    assert prop.score == 1.0
    assert prop.evidence["matched_by"] == "exact_doi"
    assert prop.status == DedupEdgeStatus.PROPOSED


def test_null_doi_never_merges_on_doi():
    """Two papers without DOIs must NEVER merge on DOI."""
    rec_a = make_record(RECORD_MISSING_METADATA)
    rec_b = make_record(RECORD_UNCERTAIN_A)

    proposals = find_candidate_pairs([rec_a, rec_b])
    for prop in proposals:
        assert prop.evidence.get("matched_by") != "exact_doi"


def test_contradictory_strong_identifiers_abstain():
    """Papers with distinct, valid DOIs must never be proposed as duplicate papers."""
    rec_a = make_record(RECORD_EXACT_PUBMED)  # DOI: 10.1056/nejmoa2024001
    rec_b = make_record(RECORD_SAME_STUDY_PROTOCOL)  # DOI: 10.1186/s13063-020-001

    proposals = find_candidate_pairs([rec_a, rec_b])
    assert len(proposals) == 0


def test_same_study_protocol_vs_results_separation():
    """Separate reports of the same clinical study (Protocol vs Results) are not duplicate papers."""
    rec_proto = make_record(RECORD_SAME_STUDY_PROTOCOL)
    rec_results = make_record(RECORD_SAME_STUDY_RESULTS)

    proposals = find_candidate_pairs([rec_proto, rec_results])
    # Must NOT propose as duplicate publications
    assert len(proposals) == 0


def test_multi_field_uncertain_candidate():
    """High title similarity with author and year agreement yields a candidate."""
    rec_a = make_record(RECORD_UNCERTAIN_A)
    rec_b = make_record(RECORD_UNCERTAIN_B)

    proposals = find_candidate_pairs([rec_a, rec_b])
    assert len(proposals) == 1
    assert proposals[0].score >= 0.80
    assert proposals[0].evidence["matched_by"] in ("exact_normalized_title", "fuzzy_multi_field")

    # Explicit fuzzy match where normalized titles differ slightly
    raw_fuzzy_b = dict(RECORD_UNCERTAIN_B)
    raw_fuzzy_b["id"] = "rec-fuzzy-b"
    raw_fuzzy_b["title"] = "Metformin therapy in type 2 diabetes: a prospective preliminary evaluation"
    rec_fuzzy_b = make_record(raw_fuzzy_b)
    fuzzy_proposals = find_candidate_pairs([rec_a, rec_fuzzy_b])
    assert len(fuzzy_proposals) == 1
    assert fuzzy_proposals[0].evidence["matched_by"] == "fuzzy_multi_field"
    assert fuzzy_proposals[0].score >= 0.75


def test_permutation_invariance():
    """Order of input records must yield identical proposals and group partitions."""
    records = [
        make_record(RECORD_EXACT_PUBMED),
        make_record(RECORD_EXACT_EUROPEPMC),
        make_record(RECORD_UNCERTAIN_A),
        make_record(RECORD_UNCERTAIN_B),
        make_record(RECORD_SAME_STUDY_RESULTS),
    ]

    proposals_1 = find_candidate_pairs(records)

    # Shuffle input records
    shuffled = records.copy()
    random.seed(42)
    random.shuffle(shuffled)
    proposals_2 = find_candidate_pairs(shuffled)

    # Proposals must match exactly
    assert len(proposals_1) == len(proposals_2)
    for p1, p2 in zip(proposals_1, proposals_2, strict=True):
        assert p1.record_id_a == p2.record_id_a
        assert p1.record_id_b == p2.record_id_b
        assert p1.score == p2.score

    # Partitioning must also be strictly identical
    groups_1 = partition_groups(records, proposals_1)
    groups_2 = partition_groups(shuffled, proposals_2)
    assert len(groups_1) == len(groups_2)
    for g1, g2 in zip(groups_1, groups_2, strict=True):
        assert g1["group_id"] == g2["group_id"]
        assert g1["representative"].id == g2["representative"].id
        assert g1["member_ids"] == g2["member_ids"]


def test_cannot_link_constraint_blocks_transitive_merge():
    """Cannot-link constraint must block merging even if edge was accepted."""
    rec_a = make_record(RECORD_EXACT_PUBMED)
    rec_b = make_record(RECORD_EXACT_EUROPEPMC)

    edge = DedupProposal(
        record_id_a=rec_a.id,
        record_id_b=rec_b.id,
        score=1.0,
        method_version="test",
        evidence={"matched_by": "manual"},
        status=DedupEdgeStatus.CONFIRMED,
    )

    # Without cannot-link -> merged into 1 group
    groups_merged = partition_groups([rec_a, rec_b], [edge], cannot_link_pairs=None)
    assert len(groups_merged) == 1
    assert groups_merged[0]["member_count"] == 2

    # With cannot-link between A and B -> must remain 2 separate groups!
    cannot_link = {(rec_a.id, rec_b.id)}
    groups_split = partition_groups([rec_a, rec_b], [edge], cannot_link_pairs=cannot_link)
    assert len(groups_split) == 2
    assert groups_split[0]["member_count"] == 1
    assert groups_split[1]["member_count"] == 1


def test_deterministic_representative_selection():
    """PubMed record with complete metadata is prioritized over Europe PMC partial copy."""
    rec_pubmed = make_record(RECORD_EXACT_PUBMED)
    rec_pmc = make_record(RECORD_EXACT_EUROPEPMC)

    edge = DedupProposal(
        record_id_a=rec_pubmed.id,
        record_id_b=rec_pmc.id,
        score=1.0,
        method_version="test",
        evidence={},
        status=DedupEdgeStatus.CONFIRMED,
    )

    groups = partition_groups([rec_pubmed, rec_pmc], [edge])
    assert len(groups) == 1
    # PubMed record must be chosen as representative
    assert groups[0]["representative"].id == rec_pubmed.id
    assert groups[0]["representative"].source == "pubmed"
