import { describe, it, expect } from "vitest";
import { ApiError } from "../api/client";
import { MOCK_GROUPS } from "../api/fixtures";

describe("Frontend API Client and Contracts", () => {
  it("creates ApiError from structured ErrorEnvelope", () => {
    const error = ApiError.fromEnvelope(409, {
      code: "STALE_VERSION_CONFLICT",
      message: "The record was updated by another reviewer.",
      retryable: false,
      details: [{ field: "expected_version", message: "Version mismatch", type: "value_error" }],
    });

    expect(error.status).toBe(409);
    expect(error.code).toBe("STALE_VERSION_CONFLICT");
    expect(error.message).toBe("The record was updated by another reviewer.");
    expect(error.retryable).toBe(false);
    expect(error.details).toHaveLength(1);
    expect(error.details?.[0].field).toBe("expected_version");
  });

  it("handles fallback envelope values gracefully", () => {
    const error = ApiError.fromEnvelope(500, {});
    expect(error.status).toBe(500);
    expect(error.code).toBe("UNKNOWN_ERROR");
    expect(error.message).toBe("An unexpected error occurred");
    expect(error.retryable).toBe(false);
  });

  it("provides valid mock fixtures adhering to domain schema", () => {
    expect(MOCK_GROUPS.length).toBeGreaterThanOrEqual(3);

    const includedGroup = MOCK_GROUPS.find((g) => g.effective_status === "include");
    expect(includedGroup).toBeDefined();
    expect(includedGroup?.representative_revision.title).toContain("metformin");
    expect(includedGroup?.representative_revision.doi).toBe("10.1056/nejmoa2024001");

    const conflictGroup = MOCK_GROUPS.find((g) => g.has_conflict);
    expect(conflictGroup).toBeDefined();
    expect(conflictGroup?.effective_status).toBe("conflict");
  });
});
