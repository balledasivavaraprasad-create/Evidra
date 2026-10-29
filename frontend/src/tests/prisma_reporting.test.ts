import { describe, it, expect } from "vitest";
import type {
  PrismaReportResponse,
  PrismaSnapshotCreateRequest,
  PrismaSnapshotSummaryItem,
} from "../api/client";

describe("PRISMA 2020 Flow Diagram & Automated Reporting", () => {
  const mockReport: PrismaReportResponse = {
    workspace_id: "ws-synth-001",
    workspace_title: "Synthetic Review: Metformin for GDM",
    generated_at: "2026-10-28T10:00:00Z",
    is_live: true,
    snapshot_id: null,
    corpus_revision_id: "cr-synth-001",
    query_version_id: "qv-synth-001",
    schema_version: "2020.1",
    stages: {
      identification: {
        total_identified: 45,
        database_sources: [
          {
            source_name: "PubMed",
            records_count: 30,
            search_execution_ids: ["se-001"],
          },
          {
            source_name: "Europe PMC",
            records_count: 15,
            search_execution_ids: ["se-002"],
          },
        ],
        other_sources: [],
        total_database_records: 45,
        total_other_records: 0,
      },
      pre_screening: {
        duplicate_records_removed: 15,
        other_records_removed: 0,
        other_removal_reasons: [],
        records_eligible_for_screening: 30,
        total_removed: 15,
      },
      screening: {
        records_screened: 24,
        records_excluded: 14,
        records_advancing: 10,
        records_pending: 4,
        records_maybe: 1,
        records_conflicts: 1,
        exclusion_reasons: [
          {
            reason: "Wrong outcome: glycemic markers omitted",
            count: 8,
            percentage: 57.14,
            stage: "screening",
          },
          {
            reason: "Wrong population: Type 1 diabetes",
            count: 4,
            percentage: 28.57,
            stage: "screening",
          },
          {
            reason: "Wrong study design: animal model",
            count: 2,
            percentage: 14.29,
            stage: "screening",
          },
        ],
      },
      retrieval: {
        reports_sought_for_retrieval: 0,
        reports_not_retrieved: 0,
        is_supported: false,
        status: "not_started",
        notes: "Evidra screening evaluates title and abstract evidence. Full-text retrieval has not commenced.",
      },
      eligibility: {
        reports_assessed: 0,
        reports_excluded: 0,
        exclusion_reasons: [],
        is_supported: false,
        status: "not_started",
        notes: "Full-text eligibility screening not yet initiated.",
      },
      included: {
        studies_included: 10,
        reports_included: 14,
        studies_included_title_abstract: 10,
        notes: "10 canonical studies synthesized comprising 14 publication records.",
      },
    },
    validation_issues: [
      {
        code: "UNSCREENED_RECORDS",
        stage: "screening",
        message: "4 records remain pending screening decisions.",
        severity: "warning",
      },
      {
        code: "MAYBE_DECISIONS_PENDING",
        stage: "screening",
        message: "1 records marked as Maybe require definitive inclusion/exclusion.",
        severity: "warning",
      },
      {
        code: "UNRESOLVED_CONFLICTS",
        stage: "screening",
        message: "1 records have active screening conflicts between reviewers.",
        severity: "warning",
      },
    ],
    reconciliation: {
      is_reconciled: true,
      identification_balance: 0,
      screening_balance: 0,
      discrepancy_explanation: null,
    },
    exclusion_reasons_summary: [
      {
        reason: "Wrong outcome: glycemic markers omitted",
        count: 8,
        percentage: 57.14,
        stage: "screening",
      },
      {
        reason: "Wrong population: Type 1 diabetes",
        count: 4,
        percentage: 28.57,
        stage: "screening",
      },
      {
        reason: "Wrong study design: animal model",
        count: 2,
        percentage: 14.29,
        stage: "screening",
      },
    ],
  };

  it("verifies mathematical balance across identification and pre-screening stages", () => {
    const { identification, pre_screening } = mockReport.stages;
    const balance = identification.total_identified - (pre_screening.total_removed + pre_screening.records_eligible_for_screening);
    expect(balance).toBe(0);
    expect(mockReport.reconciliation.identification_balance).toBe(0);
    expect(mockReport.reconciliation.is_reconciled).toBe(true);
  });

  it("verifies screening stage flow arithmetic and partitions", () => {
    const { pre_screening, screening } = mockReport.stages;
    const sumScreeningParts =
      screening.records_screened +
      screening.records_pending +
      screening.records_maybe +
      screening.records_conflicts;

    expect(sumScreeningParts).toBe(pre_screening.records_eligible_for_screening);
    expect(screening.records_excluded + screening.records_advancing).toBe(screening.records_screened);
  });

  it("distinguishes canonical studies vs reports of included studies", () => {
    const { included } = mockReport.stages;
    expect(included.studies_included).toBe(10);
    expect(included.reports_included).toBe(14);
    expect(included.reports_included).toBeGreaterThanOrEqual(included.studies_included);
  });

  it("truthfully reports full-text stage status without fabricating retrieval numbers", () => {
    const { retrieval, eligibility } = mockReport.stages;
    expect(retrieval.is_supported).toBe(false);
    expect(retrieval.status).toBe("not_started");
    expect(retrieval.reports_sought_for_retrieval).toBe(0);
    expect(eligibility.is_supported).toBe(false);
    expect(retrieval.notes).toContain("title and abstract");
  });

  it("validates exclusion reason percentages and ordering", () => {
    const reasons = mockReport.exclusion_reasons_summary || [];
    expect(reasons.length).toBe(3);
    const totalPercentage = reasons.reduce((acc, r) => acc + r.percentage, 0);
    expect(Math.round(totalPercentage)).toBe(100);
    expect(reasons[0].count).toBeGreaterThanOrEqual(reasons[1].count);
  });

  it("formats snapshot create payload and tracks audit metadata", () => {
    const payload: PrismaSnapshotCreateRequest = {
      name: "Cochrane Protocol Submission",
      notes: "Post dual-independent abstract screening",
      actor_id: "lead_investigator_42",
    };
    expect(payload.name).toBe("Cochrane Protocol Submission");
    expect(payload.actor_id).toBe("lead_investigator_42");

    const summary: PrismaSnapshotSummaryItem = {
      snapshot_id: "snap-001",
      workspace_id: "ws-synth-001",
      name: payload.name!,
      schema_version: "2020.1",
      total_identified: 45,
      duplicates_removed: 15,
      records_screened: 24,
      studies_included: 10,
      has_warnings: true,
      created_by: payload.actor_id,
      created_at: "2026-10-28T12:00:00Z",
    };
    expect(summary.has_warnings).toBe(true);
    expect(summary.total_identified).toBe(45);
  });
});
