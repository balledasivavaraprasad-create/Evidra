import { describe, it, expect, vi } from "vitest";
import { api, type CorpusDiffResponse, type CorpusRevisionResponse } from "../api/client";

describe("Level 2 History, Diff, and Restore Client Unit Tests", () => {
  it("formats and structures corpus diff request correctly", async () => {
    const mockDiff: CorpusDiffResponse = {
      base_revision_id: "rev-base",
      target_revision_id: "rev-target",
      added_groups: 2,
      removed_groups: 1,
      merged_groups: 1,
      split_groups: 0,
      changed_decisions: 1,
      conflicts_count: 0,
      added_records: 3,
      removed_records: 1,
      retained_records: 10,
      representative_changes: 0,
      invalidation_fingerprint: "sha256-fingerprint-test",
      added_record_ids: ["rec-1", "rec-2", "rec-3"],
      removed_record_ids: ["rec-4"],
    };

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementationOnce(() =>
      Promise.resolve(new Response(JSON.stringify(mockDiff), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }))
    );

    const diff = await api.revisions.getDiff("rev-target", "rev-base");

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/revisions/rev-target/diff?base_revision_id=rev-base",
      expect.objectContaining({
        headers: expect.objectContaining({ Accept: "application/json" }),
      })
    );

    expect(diff.added_records).toBe(3);
    expect(diff.removed_records).toBe(1);
    expect(diff.invalidation_fingerprint).toBe("sha256-fingerprint-test");
    expect(diff.merged_groups).toBe(1);

    fetchSpy.mockRestore();
  });

  it("submits snapshot restore payload with exact_snapshot mode", async () => {
    const mockRestored: CorpusRevisionResponse = {
      id: "rev-restored-1",
      workspace_id: "ws-100",
      parent_id: "rev-prior",
      criteria_version_id: "crit-1",
      dedup_version: "dedup:v1.0.0",
      state: "published",
      published_at: "2026-10-28T00:00:00Z",
      decision_seq_cutoff: null,
      fingerprint: "fingerprint-restored",
      group_count: 5,
      record_count: 8,
    };

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementationOnce(() =>
      Promise.resolve(new Response(JSON.stringify(mockRestored), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }))
    );

    const restored = await api.revisions.restore("ws-100", {
      snapshot_id: "rev-target-snapshot",
      mode: "exact_snapshot",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/workspaces/ws-100/restore?snapshot_id=rev-target-snapshot",
      expect.objectContaining({
        method: "POST",
      })
    );

    expect(restored.id).toBe("rev-restored-1");
    expect(restored.record_count).toBe(8);
    expect(restored.group_count).toBe(5);

    fetchSpy.mockRestore();
  });

  it("submits conflict resolution with mandatory rationale", async () => {
    const mockResolveResponse = {
      id: "ev-resolved-1",
      workspace_id: "ws-100",
      group_id: "grp-conflict-1",
      event_type: "conflict_resolution",
      sequence: 12,
      actor_id: "reviewer-expert",
      created_at: "2026-10-28T00:00:00Z",
      payload_json: JSON.stringify({ chosen_status: "include", reason: "Phase 3 clinical confirmation" }),
    };

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementationOnce(() =>
      Promise.resolve(new Response(JSON.stringify(mockResolveResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }))
    );

    const result = await api.conflicts.resolve("conf-grp-1", {
      chosen_status: "include",
      reason: "Phase 3 clinical confirmation",
      expected_version: 2,
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/conflicts/conf-grp-1/resolve",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          chosen_status: "include",
          reason: "Phase 3 clinical confirmation",
          expected_version: 2,
        }),
      })
    );

    expect(result.id).toBe("ev-resolved-1");
    expect(result.event_type).toBe("conflict_resolution");

    fetchSpy.mockRestore();
  });
});
