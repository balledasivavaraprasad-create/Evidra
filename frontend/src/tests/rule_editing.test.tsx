import { afterEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";
import { api, type CriteriaVersionResponse, type CriterionDefinition } from "../api/client";
import { CriteriaEditor } from "../features/review-setup/CriteriaEditor";
import {
  addCustomRule,
  addKeywords,
  parseKeywordInput,
  picoIsReady,
  removeKeyword,
  removeRule,
  usesKeywords,
  validateRules,
} from "../features/review-setup/ruleEditing";
import editorSource from "../features/review-setup/CriteriaEditor.tsx?raw";

afterEach(() => {
  vi.unstubAllGlobals();
});

const picoRule = (over: Partial<CriterionDefinition> = {}): CriterionDefinition => ({
  id: "pico_intervention",
  name: "Intervention: SGLT2 inhibitor",
  category: "intervention",
  is_inclusion: true,
  rationale: "The title or abstract should mention the review's intervention.",
  metadata_first: false,
  keywords: ["SGLT2 inhibitor", "empagliflozin"],
  exclude_keywords: [],
  source: "pico",
  ai_suggested_keywords: [],
  ...over,
});

const genericRule = (): CriterionDefinition => ({
  id: "english_language",
  name: "Language: English Reviewable",
  category: "language",
  is_inclusion: true,
  rationale: "Article must be reviewable in English.",
  metadata_first: true,
  keywords: [],
  exclude_keywords: [],
  source: "generic",
  ai_suggested_keywords: [],
});

describe("editing screening rules", () => {
  it("parses typed keywords on commas, semicolons and new lines", () => {
    expect(parseKeywordInput(" a ,b;  c d \n e ,, ")).toEqual(["a", "b", "c d", "e"]);
  });

  it("adds keywords to one rule, skipping ones it already has (any case)", () => {
    const rules = [picoRule(), genericRule()];
    const next = addKeywords(rules, "pico_intervention", "keywords", "Empagliflozin, dapagliflozin, dapagliflozin");
    expect(next[0].keywords).toEqual(["SGLT2 inhibitor", "empagliflozin", "dapagliflozin"]);
    expect(next[1]).toBe(rules[1]);
  });

  it("removes a keyword, and its AI mark with it", () => {
    const rules = [picoRule({ keywords: ["a", "b"], ai_suggested_keywords: ["b"] })];
    const next = removeKeyword(rules, "pico_intervention", "keywords", "b");
    expect(next[0].keywords).toEqual(["a"]);
    expect(next[0].ai_suggested_keywords).toEqual([]);
  });

  it("removes a rule", () => {
    expect(removeRule([picoRule(), genericRule()], "pico_intervention").map((r) => r.id)).toEqual(["english_language"]);
  });

  it("adds a custom rule with a fresh id, only when it has a name and keywords", () => {
    const rules = [picoRule()];
    expect(addCustomRule(rules, "  ", true, "a")).toBe(rules);
    expect(addCustomRule(rules, "Adults only", true, " , ")).toBe(rules);
    const one = addCustomRule(rules, "Adults only", true, "adult, adults");
    const two = addCustomRule(one, "No pediatrics", false, "children");
    expect(one[1]).toMatchObject({ id: "custom_1", source: "custom", is_inclusion: true, keywords: ["adult", "adults"] });
    expect(two[2]).toMatchObject({ id: "custom_2", is_inclusion: false });
  });

  it("will not save with no rules, or a keyword rule with no keywords", () => {
    expect(validateRules([])).toMatch(/at least one screening rule/i);
    expect(validateRules([picoRule({ keywords: [] })])).toMatch(/Add at least one keyword to “Intervention: SGLT2 inhibitor”/);
    expect(validateRules([picoRule(), genericRule()])).toBeNull();
    expect(validateRules([genericRule()])).toBeNull(); // built-in checks need no keywords
  });

  it("knows which rules are matched by keywords", () => {
    expect(usesKeywords(picoRule())).toBe(true);
    expect(usesKeywords(genericRule())).toBe(false);
  });

  it("is ready to generate once population and intervention are filled", () => {
    expect(picoIsReady({ population: "adults", intervention: " " })).toBe(false);
    expect(picoIsReady({ population: "adults with asthma", intervention: "inhaled steroid" })).toBe(true);
  });
});

const saved = (criteria: CriterionDefinition[]): CriteriaVersionResponse =>
  ({
    id: "crit-1",
    workspace_id: "ws-1",
    sequence: 2,
    question: "Do SGLT2 inhibitors reduce heart failure hospitalization?",
    pico_description: { population: "adults with type 2 diabetes", intervention: "SGLT2 inhibitor, empagliflozin" },
    criteria,
    content_hash: "abcdef123456",
    created_at: "2026-10-29T00:00:00Z",
  }) as CriteriaVersionResponse;

describe("the criteria editor shows the review's own rules", () => {
  const text = (markup: string) => markup.replace(/<!-- -->/g, "").replace(/&#x27;/g, "'");

  it("lists the saved rules with a real count, not a fixed seven", () => {
    const markup = text(
      renderToString(
        <CriteriaEditor workspaceId="ws-1" savedCriteria={saved([picoRule(), genericRule()])} />,
      ),
    );
    expect(markup).toContain("Active Screening Rules (2 active)");
    expect(markup).toContain("Intervention: SGLT2 inhibitor");
    expect(markup).toContain("Language: English Reviewable");
    expect(markup).toContain("Built-in check");
    // keyword chips with a remove button each
    expect(markup).toContain('aria-label="Remove empagliflozin from Intervention: SGLT2 inhibitor"');
  });

  it("marks AI-suggested keywords", () => {
    const markup = text(
      renderToString(
        <CriteriaEditor
          workspaceId="ws-1"
          savedCriteria={saved([picoRule({ keywords: ["SGLT2 inhibitor", "ertugliflozin"], ai_suggested_keywords: ["ertugliflozin"] })])}
        />,
      ),
    );
    expect(markup).toContain("AI suggested: </span>ertugliflozin");
    expect(markup).not.toContain("AI suggested: </span>SGLT2 inhibitor");
  });

  it("starts empty for a new review: no built-in rules, no example PICO", () => {
    const markup = text(renderToString(<CriteriaEditor workspaceId="ws-2" defaultQuestion="Asthma and steroids" />));
    expect(markup).toContain("Active Screening Rules (0 active)");
    expect(markup).toContain("No screening rules yet");
    expect(markup).toContain('value="Asthma and steroids"');
    expect(markup).not.toMatch(/value="[^"]*(metformin|diabetes|HbA1c)/i);
    expect(markup).toContain("Fill in at least the population and the intervention");
    const generate = markup.match(/<button[^>]*>(?:(?!<\/button>).)*Generate rules from my question/s)?.[0] ?? "";
    expect(generate).toMatch(/\sdisabled=""/);
  });

  it("has no metformin text or hardcoded rule list left in the component", () => {
    expect(editorSource).not.toMatch(/metformin|HbA1c|DEFAULT_FRONTEND_CRITERIA|population_adults_t2d/i);
  });
});

describe("asking the server for rules", () => {
  it("posts the question and PICO to the suggest endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ criteria: [picoRule()], ai_synonyms_used: false, notice: null }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const resp = await api.criteria.suggest("ws-1", {
      question: "q",
      pico: { population: "adults with asthma", intervention: "inhaled steroid" },
    });

    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/api\/v1\/workspaces\/ws-1\/criteria\/suggest$/);
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      question: "q",
      pico: { population: "adults with asthma", intervention: "inhaled steroid" },
    });
    expect(resp.criteria[0].id).toBe("pico_intervention");
  });
});
