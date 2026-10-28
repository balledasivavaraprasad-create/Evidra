import React, { useEffect, useState } from "react";
import { Sparkles, AlertCircle, CheckCircle, Quote, Bot, ShieldAlert } from "lucide-react";
import { api, type AssistantProposal, type AssistantRequest, ApiError, type CapabilitiesResponse } from "../../api/client";

export const CALM_ASSISTANT_DISABLED_NOTE =
  "AI assistant is turned off in this demo. Rules-based screening and manual review work as normal.";

interface AssistantPanelProps {
  workspaceId: string;
  targetGroupId: string;
  onApplyProposal?: (proposal: AssistantProposal) => void;
  initialCapabilities?: CapabilitiesResponse | null;
}

export const AssistantPanel: React.FC<AssistantPanelProps> = ({
  workspaceId,
  targetGroupId,
  initialCapabilities,
}) => {
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(
    initialCapabilities !== undefined ? initialCapabilities : null
  );
  const [task, setTask] = useState<"explain_screening" | "propose_pico" | "suggest_query">("explain_screening");
  const [userPrompt, setUserPrompt] = useState<string>(
    "Explain why this paper was recommended for inclusion or exclusion based on the review criteria."
  );
  const [loading, setLoading] = useState(false);
  const [proposal, setProposal] = useState<AssistantProposal | null>(null);
  const [disabledMessage, setDisabledMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);

  useEffect(() => {
    let mounted = true;
    if (initialCapabilities !== undefined) {
      return;
    }
    api.capabilities
      .get()
      .then((caps) => {
        if (mounted) setCapabilities(caps);
      })
      .catch(() => {
        // Fallback: leave capabilities null; runtime 501/503 handler handles disabled state
      });
    return () => {
      mounted = false;
    };
  }, [initialCapabilities]);

  const bothFlagsDisabled = capabilities !== null && !capabilities.llm_enabled && !capabilities.rag_enabled;
  const isInputDisabled = bothFlagsDisabled || Boolean(disabledMessage);

  const handleQuery = async () => {
    if (isInputDisabled) return;
    setLoading(true);
    setErrorMessage(null);
    setDisabledMessage(null);
    setApplied(false);
    try {
      const req: AssistantRequest = {
        task,
        target_id: targetGroupId,
        user_prompt: userPrompt,
      };
      const res = await api.assistant.query(workspaceId, req);
      setProposal(res);
    } catch (err: unknown) {
      if (err instanceof ApiError && (err.status === 501 || err.status === 503)) {
        setDisabledMessage(CALM_ASSISTANT_DISABLED_NOTE);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to query assistant");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-400" />
          <h3 className="text-base font-semibold text-slate-100">Bounded Evidence Assistant</h3>
          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            Level 2 AI
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
          <span>Requires Human Confirmation</span>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        {/* Calm Note / Preemptive Disabled Banner */}
        {bothFlagsDisabled && (
          <div
            data-testid="assistant-calm-note"
            className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-700/60 text-slate-300 text-xs flex items-start gap-2.5"
          >
            <AlertCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-slate-200">AI Assistant Offline</p>
              <p className="text-slate-400 mt-0.5">{CALM_ASSISTANT_DISABLED_NOTE}</p>
            </div>
          </div>
        )}

        {/* Task Selection */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Inquiry Task</label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: "explain_screening", label: "Explain Screening" },
              { id: "propose_pico", label: "Propose PICO" },
              { id: "suggest_query", label: "Query Advice" },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                disabled={isInputDisabled}
                onClick={() => {
                  setTask(t.id as any);
                  if (t.id === "explain_screening") {
                    setUserPrompt("Explain why this paper was recommended for inclusion or exclusion based on criteria.");
                  } else if (t.id === "propose_pico") {
                    setUserPrompt("Extract key Population, Intervention, Comparator, and Outcomes from abstract text.");
                  } else {
                    setUserPrompt("Suggest synonym expansions or query improvements for this topic.");
                  }
                }}
                className={`py-1.5 px-2 rounded-lg text-xs font-medium border transition-colors ${
                  isInputDisabled
                    ? "bg-slate-800/20 border-slate-800 text-slate-600 cursor-not-allowed"
                    : task === t.id
                    ? "bg-indigo-600/20 border-indigo-500 text-indigo-300"
                    : "bg-slate-800/40 border-slate-700/60 text-slate-400 hover:text-slate-200"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* User Prompt */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Prompt / Question</label>
          <textarea
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            disabled={isInputDisabled}
            rows={2}
            className={`w-full rounded-lg p-2.5 text-xs transition-colors focus:outline-none ${
              isInputDisabled
                ? "bg-slate-950/40 border border-slate-800 text-slate-500 placeholder-slate-600 cursor-not-allowed opacity-60"
                : "bg-slate-950/60 border border-slate-700/80 text-slate-200 placeholder-slate-500 focus:border-indigo-500"
            }`}
            placeholder={
              isInputDisabled
                ? "AI assistant is disabled in this environment."
                : "Ask the bounded assistant about this paper..."
            }
          />
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end">
          <button
            type="button"
            onClick={handleQuery}
            disabled={isInputDisabled || loading || !userPrompt.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors shadow-lg shadow-indigo-600/20 disabled:cursor-not-allowed"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {loading ? "Querying Assistant..." : "Ask Assistant"}
          </button>
        </div>

        {/* Reactive 501 / Disabled Banner (shown if 501 occurs and calm note wasn't already shown) */}
        {disabledMessage && !bothFlagsDisabled && (
          <div
            data-testid="assistant-501-banner"
            className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs flex items-start gap-2.5"
          >
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-amber-300">AI Assistant Offline</p>
              <p className="text-amber-200/80 mt-0.5">{disabledMessage}</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {errorMessage && (
          <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-rose-300">Assistant Error</p>
              <p className="text-rose-200/80 mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Proposal Result */}
        {proposal && (
          <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
            <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
              <div className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                <span>Assistant Proposal</span>
                <span className="text-[10px] text-indigo-400 font-mono">Task: {proposal.task}</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                {proposal.proposal_text}
              </p>
              {proposal.confidence_rationale && (
                <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/80">
                  <span className="text-slate-300 font-medium">Confidence Rationale: </span>
                  {proposal.confidence_rationale}
                </div>
              )}
            </div>

            {/* Citations */}
            {proposal.citations && proposal.citations.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                  <Quote className="w-3 h-3 text-indigo-400" />
                  Grounded Corpus Citations ({proposal.citations.length})
                </h4>
                <div className="space-y-1.5">
                  {proposal.citations.map((c, i) => (
                    <div
                      key={i}
                      className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/40 text-xs text-slate-300"
                    >
                      <div className="flex items-center justify-between text-[11px] text-indigo-300 font-mono mb-1">
                        <span>{c.citation_handle}</span>
                        <span className="text-slate-400">offsets: [{c.start_cp}:{c.end_cp}]</span>
                      </div>
                      <p className="text-slate-300 italic">"{c.text_snippet}"</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Human Confirmation CTA */}
            <div className="flex items-center justify-between pt-2">
              <span className="text-[11px] text-slate-400">
                Machine suggestions never mutate decisions automatically.
              </span>
              <button
                type="button"
                onClick={() => setApplied(true)}
                disabled={applied}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50 transition-colors"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                {applied ? "Applied to Notes" : "Accept Suggestion"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
