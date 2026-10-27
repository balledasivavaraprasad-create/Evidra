import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { History, GitCommit, RotateCcw, AlertTriangle, Layers, Clock } from "lucide-react";
import { NotImplementedNotice } from "../../components/NotImplementedNotice";

export const HistoryPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [restoreFeedback, setRestoreFeedback] = useState<string | null>(null);

  const mockSnapshots = [
    {
      revision_id: "rev-002",
      query_version: "q-v2",
      total_records: 38,
      included: 14,
      excluded: 22,
      conflicts: 1,
      created_at: "2026-10-27T10:15:00Z",
      description: "Added expanded search terms for metformin monotherapy in diabetes.",
      diff: { added: 6, removed: 0, merged: 2 },
    },
    {
      revision_id: "rev-001",
      query_version: "q-v1",
      total_records: 32,
      included: 12,
      excluded: 20,
      conflicts: 0,
      created_at: "2026-10-27T08:30:00Z",
      description: "Initial PubMed search ingestion.",
      diff: { added: 32, removed: 0, merged: 0 },
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <History className="w-5 h-5 text-cyan-400" />
          <span>Corpus Version History & Snapshot Restore</span>
        </h1>
        <p className="text-slate-400 text-xs">
          Immutable review loop: inspect added/removed records across iterations and restore historic states.
        </p>
      </div>

      <NotImplementedNotice
        featureName="Version Snapshots & Decision Lineage Services"
        targetTask="D05"
        taskOwner="dev-D"
        description="Level 2 immutable snapshots, decision cutoffs, and exact SQLite restoration are implemented in D05 (Bonus). This preview illustrates the diff and rollback controls."
      />

      {restoreFeedback && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 text-xs font-mono flex items-center justify-between">
          <span>{restoreFeedback}</span>
          <button onClick={() => setRestoreFeedback(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Snapshot Timeline */}
      <div className="space-y-4">
        {mockSnapshots.map((snap) => (
          <div key={snap.revision_id} className="glass-panel p-6 space-y-4 border-slate-800">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                  <GitCommit className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">{snap.revision_id}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      Query: {snap.query_version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{snap.description}</p>
                </div>
              </div>

              <div className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {new Date(snap.created_at).toLocaleString()}
              </div>
            </div>

            {/* Metrics and Diff */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-500 block text-[10px]">TOTAL PAPERS</span>
                <span className="text-white font-bold text-sm">{snap.total_records}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-500 block text-[10px]">INCLUDED</span>
                <span className="text-emerald-400 font-bold text-sm">{snap.included}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-500 block text-[10px]">EXCLUDED</span>
                <span className="text-red-400 font-bold text-sm">{snap.excluded}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-500 block text-[10px]">DIFF (+/-)</span>
                <span className="text-cyan-400 font-bold text-sm">+{snap.diff.added} added</span>
              </div>
            </div>

            {/* Actions */}
            <div className="pt-2 flex items-center justify-between">
              <div className="text-[11px] text-slate-400">
                Restoring reopens this exact saved partition without re-querying PubMed.
              </div>
              <button
                type="button"
                onClick={() => setRestoreFeedback(`Restored workspace to historical snapshot ${snap.revision_id}.`)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 font-medium text-xs transition border border-slate-700"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Restore Snapshot</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
