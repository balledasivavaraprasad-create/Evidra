import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, FRIENDLY_ERRORS, isServiceUnreachable } from "../api/client";

const respond = (status: number, body: string, contentType = "text/plain") =>
  vi.fn().mockResolvedValue(
    new Response(body, { status, statusText: body, headers: { "content-type": contentType } }),
  );

describe("plain-language API errors", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("explains a network failure as the review service being unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = await api.revisions.list("ws-synth-001").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("SERVICE_UNREACHABLE");
    expect(err.message).toBe(FRIENDLY_ERRORS.unreachable);
    expect(isServiceUnreachable(err)).toBe(true);
  });

  it("turns the dev proxy's bare 'Bad Gateway' into the same message", async () => {
    vi.stubGlobal("fetch", respond(502, "Bad Gateway"));
    const err = await api.revisions.list("ws-synth-001").catch((e) => e);
    expect(err.message).toBe(FRIENDLY_ERRORS.unreachable);
    expect(isServiceUnreachable(err)).toBe(true);
  });

  it("replaces a bare 'Internal Server Error' with an actionable message", async () => {
    vi.stubGlobal("fetch", respond(500, "Internal Server Error"));
    const err = await api.revisions.list("ws-synth-001").catch((e) => e);
    expect(err.code).toBe("SERVER_ERROR");
    expect(err.message).toBe(FRIENDLY_ERRORS.server);
    expect(err.retryable).toBe(true);
    expect(isServiceUnreachable(err)).toBe(false);
  });

  it("keeps the API's own structured message when one is provided", async () => {
    vi.stubGlobal(
      "fetch",
      respond(409, JSON.stringify({ code: "STALE_VERSION_CONFLICT", message: "Updated by another reviewer." }), "application/json"),
    );
    const err = await api.revisions.list("ws-synth-001").catch((e) => e);
    expect(err.code).toBe("STALE_VERSION_CONFLICT");
    expect(err.message).toBe("Updated by another reviewer.");
  });
});
