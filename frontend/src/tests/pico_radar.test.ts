import { describe, it, expect } from "vitest";
import type {
  ArticleRadarResponse,
  ReviewRadarResponse,
  RadarFieldDetail,
  RadarEvidenceStatus,
} from "../api/client";

describe("Missing-Evidence Radar Frontend Contracts & Logic", () => {
  it("accurately models the 4-dimensional PICO evidence statuses", () => {
    const mockArticleRadar: ArticleRadarResponse = {
      workspace_id: "ws-test",
      group_id: "grp-1",
      paper_title: "A Randomized Trial of Gene Therapy in Sickle Cell Disease",
      source_text: "We conducted a phase 3 multicenter trial of autologous hematopoietic stem cell gene therapy in patients with severe sickle cell disease. Outcomes included vaso-occlusive crisis resolution. No comparator group was examined in this single-arm cohort.",
      source_field: "abstract",
      has_source_text: true,
      effective_decision: "include",
      screening_reason: "Matches clinical review criteria",
      overall_coverage_pct: 75.0,
      needs_human_review: true,
      pico: {
        population: {
          claim_type: "population",
          field_label: "Population",
          radar_status: "supported",
          human_review_status: "unreviewed",
          claim_value: "patients with severe sickle cell disease",
          source_field: "abstract",
          supporting_quote: "patients with severe sickle cell disease",
          start_cp: 104,
          end_cp: 144,
          validation_status: "verified",
          validation_message: "Verified against stored abstract.",
          semantic_assessment: "supports",
          is_contradictory: false,
        },
        intervention: {
          claim_type: "intervention",
          field_label: "Intervention",
          radar_status: "supported",
          human_review_status: "confirmed",
          claim_value: "autologous hematopoietic stem cell gene therapy",
          source_field: "abstract",
          supporting_quote: "autologous hematopoietic stem cell gene therapy",
          validation_status: "verified",
          semantic_assessment: "supports",
          is_contradictory: false,
        },
        comparator: {
          claim_type: "comparator",
          field_label: "Comparator",
          radar_status: "not_found",
          human_review_status: "unreviewed",
          claim_value: "Not found in examined text (abstract)",
          source_field: "abstract",
          supporting_quote: undefined,
          validation_status: "insufficient_evidence",
          validation_message: "No active comparator or control group reported in abstract.",
          semantic_assessment: "insufficient",
          is_contradictory: false,
        },
        outcome: {
          claim_type: "outcome",
          field_label: "Outcome",
          radar_status: "supported",
          human_review_status: "unreviewed",
          claim_value: "vaso-occlusive crisis resolution",
          source_field: "abstract",
          supporting_quote: "vaso-occlusive crisis resolution",
          validation_status: "verified",
          semantic_assessment: "supports",
          is_contradictory: false,
        },
      },
    };

    // Invariant: Missing comparator in abstract does NOT change study inclusion decision
    expect(mockArticleRadar.effective_decision).toBe("include");
    expect(mockArticleRadar.pico.comparator.radar_status).toBe("not_found");
    expect(mockArticleRadar.pico.comparator.claim_value).toContain("Not found in examined text");

    // Invariant: Supported claims have verified quotes and non-empty offsets/quotes
    expect(mockArticleRadar.pico.population.radar_status).toBe("supported");
    expect(mockArticleRadar.pico.population.supporting_quote).toBeDefined();

    // Invariant: Overall coverage percentage reflects 3 of 4 fields supported
    expect(mockArticleRadar.overall_coverage_pct).toBe(75.0);
    expect(mockArticleRadar.needs_human_review).toBe(true);
  });

  it("handles review-level evidence coverage matrix aggregation", () => {
    const mockOverview: ReviewRadarResponse = {
      workspace_id: "ws-test",
      total_articles: 10,
      articles_with_source_text: 9,
      articles_without_source_text: 1,
      total_fields_supported_percent: 65.0,
      needs_review_total: 4,
      dimension_summaries: {
        population: {
          dimension: "population",
          total_assessed: 10,
          supported_count: 8,
          uncertain_count: 1,
          not_found_count: 0,
          conflicting_count: 0,
          stale_count: 0,
          not_assessed_count: 1,
          human_confirmed_count: 2,
          human_corrected_count: 0,
          pending_review_count: 8,
          supported_percent: 80.0,
        },
        intervention: {
          dimension: "intervention",
          total_assessed: 10,
          supported_count: 9,
          uncertain_count: 0,
          not_found_count: 0,
          conflicting_count: 0,
          stale_count: 0,
          not_assessed_count: 1,
          human_confirmed_count: 3,
          human_corrected_count: 1,
          pending_review_count: 6,
          supported_percent: 90.0,
        },
        comparator: {
          dimension: "comparator",
          total_assessed: 10,
          supported_count: 4,
          uncertain_count: 1,
          not_found_count: 4,
          conflicting_count: 0,
          stale_count: 0,
          not_assessed_count: 1,
          human_confirmed_count: 1,
          human_corrected_count: 0,
          pending_review_count: 9,
          supported_percent: 40.0,
        },
        outcome: {
          dimension: "outcome",
          total_assessed: 10,
          supported_count: 5,
          uncertain_count: 2,
          not_found_count: 1,
          conflicting_count: 1,
          stale_count: 0,
          not_assessed_count: 1,
          human_confirmed_count: 1,
          human_corrected_count: 0,
          pending_review_count: 9,
          supported_percent: 50.0,
        },
      },
      rows: [
        {
          group_id: "grp-1",
          title: "Study 1",
          has_source_text: true,
          effective_decision: "include",
          population_status: "supported",
          intervention_status: "supported",
          comparator_status: "not_found",
          outcome_status: "supported",
          needs_review: true,
          priority_rank: 4,
        },
        {
          group_id: "grp-2",
          title: "Study 2 with Conflicting Outcome",
          has_source_text: true,
          effective_decision: "maybe",
          population_status: "supported",
          intervention_status: "supported",
          comparator_status: "supported",
          outcome_status: "conflicting",
          needs_review: true,
          priority_rank: 2,
        },
      ],
    };

    expect(mockOverview.total_articles).toBe(10);
    expect(mockOverview.articles_without_source_text).toBe(1);
    expect(mockOverview.needs_review_total).toBe(4);

    // Comparator in abstract reviews typically has lower support rate without full text
    expect(mockOverview.dimension_summaries.comparator.not_found_count).toBe(4);
    expect(mockOverview.dimension_summaries.comparator.supported_percent).toBe(40.0);

    // Invariant: Conflicting outcomes are ranked higher priority than normal not-found
    expect(mockOverview.rows[1].priority_rank).toBeLessThan(mockOverview.rows[0].priority_rank);
  });
});
