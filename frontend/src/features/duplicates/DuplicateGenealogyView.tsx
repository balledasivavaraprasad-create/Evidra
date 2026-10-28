import React, { useState, useEffect } from "react";
import {
  api,
  DuplicateGroupGenealogyResponse,
  DuplicateReconcileRequest,
  DuplicateSplitRequest,
  DuplicateReverseMergeRequest,
  EligibilityStatus,
  DuplicateMatchSignalDetail,
} from "../../api/client";

interface DuplicateGenealogyViewProps {
  workspaceId: string;
  groupId: string;
  onStateChanged?: () => void;
  onRefreshNeeded?: () => void;
}

export const DuplicateGenealogyView: React.FC<DuplicateGenealogyViewProps> = ({
  workspaceId,
  groupId,
  onStateChanged,
  onRefreshNeeded,
}) => {
  const [data, setData] = useState<DuplicateGroupGenealogyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [reconcileModalOpen, setReconcileModalOpen] = useState(false);
  const [chosenDecision, setChosenDecision] = useState<EligibilityStatus>("include");
  const [reconcileReason, setReconcileReason] = useState("");
  const [isReconciling, setIsReconciling] = useState(false);

  const [splitModalOpen, setSplitModalOpen] = useState(false);
  const [selectedSplitRecords, setSelectedSplitRecords] = useState<string[]>([]);
  const [splitReason, setSplitReason] = useState("");
  const [isSplitting, setIsSplitting] = useState(false);

  const [activeTab, setActiveTab] = useState<"genealogy" | "provenance" | "history">("genealogy");

  const notifyChange = () => {
    onStateChanged?.();
    onRefreshNeeded?.();
  };

  const fetchGenealogy = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.genealogy.getGroupGenealogy(workspaceId, groupId);
      setData(resp);
    } catch (err: any) {
      console.error("Failed to load genealogy:", err);
      setError(err?.message || "Failed to load duplicate genealogy");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (workspaceId && groupId) {
      fetchGenealogy();
    }
  }, [workspaceId, groupId]);

  const handleReconcile = async () => {
    if (!reconcileReason.trim() || !data) return;
    setIsReconciling(true);
    try {
      const payload: DuplicateReconcileRequest = {
        chosen_decision: chosenDecision,
        reason: reconcileReason,
        apply_to_all_members: true,
        actor_id: "reviewer",
        expected_version: data.row_version,
      };
      const updated = await api.genealogy.reconcileConflict(workspaceId, groupId, payload);
      setData(updated);
      setReconcileModalOpen(false);
      setReconcileReason("");
      notifyChange();
    } catch (err: any) {
      alert(`Reconciliation failed: ${err.message || err}`);
    } finally {
      setIsReconciling(false);
    }
  };

  const handleSplit = async () => {
    if (selectedSplitRecords.length === 0 || !splitReason.trim() || !data) return;
    setIsSplitting(true);
    try {
      const payload: DuplicateSplitRequest = {
        source_record_ids_to_split: selectedSplitRecords,
        reason: splitReason,
        mark_as_cannot_link: true,
        actor_id: "reviewer",
        expected_version: data.row_version,
      };
      const updated = await api.genealogy.splitGroup(workspaceId, groupId, payload);
      setData(updated);
      setSplitModalOpen(false);
      setSelectedSplitRecords([]);
      setSplitReason("");
      notifyChange();
    } catch (err: any) {
      alert(`Split failed: ${err.message || err}`);
    } finally {
      setIsSplitting(false);
    }
  };

  const handleReverseMerge = async (mergeEventId: string) => {
    if (!data) return;
    if (!confirm("Are you sure you want to reverse this merge event?")) return;
    try {
      const payload: DuplicateReverseMergeRequest = {
        merge_event_id: mergeEventId,
        reason: "User requested safe reversal of duplicate merge",
        actor_id: "reviewer",
        expected_version: data.row_version,
      };
      const updated = await api.genealogy.reverseMerge(workspaceId, groupId, payload);
      setData(updated);
      notifyChange();
    } catch (err: any) {
      alert(`Reversal failed: ${err.message || err}`);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 font-mono text-sm">
        <span className="inline-block animate-spin mr-2">🔄</span>
        Loading duplicate genealogy and provenance...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-red-950/40 border border-red-800 rounded-xl text-red-300 text-xs font-mono">
        <div className="font-bold flex items-center gap-2">
          <span>❌</span> Error loading duplicate genealogy
        </div>
        <p className="mt-1 text-slate-400">{error || "No data returned"}</p>
        <button
          onClick={fetchGenealogy}
          className="mt-3 px-3 py-1.5 bg-red-800/60 hover:bg-red-700 text-white rounded text-xs"
        >
          Retry
        </button>
      </div>
    );
  }

  const members = data.members || [];
  const activeConflicts = data.active_conflicts || [];
  const fieldProvenance = data.field_provenance || [];
  const matchSignals: DuplicateMatchSignalDetail[] = data.pairwise_signals || [];
  const mergeHistory = data.merge_history || [];

  const hasConflicts = activeConflicts.length > 0;

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="glass-panel p-5 rounded-2xl border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-slate-900/60">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
              DUPLICATE GENEALOGY GROUP
            </span>
            <span className="font-mono text-xs text-slate-400">{data.group_id}</span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                data.effective_decision === "include"
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                  : data.effective_decision === "exclude"
                  ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                  : data.effective_decision === "conflict"
                  ? "bg-red-500/20 text-red-300 border-red-500/40 animate-pulse"
                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
              }`}
            >
              Status: {data.effective_decision.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {members.length} merged source records • Fingerprint: {(data.membership_fingerprint || "").slice(0, 16)}...
          </p>
        </div>

        <div className="flex items-center gap-2">
          {hasConflicts && (
            <button
              onClick={() => setReconcileModalOpen(true)}
              className="px-3 py-1.5 text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white rounded-lg shadow transition-colors flex items-center gap-1.5"
            >
              <span>⚡</span> Reconcile Conflict
            </button>
          )}
          {members.length > 1 && (
            <button
              onClick={() => {
                setSelectedSplitRecords([]);
                setSplitModalOpen(true);
              }}
              className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition-colors flex items-center gap-1"
            >
              <span>✂️</span> Split Records
            </button>
          )}
        </div>
      </div>

      {/* Decision Conflict Alert Banner */}
      {hasConflicts && (
        <div className="p-4 bg-red-950/60 border border-red-700/80 rounded-xl space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-red-300 flex items-center gap-2">
              <span>⚠️</span> Decision Conflict Detected Across Merged Records
            </h4>
            <span className="text-xs font-mono text-red-400 uppercase tracking-wider">Action Required</span>
          </div>
          {activeConflicts.map((conf, idx) => (
            <div key={idx} className="text-xs text-red-200/90 space-y-1">
              <p>{conf.explanation}</p>
              <div className="flex flex-wrap gap-2 mt-1">
                {(conf.competing_decisions || []).map((cd: any, cIdx: number) => (
                  <span
                    key={cIdx}
                    className="px-2.5 py-1 bg-red-900/40 rounded border border-red-800/60 font-mono text-[11px]"
                  >
                    {String(cd?.actor_id || cd?.actor_type || "SYSTEM")}: <strong>{String(cd?.status || cd?.decision || "UNKNOWN").toUpperCase()}</strong> {cd?.reason ? `("${cd.reason}")` : ""}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-medium">
        <button
          onClick={() => setActiveTab("genealogy")}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === "genealogy"
              ? "bg-amber-600 text-white font-bold"
              : "bg-slate-800 text-slate-400 hover:text-slate-200"
          }`}
        >
          Genealogy & Match Signals ({members.length})
        </button>
        <button
          onClick={() => setActiveTab("provenance")}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === "provenance"
              ? "bg-amber-600 text-white font-bold"
              : "bg-slate-800 text-slate-400 hover:text-slate-200"
          }`}
        >
          Field-Level Provenance ({fieldProvenance.length})
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === "history"
              ? "bg-amber-600 text-white font-bold"
              : "bg-slate-800 text-slate-400 hover:text-slate-200"
          }`}
        >
          Merge & Split Audit Trail ({mergeHistory.length})
        </button>
      </div>

      {/* Tab 1: Genealogy & Pairwise Matching Signals */}
      {activeTab === "genealogy" && (
        <div className="space-y-6">
          {/* Member Records Cards */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Merged Study Records ({members.length})
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {members.map((mem) => (
                <div
                  key={mem.source_record_id}
                  className={`p-4 rounded-xl border space-y-3 ${
                    mem.is_canonical
                      ? "bg-slate-950/70 border-amber-500/40 shadow-sm shadow-amber-500/10"
                      : "bg-slate-950/40 border-slate-800"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="px-2 py-0.5 text-[11px] font-mono font-semibold uppercase rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {mem.source_namespace} ({mem.external_id})
                    </span>
                    {mem.is_canonical && (
                      <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                        ⭐ Canonical Record
                      </span>
                    )}
                  </div>

                  <div>
                    <h5 className="text-xs font-bold text-slate-200 line-clamp-2">{mem.title}</h5>
                    <p className="text-[11px] text-slate-400 mt-1">
                      {(mem.authors || []).slice(0, 3).join(", ")} {mem.year ? `(${mem.year})` : ""} {mem.journal ? `• ${mem.journal}` : ""}
                    </p>
                  </div>

                  <div className="text-[11px] font-mono text-slate-400 flex flex-wrap gap-2 pt-1 border-t border-slate-900">
                    {mem.doi && <span>DOI: {mem.doi}</span>}
                    {mem.pmid && <span>PMID: {mem.pmid}</span>}
                  </div>

                  {/* Screening Decision of this specific record copy */}
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800/80 text-xs flex items-center justify-between">
                    <div>
                      <span className="text-slate-400 text-[10px] block uppercase font-mono">Screening Decision:</span>
                      <span
                        className={`font-bold ${
                          mem.individual_decision === "include"
                            ? "text-emerald-400"
                            : mem.individual_decision === "exclude"
                            ? "text-rose-400"
                            : "text-slate-400"
                        }`}
                      >
                        {mem.individual_decision?.toUpperCase() || "UNSCREENED"}
                      </span>
                    </div>
                    {mem.decision_source && (
                      <span className="text-[10px] font-mono text-slate-500 uppercase">
                        via {mem.decision_source}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Pairwise Candidate Match Evidence Signals */}
          {matchSignals.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-slate-800">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Matching Evidence & Similarity Signals ({matchSignals.length})
              </h4>
              <div className="space-y-2">
                {matchSignals.map((sig: DuplicateMatchSignalDetail, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-mono text-[11px]">
                        <span className="text-slate-300">{sig.record_id_a}</span>
                        <span className="text-slate-500">↔</span>
                        <span className="text-slate-300">{sig.record_id_b}</span>
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[10px]">
                          {sig.status}
                        </span>
                      </div>
                      <div className="font-bold text-amber-400 font-mono">
                        Score: {Math.round((sig.score || 0) * 100)}%
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {(sig.signals || []).map((s: string, sIdx: number) => (
                        <span
                          key={sIdx}
                          className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px] border border-slate-700"
                        >
                          ✓ {s}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Field-Level Metadata Provenance */}
      {activeTab === "provenance" && (
        <div className="space-y-3">
          <div className="text-xs text-slate-400">
            Field-by-field provenance showing which source record supplied the canonical value, with highlighted discrepancies across duplicate copies.
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Metadata Field</th>
                  <th className="py-2.5 px-3">Canonical Value</th>
                  <th className="py-2.5 px-3">Source</th>
                  <th className="py-2.5 px-3">Alternative Duplicate Values</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {fieldProvenance.map((fItem) => (
                  <tr
                    key={fItem.field_name}
                    className={`hover:bg-slate-800/20 ${fItem.has_discrepancy ? "bg-amber-950/10" : ""}`}
                  >
                    <td className="py-2.5 px-3 font-mono font-medium text-slate-300">
                      {fItem.field_name}
                      {fItem.has_discrepancy && (
                        <span className="ml-2 px-1.5 py-0.5 rounded text-[9px] bg-amber-500/20 text-amber-400 border border-amber-500/30">
                          Discrepancy
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-200 font-medium max-w-sm">
                      {fItem.canonical_value || <span className="text-slate-600 italic">None</span>}
                    </td>
                    <td className="py-2.5 px-3 uppercase font-mono text-[11px] text-slate-400">
                      {fItem.canonical_source}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 max-w-xs">
                      {(fItem.alternatives || []).length === 0 ? (
                        <span className="text-slate-600 italic">Identical across all records</span>
                      ) : (
                        <div className="space-y-1">
                          {(fItem.alternatives || []).map((alt: any, aIdx: number) => (
                            <div key={aIdx} className="text-[11px] font-mono">
                              <span className="text-slate-500 uppercase">{String(alt?.source || "Source")}:</span>{" "}
                              <span className="text-slate-300">{String(alt?.value || "None")}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Merge and Split Audit Trail */}
      {activeTab === "history" && (
        <div className="space-y-3">
          <div className="text-xs text-slate-400">
            Immutable audit log of all automated deduplication passes, human merge overrides, splits, and reversals.
          </div>

          {mergeHistory.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-xs font-mono">
              No historical merge events recorded for this group.
            </div>
          ) : (
            <div className="space-y-3">
              {mergeHistory.map((ev) => (
                <div
                  key={ev.event_id}
                  className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-800 text-slate-300">
                        {ev.operation}
                      </span>
                      <span className="font-mono text-slate-400 text-[11px]">{ev.timestamp}</span>
                    </div>

                    {ev.can_reverse ? (
                      <button
                        onClick={() => handleReverseMerge(ev.event_id)}
                        className="px-2.5 py-1 text-[11px] font-bold bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-600/60 rounded transition-colors"
                      >
                        ↩ Safe Reverse Merge
                      </button>
                    ) : (
                      <span className="text-[11px] font-mono text-slate-500">
                        {ev.is_reversed ? "Already Reversed" : "Non-Reversible"}
                      </span>
                    )}
                  </div>

                  {ev.reason && (
                    <p className="text-slate-400 italic font-mono text-[11px]">
                      Reason: "{ev.reason}"
                    </p>
                  )}

                  {!ev.can_reverse && (ev.reversal_blockers || []).length > 0 && (
                    <div className="text-[10px] text-slate-500 italic">
                      Note: {(ev.reversal_blockers || []).join(" ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reconcile Modal */}
      {reconcileModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>⚡</span> Reconcile Duplicate Decision Conflict
              </h4>
              <button
                onClick={() => setReconcileModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              One or more merged records in this duplicate group have conflicting screening decisions (e.g., Include vs Exclude). Select an authoritative decision for the unified study group.
            </p>

            <div className="space-y-2">
              <label className="text-xs text-slate-400 block font-medium">Reconciled Decision:</label>
              <div className="grid grid-cols-3 gap-2">
                {(["include", "exclude", "maybe"] as EligibilityStatus[]).map((status) => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => setChosenDecision(status)}
                    className={`py-2 text-xs font-bold uppercase rounded-lg border transition-colors ${
                      chosenDecision === status
                        ? status === "include"
                          ? "bg-emerald-600 text-white border-emerald-500 shadow-md"
                          : status === "exclude"
                          ? "bg-rose-600 text-white border-rose-500 shadow-md"
                          : "bg-amber-600 text-white border-amber-500 shadow-md"
                        : "bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700"
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-slate-400 block font-medium">
                Scientific Rationale & Audit Note:
              </label>
              <textarea
                value={reconcileReason}
                onChange={(e) => setReconcileReason(e.target.value)}
                placeholder="Explain why this decision is chosen (e.g. 'Both records describe RCT population meeting criteria')."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 h-24"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setReconcileModalOpen(false)}
                className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!reconcileReason.trim() || isReconciling}
                onClick={handleReconcile}
                className="px-4 py-1.5 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg shadow disabled:opacity-50 transition-colors"
              >
                {isReconciling ? "Reconciling..." : "Save Authoritative Decision"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Modal */}
      {splitModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>✂️</span> Separate Records from Duplicate Group
              </h4>
              <button
                onClick={() => setSplitModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                ✕
              </button>
            </div>

            <div className="text-xs text-slate-300">
              Select which member records to separate into an independent study group:
            </div>

            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {members.map((m) => (
                <label
                  key={m.source_record_id}
                  className="flex items-center gap-2 p-2 rounded bg-slate-950/60 border border-slate-800 text-xs cursor-pointer hover:bg-slate-800/40"
                >
                  <input
                    type="checkbox"
                    checked={selectedSplitRecords.includes(m.source_record_id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedSplitRecords([...selectedSplitRecords, m.source_record_id]);
                      } else {
                        setSelectedSplitRecords(selectedSplitRecords.filter((id) => id !== m.source_record_id));
                      }
                    }}
                    className="rounded border-slate-700 bg-slate-900 text-amber-500 focus:ring-0"
                  />
                  <div className="truncate">
                    <span className="font-mono text-slate-400 uppercase text-[10px] mr-1.5">
                      [{m.source_namespace}]
                    </span>
                    <span className="text-slate-200">{m.title}</span>
                  </div>
                </label>
              ))}
            </div>

            <div className="space-y-2">
              <label className="text-xs text-slate-400 block font-medium">Split Rationale:</label>
              <textarea
                value={splitReason}
                onChange={(e) => setSplitReason(e.target.value)}
                placeholder="Explain why these records are distinct (e.g. 'Companion trial phase with different outcome endpoints')."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 h-20"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setSplitModalOpen(false)}
                className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={selectedSplitRecords.length === 0 || !splitReason.trim() || isSplitting}
                onClick={handleSplit}
                className="px-4 py-1.5 text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white rounded-lg shadow disabled:opacity-50 transition-colors"
              >
                {isSplitting ? "Splitting..." : "Confirm Split & Protect"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default DuplicateGenealogyView;