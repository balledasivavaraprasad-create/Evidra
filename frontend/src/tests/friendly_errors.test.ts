import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, AUTH_REQUIRED_EVENT, FRIENDLY_ERRORS, isServiceUnreachable } from "../api/client";

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

  it("asks the app to show the password screen when the session is missing or expired", async () => {
    const listener = vi.fn();
    const fakeWindow = new EventTarget();
    vi.stubGlobal("window", fakeWindow);
    fakeWindow.addEventListener(AUTH_REQUIRED_EVENT, listener);
    vi.stubGlobal(
      "fetch",
      respond(401, JSON.stringify({ code: "AUTH_REQUIRED", message: "Enter the site password to continue." }), "application/json"),
    );
    const err = await api.revisions.list("ws-synth-001").catch((e) => e);
    fakeWindow.removeEventListener(AUTH_REQUIRED_EVENT, listener);
    expect(err.code).toBe("AUTH_REQUIRED");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("does not trigger the sign-in prompt for wrong credentials at login", async () => {
    const listener = vi.fn();
    const fakeWindow = new EventTarget();
    vi.stubGlobal("window", fakeWindow);
    fakeWindow.addEventListener(AUTH_REQUIRED_EVENT, listener);
    vi.stubGlobal(
      "fetch",
      respond(401, JSON.stringify({ code: "INVALID_CREDENTIALS", message: "Wrong email or password." }), "application/json"),
    );
    const err = await api.auth.login({ email: "ada@example.com", password: "nope" }).catch((e) => e);
    fakeWindow.removeEventListener(AUTH_REQUIRED_EVENT, listener);
    expect(err.code).toBe("INVALID_CREDENTIALS");
    expect(err.message).toBe("Wrong email or password.");
    expect(listener).not.toHaveBeenCalled();
  });
});
