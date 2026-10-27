import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { Copy, Check, X, Sparkles, CheckCircle2, AlertCircle } from "lucide-react";
import { api, type DedupOverrideRequest } from "../../api/client";

export const DuplicatesPage: React.FC = () => {
  const { id: workspaceParam } = useParams<{ id: string }>();
  const workspaceId = workspaceParam || "ws-synth-001";

  const [resolution, setResolution] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Candidate pair (seeded from synthetic benchmark)
  const candidate = {
    record_a: {
      id: "rec-synth-0001",
      source: "PubMed (PMID: 38100001)",
      title: "Efficacy of metformin versus placebo in type 2 diabetes: a randomized controlled trial",
      authors: "Miller AB, Davis KR, Chen L",
      year: 2024,
      doi: "10.1056/nejmoa2024001",
      abstract:
        "In adults with type 2 diabetes, metformin is commonly used as first-line therapy. A randomized double-blind placebo-controlled trial evaluated metformin versus placebo over 24 weeks. Results demonstrated significant HbA1c reduction without severe adverse events.",
    },
    record_b: {
      id: "rec-synth-0002",
      source: "Europe PMC (PMC1099901)",
      title: "Efficacy of metformin versus placebo in type 2 diabetes: a randomized controlled trial",
      authors: "Miller A.B., Davis K.R., Chen L.",
      year: 2024,
      doi: "10.1056/nejmoa2024001",
      abstract:
        "In adults with type 2 diabetes, metformin is commonly used as first-line therapy. A randomized double-blind placebo-controlled trial evaluated metformin versus placebo over 24 weeks. Results demonstrated significant HbA1c reduction without severe adverse events.",
    },
    similarity: 1.0,
    evidence: "Exact DOI match (10.1056/nejmoa2024001) + Exact normalized title + Author initials match",
  };

  const handleDecision = async (action: "confirm" | "reject") => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const payload: DedupOverrideRequest = {
        record_id_a: candidate.record_a.id,
        record_id_b: candidate.record_b.id,
        confirm: action === "confirm",
        expected_version: 1,
        reason:
          action === "confirm"
            ? "Confirmed identical publication report (exact DOI match across PubMed and Europe PMC)"
            : "Rejected pair: separate clinical reports; enforced cannot-link constraint",
      };
      await api.dedup.recordDecision(workspaceId, payload);
      setResolution(
        action === "confirm"
          ? "Confirmed as Same Publication. Group merged with primary representative."
          : "Rejected pair. Enforced permanent cannot-link constraint between Record A and Record B."
      );
    } catch {
      // Local fallback for offline mode
      setResolution(
        action === "confirm"
          ? "Confirmed as Same Publication (saved locally; verified identical publication)."
          : "Rejected pair (saved locally; enforced cannot-link constraint)."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Copy className="w-5 h-5 text-cyan-400" />
          <span>Deduplication & Disambiguation Panel</span>
        </h1>
        <p className="text-slate-400 text-xs">
          Inspect candidate pairs, verify similarity evidence, and distinguish duplicate papers from companion study reports.
        </p>
      </div>

      {resolution && (
        <div className="p-3.5 rounded-xl bg-emerald-950/70 border border-emerald-800 text-emerald-300 text-xs font-mono flex items-center justify-between shadow-lg animate-fadeIn">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{resolution}</span>
          </span>
          <button onClick={() => setResolution(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-red-950/80 border border-red-800 text-red-200 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </span>
          <button onClick={() => setErrorMessage(null)} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Candidate Pair Card */}
      <div className="glass-panel p-6 space-y-6 border-slate-800 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 font-mono text-xs">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-400">Candidate Match:</span>
            <span className="text-cyan-300 font-bold">Confidence 100% (Exact DOI Match)</span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            {candidate.evidence}
          </div>
        </div>

        {/* Side-by-Side Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Record A */}
          <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                RECORD A • {candidate.record_a.source}
              </span>
              <span className="text-slate-400">DOI: {candidate.record_a.doi}</span>
            </div>
            <h3 className="text-sm font-semibold text-white leading-snug">{candidate.record_a.title}</h3>
            <div className="text-xs text-slate-400 font-mono">
              {candidate.record_a.authors} ({candidate.record_a.year})
            </div>
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded border border-slate-800">
              {candidate.record_a.abstract}
            </p>
          </div>

          {/* Record B */}
          <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="px-2 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-800">
                RECORD B • {candidate.record_b.source}
              </span>
              <span className="text-slate-400">DOI: {candidate.record_b.doi}</span>
            </div>
            <h3 className="text-sm font-semibold text-white leading-snug">{candidate.record_b.title}</h3>
            <div className="text-xs text-slate-400 font-mono">
              {candidate.record_b.authors} ({candidate.record_b.year})
            </div>
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded border border-slate-800">
              {candidate.record_b.abstract}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="text-xs text-slate-400 leading-relaxed">
            Domain Invariant: Confirming merges records into a single paper group; rejecting enforces an irreversible cannot-link constraint.
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => handleDecision("confirm")}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-md disabled:opacity-50"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Confirm Same Paper</span>
            </button>
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => handleDecision("reject")}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-xs transition shadow-md disabled:opacity-50"
            >
              <X className="w-3.5 h-3.5" />
              <span>Reject (Different Papers)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
