import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { Copy, Check, X, AlertCircle, Sparkles, ArrowRight } from "lucide-react";
import { NotImplementedNotice } from "../../components/NotImplementedNotice";

export const DuplicatesPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [resolution, setResolution] = useState<string | null>(null);

  const mockCandidate = {
    record_a: {
      id: "rec-synth-0001",
      source: "PubMed (PMID: 38100001)",
      title: "Efficacy of metformin versus placebo in type 2 diabetes: a randomized controlled trial",
      authors: "Miller AB, Davis KR, Chen L",
      year: 2024,
      doi: "10.1056/nejmoa2024001",
      abstract: "In adults with type 2 diabetes, metformin is commonly used as first-line therapy. A randomized double-blind placebo-controlled trial evaluated metformin versus placebo over 24 weeks.",
    },
    record_b: {
      id: "rec-synth-0002",
      source: "Europe PMC (PMC1099901)",
      title: "Efficacy of metformin versus placebo in type 2 diabetes: a randomized controlled trial",
      authors: "Miller A.B., Davis K.R., Chen L.",
      year: 2024,
      doi: "10.1056/nejmoa2024001",
      abstract: "In adults with type 2 diabetes, metformin is commonly used as first-line therapy. A randomized double-blind placebo-controlled trial evaluated metformin versus placebo over 24 weeks.",
    },
    similarity: 1.0,
    evidence: "Exact DOI match (10.1056/nejmoa2024001) + Exact normalized title + Author initials match",
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

      <NotImplementedNotice
        featureName="Deterministic Deduplication Engine Integration"
        targetTask="B01"
        taskOwner="dev-B"
        description="Dev-B is implementing the pure deduplication matching engine in B01. This screen demonstrates candidate side-by-side inspection and cannot-link controls."
      />

      {resolution && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 text-xs font-mono flex items-center justify-between">
          <span>{resolution}</span>
          <button onClick={() => setResolution(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Candidate Pair Card */}
      <div className="glass-panel p-6 space-y-6 border-slate-800">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="text-slate-400">Candidate Match:</span>
            <span className="text-cyan-300 font-bold">Confidence 100% (Exact DOI)</span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            {mockCandidate.evidence}
          </div>
        </div>

        {/* Side-by-Side Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Record A */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                RECORD A • {mockCandidate.record_a.source}
              </span>
              <span className="text-slate-400">DOI: {mockCandidate.record_a.doi}</span>
            </div>
            <h3 className="text-sm font-semibold text-white leading-snug">{mockCandidate.record_a.title}</h3>
            <div className="text-xs text-slate-400 font-mono">
              {mockCandidate.record_a.authors} ({mockCandidate.record_a.year})
            </div>
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded border border-slate-800">
              {mockCandidate.record_a.abstract}
            </p>
          </div>

          {/* Record B */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="px-2 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-800">
                RECORD B • {mockCandidate.record_b.source}
              </span>
              <span className="text-slate-400">DOI: {mockCandidate.record_b.doi}</span>
            </div>
            <h3 className="text-sm font-semibold text-white leading-snug">{mockCandidate.record_b.title}</h3>
            <div className="text-xs text-slate-400 font-mono">
              {mockCandidate.record_b.authors} ({mockCandidate.record_b.year})
            </div>
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded border border-slate-800">
              {mockCandidate.record_b.abstract}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            Confirming merges into single paper group; rejecting creates a strict cannot-link constraint.
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setResolution("Confirmed as Same Publication. Group merged with primary representative.")}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Confirm Same Paper</span>
            </button>
            <button
              type="button"
              onClick={() => setResolution("Rejected pair. Created permanent cannot-link constraint between Record A and B.")}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-medium text-xs transition"
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
