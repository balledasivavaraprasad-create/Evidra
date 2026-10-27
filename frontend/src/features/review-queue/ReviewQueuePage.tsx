import React, { useState } from "react";
import { useParams } from "react-router-dom";
import {
  CheckCircle,
  XCircle,
  HelpCircle,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ExternalLink,
  BookOpen,
  Tag,
} from "lucide-react";
import { MOCK_GROUPS } from "../../api/fixtures";
import type { PaperGroupSummary } from "../../api/client";

export const ReviewQueuePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [filter, setFilter] = useState<"all" | "include" | "exclude" | "maybe" | "conflict">("all");
  const [selectedGroup, setSelectedGroup] = useState<PaperGroupSummary>(MOCK_GROUPS[0]);
  const [decisionFeedback, setDecisionFeedback] = useState<string | null>(null);

  const filteredGroups = MOCK_GROUPS.filter((g) => {
    if (filter === "all") return true;
    if (filter === "conflict") return g.has_conflict;
    return g.effective_status === filter;
  });

  const handleDecision = (status: "include" | "exclude" | "maybe", reason?: string) => {
    setDecisionFeedback(
      `Recorded manual decision '${status.toUpperCase()}'${reason ? ` (Reason: ${reason})` : ""} for group ${selectedGroup.id}.`
    );
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-cyan-400" />
            <span>Screening Review Workbench</span>
          </h1>
          <p className="text-slate-400 text-xs">
            Review abstracts, inspect PICO entities, verify machine suggestions, and log decisions.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          {(["all", "include", "exclude", "maybe", "conflict"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-md capitalize transition ${
                filter === f
                  ? "bg-slate-800 text-cyan-300 font-semibold shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {decisionFeedback && (
        <div className="p-3 rounded-lg bg-cyan-950/60 border border-cyan-800/80 text-cyan-300 text-xs font-mono flex items-center justify-between">
          <span>{decisionFeedback}</span>
          <button onClick={() => setDecisionFeedback(null)} className="text-cyan-400 hover:text-white">✕</button>
        </div>
      )}

      {/* 3-Panel Review Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[500px]">
        {/* Left Column: Paper Group List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-mono text-slate-400 px-1">
            Displaying {filteredGroups.length} of {MOCK_GROUPS.length} paper groups
          </div>

          <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
            {filteredGroups.map((group) => {
              const isSelected = selectedGroup.id === group.id;
              const rep = group.representative_revision;
              return (
                <div
                  key={group.id}
                  onClick={() => setSelectedGroup(group)}
                  className={`p-3.5 rounded-xl border text-left cursor-pointer transition ${
                    isSelected
                      ? "bg-slate-800/90 border-cyan-500/80 shadow-md shadow-cyan-500/10"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      {rep.source.toUpperCase()} • {rep.external_id}
                    </span>
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                        group.effective_status === "include"
                          ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                          : group.effective_status === "exclude"
                          ? "bg-red-950/80 text-red-300 border border-red-800"
                          : group.effective_status === "conflict"
                          ? "bg-amber-950/80 text-amber-300 border border-amber-800"
                          : "bg-slate-800 text-slate-300 border border-slate-700"
                      }`}
                    >
                      {group.effective_status}
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-white line-clamp-2 leading-snug">
                    {rep.title}
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                    {(rep.authors || []).join(", ")} ({rep.year || "n.d."})
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Center / Right Column: Detailed Abstract Reader & PICO Spans */}
        <div className="lg:col-span-8 space-y-4">
          <div className="glass-panel p-6 space-y-5">
            {/* Header info */}
            <div className="space-y-2 border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                  GROUP: {selectedGroup.id} ({selectedGroup.member_count} copy)
                </span>
                {selectedGroup.has_conflict && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1 font-bold">
                    <AlertTriangle className="w-3 h-3" /> MERGE CONFLICT DETECTED
                  </span>
                )}
                {selectedGroup.representative_revision.doi && (
                  <span className="text-[10px] font-mono text-slate-400">
                    DOI: {selectedGroup.representative_revision.doi}
                  </span>
                )}
              </div>

              <h2 className="text-base sm:text-lg font-bold text-white leading-snug">
                {selectedGroup.representative_revision.title}
              </h2>

              <div className="text-xs text-slate-400 font-mono flex items-center gap-4">
                <span>{(selectedGroup.representative_revision.authors || []).join(", ")}</span>
                <span>•</span>
                <span>{selectedGroup.representative_revision.journal} ({selectedGroup.representative_revision.year})</span>
              </div>
            </div>

            {/* PICO Legend */}
            <div className="flex items-center gap-3 text-[11px] font-mono">
              <span className="text-slate-500 font-semibold">PICO Highlights:</span>
              <span className="px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/80">P • Population</span>
              <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/80">I • Intervention</span>
              <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/80">C • Comparator</span>
              <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">O • Outcome</span>
            </div>

            {/* Abstract Text Surface */}
            <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800/80 leading-relaxed text-slate-200 text-sm font-sans select-text">
              {selectedGroup.representative_revision.abstract_text || (
                <em className="text-slate-500">No abstract available for this record. Manual review required.</em>
              )}
            </div>

            {/* Review Decision Actions */}
            <div className="pt-4 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleDecision("include")}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>Include Paper</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleDecision("exclude", "Animal Study")}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-xs transition"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  <span>Exclude (Animal)</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleDecision("exclude", "Simulation Only")}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-800/80 hover:bg-red-700 text-slate-200 font-semibold text-xs transition"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  <span>Exclude (Simulation)</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleDecision("maybe", "Unclear Eligibility")}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 font-medium text-xs transition"
                >
                  <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                  <span>Maybe</span>
                </button>
              </div>

              <button
                type="button"
                onClick={() => setDecisionFeedback("Decision reverted to prior state.")}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 text-xs transition font-mono border border-slate-800"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Undo</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
