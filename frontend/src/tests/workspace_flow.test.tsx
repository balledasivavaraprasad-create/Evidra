import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";
import {
  DEMO_WORKSPACE_ID,
  forgetWorkspaceId,
  getRememberedWorkspaceId,
  reconcileRememberedWorkspace,
  rememberWorkspaceId,
} from "../context/currentWorkspace";
import { loadSavedCriteria } from "../features/search/savedCriteria";
import { QueryBuilder, SAVE_QUESTION_HINT } from "../features/search/QueryBuilder";
import { WorkspaceNotFound } from "../components/WorkspaceGuard";
import pageSource from "../features/search/QueryBuilderPage.tsx?raw";
import builderSource from "../features/search/QueryBuilder.tsx?raw";

const KEY = "evidra-current-workspace";

function stubStorage(initial: Record<string, string> = {}) {
  const store = new Map(Object.entries(initial));
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
  });
  return store;
}

const json = (status: number, body: unknown) =>
  vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }),
  );

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("remembered review is checked against the server's list", () => {
  it("keeps a remembered review the server still has", () => {
    const store = stubStorage({ [KEY]: "ws-mine" });
    expect(reconcileRememberedWorkspace(["ws-other", "ws-mine"])).toBe("ws-mine");
    expect(store.get(KEY)).toBe("ws-mine");
  });

  it("clears a remembered review that is gone and falls back to the demo", () => {
    const store = stubStorage({ [KEY]: "ws-wiped" });
    expect(reconcileRememberedWorkspace(["ws-other"])).toBe(DEMO_WORKSPACE_ID);
    expect(store.has(KEY)).toBe(false);
    expect(getRememberedWorkspaceId()).toBe(DEMO_WORKSPACE_ID);
  });

  it("clears it when the server has no reviews at all (empty database after a restart)", () => {
    const store = stubStorage({ [KEY]: "ws-wiped" });
    expect(reconcileRememberedWorkspace([])).toBe(DEMO_WORKSPACE_ID);
    expect(store.has(KEY)).toBe(false);
  });

  it("uses the demo when nothing was remembered", () => {
    stubStorage();
    expect(reconcileRememberedWorkspace(["ws-other"])).toBe(DEMO_WORKSPACE_ID);
  });

  it("falls back to the demo when storage is unavailable", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => {
        throw new Error("blocked");
      },
    });
    expect(reconcileRememberedWorkspace(["ws-mine"])).toBe(DEMO_WORKSPACE_ID);
    expect(() => rememberWorkspaceId("ws-mine")).not.toThrow();
    expect(() => forgetWorkspaceId()).not.toThrow();
  });

  it("forgetWorkspaceId(id) only forgets that exact review", () => {
    const store = stubStorage({ [KEY]: "ws-a" });
    forgetWorkspaceId("ws-b");
    expect(store.get(KEY)).toBe("ws-a");
    forgetWorkspaceId("ws-a");
    expect(store.has(KEY)).toBe(false);
  });
});

describe("loading the demo's saved review question", () => {
  const saved = {
    id: "crit-synth-001",
    workspace_id: DEMO_WORKSPACE_ID,
    sequence: 1,
    question: "In adults with type 2 diabetes, how does metformin affect HbA1c?",
    pico_description: { P: "Adults with T2D", I: "Metformin", C: "Placebo", O: "HbA1c" },
    criteria: [],
    content_hash: "h",
    created_at: "2026-01-01T00:00:00Z",
  };

  beforeEach(() => stubStorage());

  it("asks the criteria endpoint for this workspace and returns the saved version", async () => {
    const fetchMock = json(200, saved);
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadSavedCriteria(DEMO_WORKSPACE_ID);

    expect(fetchMock.mock.calls[0][0]).toMatch(new RegExp(`/api/v1/workspaces/${DEMO_WORKSPACE_ID}/criteria$`));
    expect(fetchMock.mock.calls[0][1]?.method ?? "GET").toBe("GET");
    expect(result?.id).toBe("crit-synth-001");
    expect(result?.question).toBe(saved.question);
  });

  it("maps the seed's one-letter PICO keys to the names the editor reads", async () => {
    vi.stubGlobal("fetch", json(200, saved));
    const result = await loadSavedCriteria(DEMO_WORKSPACE_ID);
    expect(result?.pico_description).toEqual({
      population: "Adults with T2D",
      intervention: "Metformin",
      comparator: "Placebo",
      outcome: "HbA1c",
    });
  });

  it("returns null when nothing has been saved yet (404)", async () => {
    vi.stubGlobal("fetch", json(404, { error: { code: "NOT_FOUND", message: "No criteria version saved yet" } }));
    await expect(loadSavedCriteria(DEMO_WORKSPACE_ID)).resolves.toBeNull();
  });

  it("does not hide a real failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(loadSavedCriteria(DEMO_WORKSPACE_ID)).rejects.toMatchObject({ code: "SERVICE_UNREACHABLE" });
  });
});

describe("reloading the setup page of a review that is not the demo", () => {
  const saved = {
    id: "crit-mine-1",
    workspace_id: "ws-mine",
    sequence: 2,
    question: "Do statins reduce stroke risk?",
    pico_description: { population: "Adults at risk", intervention: "Statins" },
    criteria: [],
    content_hash: "h",
    created_at: "2026-01-01T00:00:00Z",
  };

  beforeEach(() => stubStorage());

  it("loads that review's own latest saved question and keeps its PICO as saved", async () => {
    const fetchMock = json(200, saved);
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadSavedCriteria("ws-mine");

    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/v1\/workspaces\/ws-mine\/criteria$/);
    expect(result?.id).toBe("crit-mine-1");
    expect(result?.question).toBe("Do statins reduce stroke risk?");
    expect(result?.pico_description).toEqual({ population: "Adults at risk", intervention: "Statins" });
  });

  it("keeps the empty form when nothing is saved yet (404)", async () => {
    vi.stubGlobal("fetch", json(404, { error: { code: "NOT_FOUND", message: "No criteria version saved yet" } }));
    await expect(loadSavedCriteria("ws-mine")).resolves.toBeNull();
  });

  it("leaves the search unlocked once the saved question is passed in", () => {
    const markup = renderToString(<QueryBuilder workspaceId="ws-mine" criteriaVersionId={saved.id} />);
    expect(markup).not.toContain(SAVE_QUESTION_HINT);
    const save = [...markup.matchAll(/<button\b[^>]*>.*?<\/button>/gs)].find((m) => m[0].includes("Save Query Version"));
    expect(save![0].match(/^<button\b[^>]*>/)![0]).not.toMatch(/\sdisabled=""/);
  });

  it("the page loads saved criteria for every review, not only the demo", () => {
    // Regression guard: the loader used to be skipped for anything but ws-synth-001
    expect(pageSource).not.toMatch(/workspaceId\s*!==\s*DEMO_WORKSPACE_ID/);
    expect(pageSource).toContain("loadSavedCriteria(workspaceId)");
  });
});

describe("search can't be saved before the review question is", () => {
  const html = (criteriaVersionId?: string | null) =>
    renderToString(<QueryBuilder workspaceId="ws-new" criteriaVersionId={criteriaVersionId} />);

  /** Opening tag of the button that contains `label` (it may start with an icon). */
  const buttonTag = (markup: string, label: string) => {
    const button = [...markup.matchAll(/<button\b[^>]*>.*?<\/button>/gs)].find((m) => m[0].includes(label));
    expect(button, `no button labelled "${label}"`).toBeDefined();
    return button![0].match(/^<button\b[^>]*>/)![0];
  };
  // The attribute, not the Tailwind `disabled:` class that is on every button
  const isDisabled = (tag: string) => /\sdisabled=""/.test(tag);

  it.each([undefined, null])("disables Save and the run buttons, with a hint, when criteria is %s", (value) => {
    const markup = html(value);
    expect(isDisabled(buttonTag(markup, "Save Query Version"))).toBe(true);
    expect(isDisabled(buttonTag(markup, "Count on pubmed"))).toBe(true);
    expect(isDisabled(buttonTag(markup, "Count on europepmc"))).toBe(true);
    expect(markup).toContain(SAVE_QUESTION_HINT);
    expect(SAVE_QUESTION_HINT).toBe("Save the review question first.");
  });

  it("enables Save and drops the hint once a question is saved", () => {
    const markup = html("crit-real-1");
    expect(isDisabled(buttonTag(markup, "Save Query Version"))).toBe(false);
    // Running a count still waits for a saved query, but no longer because of the question
    expect(markup).not.toContain(SAVE_QUESTION_HINT);
  });

  it("the page no longer has a placeholder criteria id to send", () => {
    // Regression guard: "crit-ver-default" was sent to the API and rejected with HTTP 400
    expect(pageSource).not.toContain("crit-ver-default");
    expect(builderSource).not.toContain("crit-ver-default");
  });
});

describe("a link to a review that no longer exists", () => {
  it("shows one clear message with a way back instead of raw 404s", () => {
    const markup = renderToString(<WorkspaceNotFound workspaceId="ws-gone" onGoToReviews={() => undefined} />)
      .replace(/&#x27;/g, "'")
      .replace(/&quot;/g, '"');

    expect(markup).toContain('role="alert"');
    expect(markup).toContain("This review doesn't exist");
    expect(markup).toContain("ws-gone");
    expect(markup).toContain("Go to your reviews");
    expect(markup).not.toMatch(/Not Found|HTTP 404/i);
  });
});
