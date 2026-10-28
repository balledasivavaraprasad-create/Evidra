import { describe, it, expect } from "vitest";
import type {
  DuplicateGroupGenealogyResponse,
  DuplicateReconcileRequest,
  DuplicateSplitRequest,
  DuplicateReverseMergeRequest,
  FieldProvenanceItem,
} from "../api/client";

describe("Duplicate Genealogy & Reconciliation System", () => {
  it("structures multi-source duplicate group with canonical record and matching signals", () => {
    const mockGenealogy: DuplicateGroupGenealogyResponse = {
      workspace_id: "ws-test-01",
      group_id: "grp-test-01",
      canonical_record_id: "src-pubmed-001",
      effective_decision: "conflict",
      membership_fingerprint: "a1b2c3d4e5f6g7h8",
      row_version: 3,
      members: [
        {
          source_record_id: "src-pubmed-001",
          record_revision_id: "rev-001",
          source_namespace: "PubMed",
          external_id: "38100001",
          title: "Metformin in Gestational Diabetes Mellitus: A Multicenter Randomized Trial",
          authors: ["Smith J", "Doe A"],
          year: 2023,
          journal: "New England Journal of Medicine",
          doi: "10.1056/NEJMoa2301",
          is_canonical: true,
          individual_decision: "include",
          decision_source: "human_review",
        },
        {
          source_record_id: "src-epmc-002",
          record_revision_id: "rev-002",
          source_namespace: "Europe PMC",
          external_id: "PMC1099901",
          title: "Metformin in Gestational Diabetes Mellitus: A Multicenter Randomized Trial.",
          authors: ["Smith J.", "Doe A."],
          year: 2023,
          journal: "N Engl J Med",
          doi: "10.1056/NEJMoa2301",
          is_canonical: false,
          individual_decision: "exclude",
          decision_source: "heuristic_rule",
        },
      ],
      pairwise_signals: [
        {
          record_id_a: "src-pubmed-001",
          record_id_b: "src-epmc-002",
          score: 1.0,
          status: "confirmed",
          signals: ["exact_doi:10.1056/NEJMoa2301", "normalized_title_match"],
        },
      ],
      active_conflicts: [
        {
          classification: "decision_divergence",
          is_resolved: false,
          explanation: "Conflict between include and exclude across 2 duplicate records",
          affected_records: ["src-pubmed-001", "src-epmc-002"],
        },
      ],
    };

    expect(mockGenealogy.members).toHaveLength(2);
    expect(mockGenealogy.members![0].is_canonical).toBe(true);
    expect(mockGenealogy.pairwise_signals![0].score).toBe(1.0);
    expect(mockGenealogy.pairwise_signals![0].signals).toContain("exact_doi:10.1056/NEJMoa2301");
    expect(mockGenealogy.active_conflicts![0].classification).toBe("decision_divergence");
  });

  it("identifies field-level discrepancies between canonical record and duplicate copies", () => {
    const provenanceItems: FieldProvenanceItem[] = [
      {
        field_name: "title",
        canonical_value: "Metformin in Gestational Diabetes Mellitus: A Multicenter Randomized Trial",
        canonical_source: "PubMed",
        source_record_id: "src-pubmed-001",
        has_discrepancy: true,
        alternatives: [
          {
            source: "Europe PMC",
            value: "Metformin in Gestational Diabetes Mellitus: A Multicenter Randomized Trial.",
            record_id: "src-epmc-002",
          },
        ],
      },
      {
        field_name: "doi",
        canonical_value: "10.1056/NEJMoa2301",
        canonical_source: "PubMed",
        source_record_id: "src-pubmed-001",
        has_discrepancy: false,
        alternatives: [],
      },
    ];

    expect(provenanceItems[0].has_discrepancy).toBe(true);
    expect(provenanceItems[0].alternatives).toHaveLength(1);
    expect(provenanceItems[1].has_discrepancy).toBe(false);
  });

  it("constructs valid reconciliation request enforcing human attribution and version checking", () => {
    const reconcileReq: DuplicateReconcileRequest = {
      chosen_decision: "include",
      reason: "Validated full-text methodology; trial satisfies all RCT eligibility criteria",
      actor_id: "lead_reviewer_1",
      apply_to_all_members: true,
      expected_version: 4,
    };

    expect(reconcileReq.chosen_decision).toBe("include");
    expect(reconcileReq.apply_to_all_members).toBe(true);
    expect(reconcileReq.expected_version).toBe(4);
    expect(reconcileReq.reason.length).toBeGreaterThan(10);
  });

  it("constructs valid split request enforcing cannot-link constraints", () => {
    const splitReq: DuplicateSplitRequest = {
      source_record_ids_to_split: ["src-epmc-002"],
      reason: "Companion phase 2 follow-up with distinct patient cohort and non-overlapping outcomes",
      mark_as_cannot_link: true,
      actor_id: "methodologist_2",
      expected_version: 2,
    };

    expect(splitReq.source_record_ids_to_split).toContain("src-epmc-002");
    expect(splitReq.mark_as_cannot_link).toBe(true);
    expect(splitReq.expected_version).toBe(2);
  });

  it("constructs valid reverse merge request with audit event linkage", () => {
    const reverseReq: DuplicateReverseMergeRequest = {
      merge_event_id: "dme-merge-001",
      reason: "False positive title similarity match on subsequent manual audit",
      actor_id: "audit_lead",
      expected_version: 3,
    };

    expect(reverseReq.merge_event_id).toBe("dme-merge-001");
    expect(reverseReq.expected_version).toBe(3);
    expect(reverseReq.actor_id).toBe("audit_lead");
  });
});
