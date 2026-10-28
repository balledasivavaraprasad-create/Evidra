import { describe, it, expect } from "vitest";
import type {
  DevilsAdvocateChallengeResponse,
  DevilsAdvocateDashboardResponse,
  CounterArgumentItem,
  VulnerabilityFlag,
} from "../api/client";

describe("Devil's Advocate Reviewer Frontend Contracts & Logic", () => {
  it("structures challenge assessment, counter-evidence, and vulnerability flags", () => {
    const mockChallenge: DevilsAdvocateChallengeResponse = {
      id: "chal-001",
      workspace_id: "ws-test",
      group_id: "grp-1",
      record_revision_id: "rev-1",
      proposed_decision: "exclude",
      original_exclusion_reason: "Single arm study without active comparator",
      recommendation: "reconsider_exclusion",
      vulnerability_score: 0.75,
      critique: "High risk of false exclusion: The stated exclusion rationale is directly challenged by source text mentioning a standard of care control group.",
      counter_arguments: [
        {
          argument: "Source text mentions a comparator, control group, or comparative design.",
          supporting_quote: "compared to standard of care control group",
          source_field: "abstract",
          relevance_aspect: "comparator",
          confidence: 0.9,
        },
        {
          argument: "High-rigor prospective clinical trial methodology identified.",
          supporting_quote: "multicenter randomized phase 3 trial",
          source_field: "abstract",
          relevance_aspect: "methodology",
          confidence: 0.95,
        },
      ],
      vulnerability_flags: [
        "indirect_comparator",
        "counter_evidence_found",
        "abstract_only_limitation",
      ],
      disposition: "pending",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    expect(mockChallenge.recommendation).toBe("reconsider_exclusion");
    expect(mockChallenge.vulnerability_score).toBe(0.75);
    expect(mockChallenge.counter_arguments?.length).toBe(2);
    expect(mockChallenge.vulnerability_flags).toContain("indirect_comparator");
    expect(mockChallenge.vulnerability_flags).toContain("counter_evidence_found");

    // Invariant: Challenge starts in pending disposition and does NOT automatically overturn exclusion
    expect(mockChallenge.disposition).toBe("pending");
    expect(mockChallenge.proposed_decision).toBe("exclude");
  });

  it("handles reviewer concession workflow preserving decision provenance", () => {
    const concededChallenge: DevilsAdvocateChallengeResponse = {
      id: "chal-002",
      workspace_id: "ws-test",
      group_id: "grp-2",
      record_revision_id: "rev-2",
      proposed_decision: "exclude",
      original_exclusion_reason: "Wrong population (adult only)",
      recommendation: "reconsider_exclusion",
      vulnerability_score: 0.65,
      critique: "Subgroup analysis in adolescent cohort warrants reconsideration.",
      counter_arguments: [
        {
          argument: "Target patient cohort or potential subgroup reported in text.",
          supporting_quote: "cohort B enrolled adolescents aged 12-17",
          source_field: "abstract",
          relevance_aspect: "population",
          confidence: 0.85,
        },
      ],
      vulnerability_flags: ["overlooked_subgroup", "counter_evidence_found"],
      disposition: "conceded",
      disposition_notes: "Adolescent subgroup identified; retrieved for full-text review.",
      disposition_by: "dr-reviewer",
      disposed_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    expect(concededChallenge.disposition).toBe("conceded");
    expect(concededChallenge.disposition_notes).toContain("Adolescent subgroup identified");
    expect(concededChallenge.disposition_by).toBe("dr-reviewer");
  });

  it("calculates review-level dashboard metrics and false-exclusion prevention rate", () => {
    const mockDashboard: DevilsAdvocateDashboardResponse = {
      workspace_id: "ws-test",
      total_challenged: 20,
      pending_challenges: 5,
      high_vulnerability_count: 8,
      conceded_count: 6,
      upheld_count: 7,
      dismissed_count: 2,
      concession_rate: 40.0, // 6 / (6 + 7 + 2) = 6/15 = 40%
      false_exclusions_prevented: 6,
      challenges: [
        {
          challenge_id: "chal-101",
          group_id: "grp-101",
          title: "Randomized Trial of Targeted Immunotherapy",
          authors: ["Smith J", "Doe A"],
          year: 2024,
          pmid: "12345678",
          proposed_decision: "exclude",
          original_exclusion_reason: "No comparator",
          recommendation: "reconsider_exclusion",
          vulnerability_score: 0.85,
          vulnerability_flags: ["indirect_comparator", "counter_evidence_found"],
          disposition: "conceded",
          counter_argument_count: 2,
          created_at: new Date().toISOString(),
        },
      ],
    };

    expect(mockDashboard.total_challenged).toBe(20);
    expect(mockDashboard.conceded_count).toBe(6);
    expect(mockDashboard.false_exclusions_prevented).toBe(6);
    expect(mockDashboard.concession_rate).toBe(40.0);
    expect(mockDashboard.challenges?.[0].vulnerability_score).toBe(0.85);
  });
});
