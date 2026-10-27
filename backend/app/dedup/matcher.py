"""Deterministic candidate pair matching and deduplication proposals."""
from __future__ import annotations

from rapidfuzz import fuzz

from app.contracts.enums import DedupEdgeStatus
from app.contracts.models import DedupProposal, RecordRevisionResponse
from app.dedup.normalization import (
    extract_author_tokens,
    extract_trial_registrations,
    is_study_protocol_or_design,
    normalize_doi,
    normalize_pmid,
    normalize_title,
)

METHOD_VERSION = "dedup-rules-v1.0.0"


def find_candidate_pairs(
    records: list[RecordRevisionResponse],
) -> list[DedupProposal]:
    """Detect duplicate candidate pairs deterministically across given records.

    Examines exact identifiers (DOI, PMID), normalized title equality, and
    multi-field fuzzy similarity with author and year confirmation.
    Strictly differentiates separate reports of the same clinical study
    from duplicate copies of the same publication.
    """
    if len(records) < 2:
        return []

    # Sort deterministically by record revision ID
    sorted_records = sorted(records, key=lambda r: r.id)
    proposals: list[DedupProposal] = []
    seen_pairs: set[tuple[str, str]] = set()

    n = len(sorted_records)
    for i in range(n):
        rec_a = sorted_records[i]
        doi_a = normalize_doi(rec_a.doi)
        pmid_a = normalize_pmid(rec_a.pmid)
        norm_title_a = normalize_title(rec_a.title)
        authors_a = extract_author_tokens(rec_a.authors)
        is_proto_a = is_study_protocol_or_design(rec_a.title)
        trials_a = set(extract_trial_registrations(rec_a.abstract_text or "") + extract_trial_registrations(rec_a.title))

        for j in range(i + 1, n):
            rec_b = sorted_records[j]
            pair_key = (rec_a.id, rec_b.id)
            if pair_key in seen_pairs:
                continue

            doi_b = normalize_doi(rec_b.doi)
            pmid_b = normalize_pmid(rec_b.pmid)
            norm_title_b = normalize_title(rec_b.title)
            authors_b = extract_author_tokens(rec_b.authors)
            is_proto_b = is_study_protocol_or_design(rec_b.title)
            trials_b = set(extract_trial_registrations(rec_b.abstract_text or "") + extract_trial_registrations(rec_b.title))

            # -------------------------------------------------------------
            # Rule 0: Contradictory Strong Identifiers Check
            # If both have valid DOIs and they differ, they cannot be the same paper.
            # -------------------------------------------------------------
            has_contradictory_doi = bool(doi_a and doi_b and doi_a != doi_b)
            has_contradictory_pmid = bool(pmid_a and pmid_b and pmid_a != pmid_b)
            if has_contradictory_doi or has_contradictory_pmid:
                # Strong contradictory identifier blocks duplicate proposal
                continue

            # -------------------------------------------------------------
            # Rule 1: Study vs. Paper Distinction
            # If records share a trial registry ID, but one is protocol and one is results,
            # they are companion reports of the same clinical study, NOT duplicate papers.
            # -------------------------------------------------------------
            shared_trials = trials_a.intersection(trials_b)
            if shared_trials and (is_proto_a != is_proto_b):
                # Companion reports of same study -> do not propose as duplicate publication
                continue

            # -------------------------------------------------------------
            # Rule 2: Exact Identifier Matches (DOI or PMID)
            # -------------------------------------------------------------
            if doi_a and doi_b and doi_a == doi_b:
                evidence = {
                    "matched_by": "exact_doi",
                    "doi": doi_a,
                    "title_similarity": round(fuzz.ratio(norm_title_a, norm_title_b) / 100.0, 3),
                    "shared_trials": sorted(shared_trials),
                }
                proposals.append(
                    DedupProposal(
                        record_id_a=rec_a.id,
                        record_id_b=rec_b.id,
                        score=1.0,
                        method_version=METHOD_VERSION,
                        evidence=evidence,
                        status=DedupEdgeStatus.PROPOSED,
                    )
                )
                seen_pairs.add(pair_key)
                continue

            if pmid_a and pmid_b and pmid_a == pmid_b:
                evidence = {
                    "matched_by": "exact_pmid",
                    "pmid": pmid_a,
                    "title_similarity": round(fuzz.ratio(norm_title_a, norm_title_b) / 100.0, 3),
                    "shared_trials": sorted(shared_trials),
                }
                proposals.append(
                    DedupProposal(
                        record_id_a=rec_a.id,
                        record_id_b=rec_b.id,
                        score=1.0,
                        method_version=METHOD_VERSION,
                        evidence=evidence,
                        status=DedupEdgeStatus.PROPOSED,
                    )
                )
                seen_pairs.add(pair_key)
                continue

            # -------------------------------------------------------------
            # Rule 3: Exact Normalized Title Match
            # -------------------------------------------------------------
            if norm_title_a and norm_title_b and norm_title_a == norm_title_b:
                # Require author or year agreement to prevent false merges of generic titles
                author_overlap = bool(authors_a.intersection(authors_b)) if (authors_a and authors_b) else True
                year_agree = abs(rec_a.year - rec_b.year) <= 1 if (rec_a.year and rec_b.year) else True

                if author_overlap and year_agree:
                    evidence = {
                        "matched_by": "exact_normalized_title",
                        "author_overlap": list(authors_a.intersection(authors_b)),
                        "year_a": rec_a.year,
                        "year_b": rec_b.year,
                    }
                    proposals.append(
                        DedupProposal(
                            record_id_a=rec_a.id,
                            record_id_b=rec_b.id,
                            score=0.95,
                            method_version=METHOD_VERSION,
                            evidence=evidence,
                            status=DedupEdgeStatus.PROPOSED,
                        )
                    )
                    seen_pairs.add(pair_key)
                    continue

            # -------------------------------------------------------------
            # Rule 4: Multi-Field Fuzzy Match
            # High title token sort similarity + independent author overlap + year proximity
            # -------------------------------------------------------------
            if norm_title_a and norm_title_b:
                title_sim = fuzz.token_sort_ratio(norm_title_a, norm_title_b)
                author_overlap = bool(authors_a.intersection(authors_b)) if (authors_a and authors_b) else False
                year_diff = abs(rec_a.year - rec_b.year) if (rec_a.year and rec_b.year) else None
                year_close = year_diff <= 1 if year_diff is not None else False

                # Require high title similarity (>= 85) AND at least one other corroborating field
                if title_sim >= 90 and (author_overlap or year_close):
                    score = round(title_sim / 100.0 * 0.9, 3)
                    evidence = {
                        "matched_by": "fuzzy_multi_field",
                        "title_token_similarity": title_sim,
                        "author_overlap": list(authors_a.intersection(authors_b)),
                        "year_diff": year_diff,
                    }
                    proposals.append(
                        DedupProposal(
                            record_id_a=rec_a.id,
                            record_id_b=rec_b.id,
                            score=score,
                            method_version=METHOD_VERSION,
                            evidence=evidence,
                            status=DedupEdgeStatus.PROPOSED,
                        )
                    )
                    seen_pairs.add(pair_key)
                elif title_sim >= 85 and author_overlap and year_close:
                    score = round(title_sim / 100.0 * 0.85, 3)
                    evidence = {
                        "matched_by": "fuzzy_multi_field",
                        "title_token_similarity": title_sim,
                        "author_overlap": list(authors_a.intersection(authors_b)),
                        "year_diff": year_diff,
                    }
                    proposals.append(
                        DedupProposal(
                            record_id_a=rec_a.id,
                            record_id_b=rec_b.id,
                            score=score,
                            method_version=METHOD_VERSION,
                            evidence=evidence,
                            status=DedupEdgeStatus.PROPOSED,
                        )
                    )
                    seen_pairs.add(pair_key)

    # Sort proposals deterministically by (record_id_a, record_id_b)
    return sorted(proposals, key=lambda p: (p.record_id_a, p.record_id_b))
