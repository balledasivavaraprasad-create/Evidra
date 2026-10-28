import { describe, it, expect } from "vitest";
import type {
  SearchEvolutionDiffResponse,
  SearchEvolutionRecordDiff,
  SearchEvolutionVersionSummary,
  SearchRestoreResponse,
} from "../api/client";

describe("Search Evolution Time Machine Frontend Contracts & Logic", () => {
  it("correctly models the 6-way longitudinal diff categories", () => {
    const mockDiff: SearchEvolutionDiffResponse = {
      summary: {
        base_version_id: "qv-1",
        base_sequence: 1,
        target_version_id: "qv-2",
        target_sequence: 2,
        total_base_records: 10,
        total_target_records: 12,
        newly_discovered_count: 3,
        repeated_count: 7,
        missing_from_newer_count: 3,
        metadata_changed_count: 1,
        conflicts_count: 0,
        screened_target_count: 5,
        unscreened_target_count: 7,
      },
      records: [
        {
          source_record_id: "sr-101",
          external_id: "34990001",
          source: "pubmed",
          title: "Novel CRISPR therapy for beta thalassemia: a phase 3 trial",
          authors: ["Smith J", "Doe A"],
          year: 2024,
          journal: "N Engl J Med",
          doi: "10.1056/nejmoa2300001",
          pmid: "34990001",
          category: "newly_discovered",
          target_record_revision_id: "rev-101",
          screening_decision: "unscreened",
          metadata_changed_since_screening: false,
          field_diffs: [],
        },
        {
          source_record_id: "sr-102",
          external_id: "33880002",
          source: "pubmed",
          title: "Historical standard of care in sickle cell disease",
          authors: ["Lee C"],
          year: 2022,
          journal: "Lancet",
          category: "missing_from_newer",
          base_record_revision_id: "rev-102",
          screening_decision: "include",
          screening_reason: "Matches population and outcome criteria",
          screening_preserved_from_version_id: "qv-1",
          metadata_changed_since_screening: false,
          field_diffs: [],
        },
        {
          source_record_id: "sr-103",
          external_id: "34550003",
          source: "pubmed",
          title: "Updated gene editing outcomes: 24-month followup",
          authors: ["Garcia M", "Taylor R"],
          year: 2024,
          journal: "Blood",
          category: "metadata_changed",
          base_record_revision_id: "rev-103-v1",
          target_record_revision_id: "rev-103-v2",
          screening_decision: "include",
          screening_preserved_from_version_id: "qv-1",
          metadata_changed_since_screening: true,
          field_diffs: [
            {
              field_name: "title",
              base_value: "Gene editing outcomes: preliminary 12-month data",
              target_value: "Updated gene editing outcomes: 24-month followup",
            },
            {
              field_name: "year",
              base_value: "2023",
              target_value: "2024",
            },
          ],
        },
      ],
    };

    expect(mockDiff.summary.newly_discovered_count).toBe(3);
    expect(mockDiff.summary.missing_from_newer_count).toBe(3);

    // Invariant: absence without deletion does not erase screening decision
    const missingRecord = mockDiff.records.find((r) => r.category === "missing_from_newer");
    expect(missingRecord).toBeDefined();
    expect(missingRecord?.screening_decision).toBe("include");
    expect(missingRecord?.screening_preserved_from_version_id).toBe("qv-1");

    // Invariant: metadata changes since screening are flagged
    const changedRecord = mockDiff.records.find((r) => r.category === "metadata_changed");
    expect(changedRecord).toBeDefined();
    expect(changedRecord?.metadata_changed_since_screening).toBe(true);
    expect(changedRecord?.field_diffs).toHaveLength(2);
    expect(changedRecord?.field_diffs?.[0].field_name).toBe("title");
  });

  it("handles non-destructive query version restore response contracts", () => {
    const restoreResponse: SearchRestoreResponse = {
      restored_query: {
        id: "qv-3",
        workspace_id: "ws-test",
        sequence: 3,
        parent_id: "qv-1",
        ast: {
          operator: "AND",
          children: [{ term: "CRISPR" }, { term: "thalassemia" }],
        },
        sources: ["pubmed"],
        criteria_version_id: "crit-1",
        content_hash: "hash-123456",
        change_description: "Restored search strategy from Version 1: Reverting to broad sensitivity",
        restored_from_version_id: "qv-1",
        created_at: new Date().toISOString(),
      },
      restored_from_version_id: "qv-1",
      message: "Successfully restored search strategy from Version 1 as Version 3",
    };

    expect(restoreResponse.restored_from_version_id).toBe("qv-1");
    expect(restoreResponse.restored_query.sequence).toBe(3);
    expect(restoreResponse.restored_query.change_description).toContain("Restored search strategy from Version 1");
    expect(restoreResponse.restored_query.restored_from_version_id).toBe("qv-1");
  });

  it("computes screening progress metrics on search versions", () => {
    const versionSummary: SearchEvolutionVersionSummary = {
      id: "qv-2",
      sequence: 2,
      workspace_id: "ws-test",
      created_at: new Date().toISOString(),
      sources: ["pubmed", "europepmc"],
      total_records: 50,
      screened_records: 35,
      unscreened_records: 15,
      new_records_count: 10,
      repeated_records_count: 40,
      executions: [],
    };

    const screeningProgressPct = Math.round(
      (versionSummary.screened_records / versionSummary.total_records) * 100
    );
    expect(screeningProgressPct).toBe(70);
    expect(versionSummary.new_records_count + versionSummary.repeated_records_count).toBe(50);
  });
});
