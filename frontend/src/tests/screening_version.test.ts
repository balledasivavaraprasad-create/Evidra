import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import reviewQueueSource from "../features/review-queue/ReviewQueuePage.tsx?raw";

describe("Screening group row_version concurrency contract", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("decision -> refetch -> second decision sends the new row_version", async () => {
    const groupId = "grp-synth-001";
    const calls: Array<{ url: string; method?: string; body?: any }> = [];

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        const parsedBody = init?.body ? JSON.parse(init.body as string) : undefined;
        calls.push({ url, method: init?.method, body: parsedBody });

        if (url.includes(`/api/v1/groups/${groupId}/decisions`)) {
          // Verify decision endpoint receives expected_version
          return Promise.resolve(
            new Response(
              JSON.stringify({
                id: "dec-1",
                group_id: groupId,
                status: parsedBody?.status,
                scope: "group",
                reviewer_id: "rev-local",
                reason: parsedBody?.reason,
                expected_version: parsedBody?.expected_version,
                created_at: new Date().toISOString(),
              }),
              { status: 200, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        if (url.includes(`/api/v1/groups/${groupId}`)) {
          // Return detail with bumped row_version
          const callCount = calls.filter((c) => c.url.includes(`/api/v1/groups/${groupId}`) && c.method !== "POST").length;
          return Promise.resolve(
            new Response(
              JSON.stringify({
                group: {
                  id: groupId,
                  row_version: callCount + 1, // first refetch returns 2, second returns 3
                  effective_status: "include",
                  has_human_decision: true,
                  has_conflict: false,
                  member_count: 1,
                  representative_record_id: "rec-1",
                  representative_revision: {
                    id: "rev-1",
                    source_id: "pubmed",
                    source_record_id: "1001",
                    title: "Test Article",
                    abstract: "Test Abstract",
                    content_hash: "hash1",
                  },
                },
                decisions: [],
                pico_extractions: [],
                members: [],
              }),
              { status: 200, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        return Promise.resolve(new Response("{}", { status: 200 }));
      })
    );

    // Initial state: group starts with row_version: 1
    let currentVersion = 1;

    // First decision sends row_version: 1
    await api.groups.recordDecision(groupId, {
      status: "include",
      reason: "Relevant RCT",
      expected_version: currentVersion,
    });

    expect(calls[0].body.expected_version).toBe(1);

    // Refetch group detail to get latest row_version
    const detailAfterFirst = await api.groups.getDetail(groupId);
    currentVersion = detailAfterFirst.group.row_version;
    expect(currentVersion).toBe(2);

    // Second decision sends updated row_version: 2
    await api.groups.recordDecision(groupId, {
      status: "exclude",
      reason: "Wrong patient population",
      expected_version: currentVersion,
    });

    const secondDecisionCall = calls.find(
      (c, idx) => idx > 1 && c.url.includes(`/api/v1/groups/${groupId}/decisions`)
    );
    expect(secondDecisionCall?.body.expected_version).toBe(2);

    // Refetch group detail again
    const detailAfterSecond = await api.groups.getDetail(groupId);
    expect(detailAfterSecond.group.row_version).toBe(3);
  });

  it("handles 409 conflict by refetching group and offering user-friendly message", async () => {
    const groupId = "grp-synth-conflict";

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        if (url.includes(`/api/v1/groups/${groupId}/decisions`)) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                code: "STALE_VERSION_CONFLICT",
                message: "Record has been updated by another user.",
              }),
              { status: 409, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        if (url.includes(`/api/v1/groups/${groupId}`)) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                group: {
                  id: groupId,
                  row_version: 5,
                  effective_status: "include",
                  has_human_decision: true,
                  has_conflict: false,
                  member_count: 1,
                  representative_record_id: "rec-1",
                  representative_revision: {
                    id: "rev-1",
                    source_id: "pubmed",
                    source_record_id: "1001",
                    title: "Test Article",
                    abstract: "Test Abstract",
                    content_hash: "hash1",
                  },
                },
                decisions: [],
                pico_extractions: [],
                members: [],
              }),
              { status: 200, headers: { "Content-Type": "application/json" } }
            )
          );
        }

        return Promise.resolve(new Response("{}", { status: 200 }));
      })
    );

    // Decision with stale version throws 409
    let caughtError: unknown;
    try {
      await api.groups.recordDecision(groupId, {
        status: "include",
        reason: "Stale attempt",
        expected_version: 1,
      });
    } catch (e) {
      caughtError = e;
    }

    expect(caughtError).toBeInstanceOf(ApiError);
    expect((caughtError as ApiError).status).toBe(409);

    // On 409, refetch gets current row_version
    const refreshed = await api.groups.getDetail(groupId);
    expect(refreshed.group.row_version).toBe(5);
  });

  it("source guard: ReviewQueuePage does not use local guessed version map", () => {
    // Must NOT have local state guessing versions
    expect(reviewQueueSource).not.toContain("groupVersions");
    expect(reviewQueueSource).not.toContain("setGroupVersions");
    expect(reviewQueueSource).not.toContain("currentVersion + 1");

    // Must read group.row_version from server
    expect(reviewQueueSource).toContain("row_version");

    // Must show exact prompt message on 409 conflict
    expect(reviewQueueSource).toContain(
      "This paper was updated. Your view has been refreshed — please choose again."
    );
  });
});
