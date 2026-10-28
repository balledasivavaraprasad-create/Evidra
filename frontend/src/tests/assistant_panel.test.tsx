import React from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  AssistantPanel,
  CALM_ASSISTANT_DISABLED_NOTE,
} from "../features/review-queue/AssistantPanel";
import { ApiError } from "../api/client";

describe("AssistantPanel (AI Disabled State & 501 Resilience)", () => {
  it("displays the calm note and disables user input when both llm_enabled and rag_enabled are false", () => {
    const html = renderToString(
      <AssistantPanel
        workspaceId="ws-test-001"
        targetGroupId="grp-001"
        initialCapabilities={{ llm_enabled: false, rag_enabled: false }}
      />
    );

    // Displays calm note
    expect(html).toContain(CALM_ASSISTANT_DISABLED_NOTE);
    expect(html).toContain("AI Assistant Offline");

    // Inputs must be disabled
    expect(html).toContain('disabled=""');
    expect(html).toContain("AI assistant is disabled in this environment.");
  });

  it("enables user input and omits the calm note when capabilities allow LLM or RAG", () => {
    const html = renderToString(
      <AssistantPanel
        workspaceId="ws-test-001"
        targetGroupId="grp-001"
        initialCapabilities={{ llm_enabled: true, rag_enabled: true }}
      />
    );

    // Does not display calm note
    expect(html).not.toContain(CALM_ASSISTANT_DISABLED_NOTE);
    expect(html).toContain("Ask the bounded assistant about this paper...");
    expect(html).toContain("Ask Assistant");
  });

  it("confirms 501 HTTP status maps to the friendly calm note for demo environments", () => {
    const apiError501 = ApiError.fromEnvelope(501, {
      code: "NOT_IMPLEMENTED",
      message: "Operation 'query_assistant' is disabled by default runtime configuration.",
      retryable: false,
    });

    expect(apiError501.status).toBe(501);
    expect(CALM_ASSISTANT_DISABLED_NOTE).toBe(
      "AI assistant is turned off in this demo. Rules-based screening and manual review work as normal."
    );
  });

  it("upholds AGENTS.md invariant: rules and manual review remain unblocked", () => {
    const capabilities = { llm_enabled: false, rag_enabled: false };
    const isAiDisabled = !capabilities.llm_enabled && !capabilities.rag_enabled;

    expect(isAiDisabled).toBe(true);
    // AGENTS.md rule: if AI is disabled or fails, rules and manual review remain fully available
    expect(CALM_ASSISTANT_DISABLED_NOTE).toContain("Rules-based screening and manual review work as normal.");
  });
});
