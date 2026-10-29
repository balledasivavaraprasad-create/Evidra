import React from "react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ModelErrorNotice } from "../features/review-queue/AssistantPanel";
import { api, type AssistantProposal } from "../api/client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("assistant errors are shown, not hidden", () => {
  it("shows the real reason the model could not answer", () => {
    const html = renderToString(
      <ModelErrorNotice message="The AI service rejected the API key. Check that LLM_API_KEY is correct and allowed to use this model." />,
    ).replace(/&#x27;/g, "'");
    expect(html).toContain('role="alert"');
    expect(html).toContain("The AI model couldn't answer");
    expect(html).toContain("rejected the API key");
    expect(html).toContain("not a model answer");
  });

  it("shows a quota problem in the same way", () => {
    const html = renderToString(<ModelErrorNotice message="The AI service's quota or rate limit was reached." />);
    expect(html).toContain("quota or rate limit");
  });

  it("shows nothing when the model answered", () => {
    expect(renderToString(<ModelErrorNotice message={null} />)).toBe("");
    expect(renderToString(<ModelErrorNotice message={undefined} />)).toBe("");
  });

  it("the proposal from the server carries the reason", async () => {
    const proposal: AssistantProposal = {
      task: "explain_screening",
      proposal_text: "Deterministic fallback proposal based on [PUBMED:1]",
      citations: [],
      confidence_rationale: "The AI model could not answer",
      requires_human_approval: true,
      model_error: "The AI service's quota or rate limit was reached.",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(proposal), { status: 200, headers: { "content-type": "application/json" } })),
    );
    const got = await api.assistant.query("ws-1", { task: "explain_screening", target_id: "g1", user_prompt: "Why?" });
    expect(got.model_error).toBe("The AI service's quota or rate limit was reached.");
  });

  it("a server error reaches the reader with its own message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ code: "HTTP_ERROR", message: "Workspace has no corpus revision to query" }), {
          status: 400,
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    const err = await api.assistant.query("ws-1", { task: "explain_screening", target_id: "g1", user_prompt: "Why?" }).catch((e) => e);
    expect(err.message).toBe("Workspace has no corpus revision to query");
  });
});
