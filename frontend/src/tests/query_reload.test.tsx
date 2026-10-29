import { afterEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { api } from "../api/client";
import type {
  CriteriaVersionResponse,
  JobResponse,
  QueryASTNodeInput,
  QueryVersionResponse,
  SearchExecutionResponse,
} from "../api/client";
import { astToGroups, compileClauseToAST, type QueryGroupClause } from "../features/search/astCompiler";
import { QueryBuilder } from "../features/search/QueryBuilder";
import { ImportWorkflow } from "../features/runs/ImportWorkflow";
import {
  executionLabel,
  isImportable,
  isTicked,
  nothingFoundMessage,
  selectedIds,
  sortExecutions,
  upsertExecution,
  withSelection,
} from "../features/search/executions";
import { splitPicoTerms, termsFromPico } from "../features/search/searchTerms";
import { loadSetupData, newestJob } from "../features/search/setupData";
import { importPhase, isProcessingDone, processingLine } from "../features/runs/processing";

afterEach(() => {
  vi.unstubAllGlobals();
});

const term = (t: string): QueryASTNodeInput => ({ term: t, operator: null, children: null });
const group = (operator: "AND" | "OR" | "NOT", ...terms: string[]): QueryASTNodeInput => ({
  operator,
  children: terms.map(term),
});

describe("astToGroups is the inverse of compileClauseToAST", () => {
  const roundTrip = (ast: QueryASTNodeInput) => {
    const parsed = astToGroups(ast);
    expect(parsed).not.toBeNull();
    return compileClauseToAST(parsed!.groups, parsed!.rootOperator);
  };

  it("a single-term root", () => {
    const parsed = astToGroups(term("empagliflozin"));
    expect(parsed?.groups).toHaveLength(1);
    expect(parsed?.groups[0].clauses.map((c) => c.term)).toEqual(["empagliflozin"]);
    expect(roundTrip(term("empagliflozin"))).toEqual(term("empagliflozin"));
  });

  it("the empty query ('*') has no groups", () => {
    expect(astToGroups(term("*"))).toEqual({ rootOperator: "AND", groups: [] });
  });

  it("one flat group keeps its operator and terms", () => {
    const ast = group("OR", "SGLT2 inhibitor", "empagliflozin", "dapagliflozin");
    const parsed = astToGroups(ast)!;
    expect(parsed.groups).toHaveLength(1);
    expect(parsed.groups[0].operator).toBe("OR");
    expect(parsed.groups[0].clauses.map((c) => c.term)).toEqual(["SGLT2 inhibitor", "empagliflozin", "dapagliflozin"]);
    expect(roundTrip(ast)).toEqual(ast);
  });

  it("two groups under AND (the shape the builder saves for intervention and population)", () => {
    const ast: QueryASTNodeInput = {
      operator: "AND",
      children: [group("OR", "SGLT2 inhibitor", "empagliflozin"), group("OR", "type 2 diabetes", "T2D")],
    };
    const parsed = astToGroups(ast)!;
    expect(parsed.rootOperator).toBe("AND");
    expect(parsed.groups.map((g) => g.clauses.map((c) => c.term))).toEqual([
      ["SGLT2 inhibitor", "empagliflozin"],
      ["type 2 diabetes", "T2D"],
    ]);
    expect(roundTrip(ast)).toEqual(ast);
  });

  it("a one-term group next to a multi-term group, under OR and NOT roots", () => {
    for (const root of ["OR", "NOT"] as const) {
      const ast: QueryASTNodeInput = { operator: root, children: [term("adults with type 2 diabetes"), group("OR", "a", "b")] };
      const parsed = astToGroups(ast)!;
      expect(parsed.rootOperator).toBe(root);
      expect(parsed.groups).toHaveLength(2);
      expect(roundTrip(ast)).toEqual(ast);
    }
  });

  it("builder groups -> AST -> groups -> AST is stable", () => {
    const groups: QueryGroupClause[] = [
      { id: "g1", operator: "OR", clauses: [{ id: "a", field: "all", term: "x" }, { id: "b", field: "all", term: "y" }] },
      { id: "g2", operator: "AND", clauses: [{ id: "c", field: "all", term: "z" }, { id: "d", field: "all", term: "w" }] },
    ];
    const ast = compileClauseToAST(groups, "AND");
    const back = astToGroups(ast)!;
    expect(compileClauseToAST(back.groups, back.rootOperator)).toEqual(ast);
  });

  it("returns null for nesting deeper than one level, instead of guessing", () => {
    const deep: QueryASTNodeInput = {
      operator: "AND",
      children: [term("a"), { operator: "OR", children: [term("b"), group("AND", "c", "d")] }],
    };
    expect(astToGroups(deep)).toBeNull();
  });
});

describe("default search terms come from the PICO", () => {
  const crit = (pico: Record<string, string>) => ({ pico_description: pico }) as unknown as CriteriaVersionResponse;

  it("splits on commas, ' or ', slashes and parentheses", () => {
    expect(splitPicoTerms("SGLT2 inhibitor, empagliflozin, dapagliflozin, canagliflozin")).toEqual([
      "SGLT2 inhibitor",
      "empagliflozin",
      "dapagliflozin",
      "canagliflozin",
    ]);
    expect(splitPicoTerms("empagliflozin (Jardiance) or dapagliflozin/canagliflozin")).toEqual([
      "empagliflozin",
      "Jardiance",
      "dapagliflozin",
      "canagliflozin",
    ]);
    expect(splitPicoTerms("  ;  ")).toEqual([]);
    expect(splitPicoTerms("Metformin, metformin")).toEqual(["Metformin"]);
    // "or" inside a word is not a separator
    expect(splitPicoTerms("hormone therapy")).toEqual(["hormone therapy"]);
  });

  it("builds intervention then population groups, one term each", () => {
    const terms = termsFromPico(
      crit({
        population: "adults with type 2 diabetes",
        intervention: "SGLT2 inhibitor, empagliflozin, dapagliflozin, canagliflozin",
        comparator: "placebo",
        outcome: "heart failure hospitalization",
      }),
    );
    expect(terms).toEqual([
      ["SGLT2 inhibitor", "empagliflozin", "dapagliflozin", "canagliflozin"],
      ["adults with type 2 diabetes"],
    ]);
  });

  it("is a single empty group, never example terms, when there is no PICO", () => {
    expect(termsFromPico(null)).toEqual([[""]]);
    expect(termsFromPico(crit({}))).toEqual([[""]]);
  });
});

const exec = (id: string, over: Partial<SearchExecutionResponse> = {}): SearchExecutionResponse => ({
  id,
  query_version_id: "qv-1",
  source: "pubmed",
  exact_query: "empagliflozin[All Fields]",
  hit_count: 1200,
  counted_at: "2026-10-29T10:00:00Z",
  partial: false,
  selected_for_import: true,
  status: "succeeded",
  synonym_setting: false,
  ...over,
});

describe("search execution list rules", () => {
  it("counting the same query again replaces the row instead of adding a second", () => {
    const first = exec("aaaa1111bbbb2222");
    const recount = exec("aaaa1111bbbb2222", { hit_count: 1300 });
    const list = upsertExecution([first], recount);
    expect(list).toHaveLength(1);
    expect(list[0].hit_count).toBe(1300);
  });

  it("a new execution goes on top; an old one keeps its place when replaced", () => {
    const a = exec("a1");
    const b = exec("b2", { source: "europepmc" });
    expect(upsertExecution([a], b).map((e) => e.id)).toEqual(["b2", "a1"]);
    expect(upsertExecution([b, a], { ...a, hit_count: 5 }).map((e) => e.id)).toEqual(["b2", "a1"]);
  });

  it("ticked ids list each id once, and ticking changes only the row asked", () => {
    const list = [exec("a1"), exec("b2", { source: "europepmc" })];
    expect(selectedIds(list)).toEqual(["a1", "b2"]);
    const next = withSelection(list, "a1", false);
    expect(next.map((e) => e.selected_for_import)).toEqual([false, true]);
    expect(next[1]).toBe(list[1]);
    expect(selectedIds([...list, list[0]])).toEqual(["a1", "b2"]);
  });

  it("is shown newest first and labelled with the source and the last 8 characters of the id", () => {
    const old = exec("old-0000-aaaaaaaa", { counted_at: "2026-10-28T09:00:00Z" });
    const recent = exec("new-0000-bbbbbbbb", { counted_at: "2026-10-29T09:00:00Z" });
    expect(sortExecutions([old, recent]).map((e) => e.id)).toEqual([recent.id, old.id]);
    expect(executionLabel(recent)).toBe("pubmed · bbbbbbbb");
  });
});

const savedQuery: QueryVersionResponse = {
  id: "qv-1",
  workspace_id: "ws-1",
  sequence: 1,
  ast: {
    operator: "AND",
    children: [group("OR", "SGLT2 inhibitor", "empagliflozin"), term("adults with type 2 diabetes")],
  },
  start_date: "2019",
  end_date: null,
  sources: ["pubmed"],
  criteria_version_id: "crit-1",
  content_hash: "h",
  created_at: "2026-10-29T09:00:00Z",
} as QueryVersionResponse;

const inputTag = (markup: string, ariaLabel: RegExp) =>
  markup.match(new RegExp(`<input[^>]*aria-label="${ariaLabel.source}"[^>]*>`))?.[0] ?? "";

describe("the query builder after a reload", () => {
  const ticked = exec("aaaaaaaa11111111");
  const unticked = exec("bbbbbbbb22222222", { source: "europepmc", selected_for_import: false });
  const markup = renderToString(
    <QueryBuilder
      workspaceId="ws-1"
      criteriaVersionId="crit-1"
      savedQuery={savedQuery}
      savedExecutions={[ticked, unticked]}
      initialTerms={[["ignored"]]}
    />,
  );

  it("rebuilds terms, dates and sources from the saved query, not from defaults", () => {
    expect(markup).toContain('value="SGLT2 inhibitor"');
    expect(markup).toContain('value="empagliflozin"');
    expect(markup).toContain('value="adults with type 2 diabetes"');
    expect(markup).not.toContain('value="ignored"');
    expect(markup).toContain('value="2019"');
    expect(markup).not.toContain('value="2020"');
    expect(markup).not.toMatch(/metformin|glucophage/i);
    // only PubMed was saved, so only PubMed has a count button
    expect(markup).toContain("Count on pubmed");
    expect(markup).not.toContain("Count on europepmc");
  });

  it("treats the saved query as active", () => {
    expect(markup).toContain("Query Seq #");
    expect(markup).toContain("qv-1".slice(0, 8));
    const countTag = markup.match(/<button\b[^>]*>(?:(?!<\/button>).)*Count on pubmed/s)?.[0] ?? "";
    expect(countTag).not.toMatch(/\sdisabled=""/);
  });

  it("shows each saved count once, ticked or not as the server has it", () => {
    expect(markup.replace(/<!-- -->/g, "")).toContain("1 of 2 selected for import");
    expect(inputTag(markup, /Import pubmed · 11111111/)).toMatch(/\schecked=""/);
    expect(inputTag(markup, /Import europepmc · 22222222/)).not.toMatch(/\schecked=""/);
    expect(markup).toContain("pubmed · 11111111");
    expect(markup).toContain("europepmc · 22222222");
  });

  it("with nothing saved it starts from the PICO terms it is given, never the old example", () => {
    const fresh = renderToString(
      <QueryBuilder
        workspaceId="ws-2"
        criteriaVersionId="crit-2"
        initialTerms={[["SGLT2 inhibitor", "empagliflozin"], ["adults with type 2 diabetes"]]}
      />,
    );
    expect(fresh).toContain('value="SGLT2 inhibitor"');
    expect(fresh).toContain('value="adults with type 2 diabetes"');
    expect(fresh).not.toMatch(/metformin|glucophage|T2D/i);
    expect(fresh).not.toContain("Query Seq #");
  });

  it("tells the reader when a saved search is too nested to show as groups", () => {
    const nested = {
      ...savedQuery,
      ast: { operator: "AND", children: [term("a"), { operator: "OR", children: [term("b"), group("AND", "c", "d")] }] },
    } as QueryVersionResponse;
    const out = renderToString(
      <QueryBuilder workspaceId="ws-1" criteriaVersionId="crit-1" savedQuery={nested} initialTerms={[["x"]]} />,
    );
    expect(out).toContain("nested more deeply");
  });
});

const job = (over: Partial<JobResponse>): JobResponse =>
  ({
    id: "job-1",
    workspace_id: "ws-1",
    kind: "import_records",
    state: "succeeded",
    progress: 1,
    processed_items: 400,
    total_items: 400,
    request_key: "k",
    created_at: "2026-10-29T10:00:00Z",
    updated_at: "2026-10-29T10:01:00Z",
    ...over,
  }) as JobResponse;

describe("the import workflow resumes the latest job", () => {
  const render = (initialJob: JobResponse | null) =>
    renderToString(
      <MemoryRouter>
        <ImportWorkflow workspaceId="ws-1" selectedExecutionIds={[]} initialJob={initialJob} />
      </MemoryRouter>,
    );

  it("shows a running import with its progress and a cancel button", () => {
    const markup = render(job({ state: "running", progress: 0.5, processed_items: 200 }));
    expect(markup).toMatch(/State:\s*(<!-- -->)?\s*running/);
    expect(markup).toContain("Cancel Job");
    expect(markup).not.toContain("Approve &amp; Start Import");
  });

  it("shows a finished import with a way to start another", () => {
    const markup = render(job({ state: "succeeded" }));
    expect(markup).toMatch(/State:\s*(<!-- -->)?\s*succeeded/);
    expect(markup).toContain("New Import");
  });

  it("shows the start form when no import has happened", () => {
    expect(render(null)).toContain("Approve &amp; Start Import");
  });

  it("picks the newest job whatever order the server returns", () => {
    const older = job({ id: "old", created_at: "2026-10-28T10:00:00Z" });
    const newer = job({ id: "new", created_at: "2026-10-29T10:00:00Z" });
    expect(newestJob([older, newer])?.id).toBe("new");
    expect(newestJob([newer, older])?.id).toBe("new");
    expect(newestJob([])).toBeNull();
  });
});

describe("loading the setup page's data", () => {
  const body = (status: number, data: unknown) =>
    new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
  const notFound = () => body(404, { error: { code: "NOT_FOUND", message: "Nothing saved yet" } });
  const workspace = { id: "ws-1", title: "SGLT2i and HF hospitalization in T2D" };

  function stubServer(routes: Record<string, () => Response>) {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const key = Object.keys(routes).find((k) => url.includes(k));
      if (!key) throw new Error(`unexpected request ${url}`);
      return routes[key]();
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("reads question, query, counts and latest import from the server", async () => {
    const fetchMock = stubServer({
      "/api/v1/workspaces/ws-1/criteria": () => body(200, { id: "crit-1", workspace_id: "ws-1", sequence: 1, question: "Q", pico_description: { population: "p" }, criteria: [], content_hash: "h", created_at: "2026-10-29T09:00:00Z" }),
      "/api/v1/workspaces/ws-1/queries/latest": () => body(200, savedQuery),
      "/api/v1/workspaces/ws-1/executions": () => body(200, [exec("aaaa"), exec("bbbb", { counted_at: "2026-10-29T11:00:00Z" })]),
      "/api/v1/workspaces/ws-1/jobs": () => body(200, [job({ id: "j1" })]),
      "/api/v1/workspaces": () => body(200, [workspace]),
    });

    const data = await loadSetupData("ws-1");

    expect(data.workspace?.title).toBe(workspace.title);
    expect(data.criteria?.id).toBe("crit-1");
    expect(data.query?.id).toBe("qv-1");
    expect(data.executions.map((e) => e.id)).toEqual(["bbbb", "aaaa"]);
    expect(data.importJob?.id).toBe("j1");
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.find((u) => u.includes("/executions"))).toContain("query_version_id=qv-1");
    expect(urls.find((u) => u.includes("/jobs"))).toContain("kind=import_records");
  });

  it("treats 404 for the question and query as 'nothing saved yet', and skips the counts", async () => {
    const fetchMock = stubServer({
      "/api/v1/workspaces/ws-1/criteria": notFound,
      "/api/v1/workspaces/ws-1/queries/latest": notFound,
      "/api/v1/workspaces/ws-1/jobs": () => body(200, []),
      "/api/v1/workspaces": () => body(200, [workspace]),
    });

    const data = await loadSetupData("ws-1");

    expect(data).toMatchObject({ criteria: null, query: null, executions: [], importJob: null });
    expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("/executions"))).toBe(false);
  });

  it.each([
    ["the counts", "/api/v1/workspaces/ws-1/executions"],
    ["the jobs", "/api/v1/workspaces/ws-1/jobs"],
    ["the question", "/api/v1/workspaces/ws-1/criteria"],
  ])("fails loudly when %s cannot be loaded, instead of showing an empty form", async (_what, failing) => {
    stubServer({
      "/api/v1/workspaces/ws-1/criteria": () => body(200, { id: "crit-1", workspace_id: "ws-1", sequence: 1, question: "Q", pico_description: {}, criteria: [], content_hash: "h", created_at: "2026-10-29T09:00:00Z" }),
      "/api/v1/workspaces/ws-1/queries/latest": () => body(200, savedQuery),
      "/api/v1/workspaces/ws-1/executions": () => body(200, []),
      "/api/v1/workspaces/ws-1/jobs": () => body(200, []),
      "/api/v1/workspaces": () => body(200, [workspace]),
      [failing]: () => new Response("Internal Server Error", { status: 500, headers: { "content-type": "text/plain" } }),
    });
    await expect(loadSetupData("ws-1")).rejects.toMatchObject({ status: 500 });
  });
});

describe("a count that finds nothing", () => {
  const found = exec("aaaaaaaa11111111", { hit_count: 1200 });
  // Older saved data could still say "ticked" for a 0-hit count
  const empty = exec("bbbbbbbb22222222", { source: "europepmc", hit_count: 0, selected_for_import: true });

  it("is never counted as ticked for import", () => {
    expect(isImportable(empty)).toBe(false);
    expect(isTicked(empty)).toBe(false);
    expect(selectedIds([found, empty])).toEqual([found.id]);
  });

  it("is named after its source", () => {
    expect(nothingFoundMessage("europepmc")).toBe("Nothing found on Europe PMC");
    expect(nothingFoundMessage("pubmed")).toBe("Nothing found on PubMed");
  });

  it("shows as unticked, locked and labelled in the list", () => {
    const markup = renderToString(
      <QueryBuilder workspaceId="ws-1" criteriaVersionId="crit-1" savedQuery={savedQuery} savedExecutions={[found, empty]} />,
    ).replace(/<!-- -->/g, "");
    const tag = inputTag(markup, /Import europepmc · 22222222/);
    expect(tag).not.toMatch(/\schecked=""/);
    expect(tag).toMatch(/\sdisabled=""/);
    expect(markup).toContain("Nothing found on Europe PMC");
    expect(markup).toContain("1 of 2 selected for import");
    expect(inputTag(markup, /Import pubmed · 11111111/)).toMatch(/\schecked=""/);
  });
});

describe("a source that does not answer", () => {
  it("surfaces the server's plain message instead of a generic failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ code: "SOURCE_UNAVAILABLE", message: "Europe PMC didn't respond: the request timed out", retryable: true }),
          { status: 502, headers: { "content-type": "application/json" } },
        ),
      ),
    );
    const err = await api.queries.executeSearch("qv-1", { source: "europepmc", synonym_expansion: false }).catch((e) => e);
    expect(err.message).toBe("Europe PMC didn't respond: the request timed out");
    expect(err.code).toBe("SOURCE_UNAVAILABLE");
  });
});

describe("import flows into processing", () => {
  const imp = (over: Partial<JobResponse> = {}) => job({ id: "imp", created_at: "2026-10-29T10:00:00Z", ...over });
  const proc = (over: Partial<JobResponse> = {}) =>
    job({ id: "proc", kind: "screen", created_at: "2026-10-29T10:01:00Z", state: "queued", ...over });

  it("reads Importing -> Processing -> Ready", () => {
    expect(importPhase(imp({ state: "running" }), null)).toBe("importing");
    expect(importPhase(imp({ state: "queued" }), null)).toBe("importing");
    expect(importPhase(imp({ state: "succeeded" }), proc({ state: "queued" }))).toBe("processing");
    expect(importPhase(imp({ state: "succeeded" }), proc({ state: "running" }))).toBe("processing");
    expect(importPhase(imp({ state: "succeeded" }), proc({ state: "succeeded" }))).toBe("ready");
  });

  it("treats processing that paused for the reviewer as ready: the papers are there", () => {
    const paused = proc({ state: "waiting_human" });
    expect(isProcessingDone(paused)).toBe(true);
    expect(importPhase(imp({ state: "succeeded" }), paused)).toBe("ready");
  });

  it("reports a stopped import or stopped processing, not Ready", () => {
    expect(importPhase(imp({ state: "failed" }), null)).toBe("import-failed");
    expect(importPhase(imp({ state: "partial" }), null)).toBe("import-failed");
    expect(importPhase(imp({ state: "succeeded" }), proc({ state: "failed" }))).toBe("processing-failed");
  });

  it("never says Ready before it has looked up the processing job", () => {
    // Just after an import finishes there is "no processing job yet" only because we haven't asked
    expect(importPhase(imp({ state: "succeeded" }), null, false)).toBe("processing");
    expect(importPhase(imp({ state: "succeeded" }), null, true)).toBe("ready");
    expect(importPhase(imp({ state: "running" }), null, false)).toBe("importing");
    expect(importPhase(imp({ state: "failed" }), null, false)).toBe("import-failed");
  });

  it("ignores a processing job that is older than the import", () => {
    const older = proc({ created_at: "2026-10-28T10:00:00Z", state: "running" });
    expect(importPhase(imp({ state: "succeeded" }), older)).toBe("ready");
  });

  it("describes what processing is doing", () => {
    expect(processingLine(proc({ state: "queued" }))).toBe("Waiting to start");
    expect(processingLine(proc({ state: "running" }))).toMatch(/duplicates.*screening.*PICO/i);
  });

  it("the import panel shows the steps, and Go to screening only when ready", () => {
    const panel = (state: JobResponse["state"]) =>
      renderToString(
        <MemoryRouter>
          <ImportWorkflow workspaceId="ws-1" selectedExecutionIds={[]} initialJob={imp({ state })} />
        </MemoryRouter>,
      ).replace(/<!-- -->/g, "");
    const running = panel("running");
    expect(running).toContain("Importing");
    expect(running).toContain("Processing");
    expect(running).toContain("Ready");
    expect(running).not.toContain("Go to screening");
    // A finished import whose processing has not been looked up yet is still Processing, never Ready
    const checking = panel("succeeded");
    expect(checking).toContain("Checking on processing");
    expect(checking).not.toContain("Go to screening");
    expect(panel("failed")).not.toContain("Go to screening");
  });
});
