import React, { useEffect, useState, useTransition } from "react";
import { ErrorState, LoadingRegion, SkeletonCard, SkeletonStatRow, SkeletonTable, SkeletonTimeline } from "../../components/Feedback";
import { useParams } from "react-router-dom";
import {
  History,
  GitCommit,
  RotateCcw,
  AlertTriangle,
  Layers,
  Clock,
  ArrowRight,
  GitCompare,
  ShieldAlert,
  CheckCircle2,
  FileText,
  Fingerprint,
  RefreshCw,
  Sparkles,
  GitMerge,
  Split,
} from "lucide-react";
import {
  api,
  type CorpusRevisionResponse,
  type CorpusDiffResponse,
  type PaperGroupSummary,
  type SnapshotRestoreRequest,
} from "../../api/client";
import { ConflictResolutionModal } from "../conflicts/ConflictResolutionModal";
import { SearchEvolutionView } from "../search-evolution/SearchEvolutionView";

type ActiveTab = "timeline" | "diff" | "search_evolution" | "conflicts";

interface HistoryPageProps {
  initialTab?: ActiveTab;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({ initialTab = "timeline" }) => {
  const { id: workspaceId } = useParams<{ id: string }>();
  const activeWorkspaceId = workspaceId ?? "";

  const [activeTab, setActiveTab] = useState<ActiveTab>(initialTab);
  const [revisions, setRevisions] = useState<CorpusRevisionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Restore state
  const [selectedSnapshotForRestore, setSelectedSnapshotForRestore] = useState<CorpusRevisionResponse | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);

  // Diff state
  const [baseRevId, setBaseRevId] = useState<string>("");
  const [targetRevId, setTargetRevId] = useState<string>("");
  const [diffResult, setDiffResult] = useState<CorpusDiffResponse | null>(null);
  const [isDiffLoading, setIsDiffLoading] = useState(false);

  // Conflicts state
  const [conflictedGroups, setConflictedGroups] = useState<PaperGroupSummary[]>([]);
  const [activeConflictGroup, setActiveConflictGroup] = useState<PaperGroupSummary | null>(null);

  const [, startTransition] = useTransition();

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const revs = await api.revisions.list(activeWorkspaceId);
      setRevisions(revs);
      if (revs.length > 0) {
        if (!targetRevId) setTargetRevId(revs[0].id);
        if (revs.length > 1 && !baseRevId) setBaseRevId(revs[1].id);

        // Fetch conflicted groups from latest revision
        const groups = await api.revisions.listGroups(revs[0].id, "conflict");
        setConflictedGroups(groups);
      }
    } catch (err: unknown) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeWorkspaceId]);

  // Load diff when base and target change
  const handleComputeDiff = async (baseId: string, targetId: string) => {
    if (!baseId || !targetId || baseId === targetId) {
      setDiffResult(null);
      return;
    }
    setIsDiffLoading(true);
    try {
      const diff = await api.revisions.getDiff(targetId, baseId);
      setDiffResult(diff);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to compute corpus diff";
      setFeedback({ type: "error", message: msg });
    } finally {
      setIsDiffLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "diff" && baseRevId && targetRevId && baseRevId !== targetRevId) {
      handleComputeDiff(baseRevId, targetRevId);
    }
  }, [activeTab, baseRevId, targetRevId]);

  const handleExecuteRestore = async () => {
    if (!selectedSnapshotForRestore) return;
    setIsRestoring(true);
    try {
      const payload: SnapshotRestoreRequest = {
        snapshot_id: selectedSnapshotForRestore.id,
        mode: "exact_snapshot",
      };
      const restored = await api.revisions.restore(activeWorkspaceId, payload);
      setFeedback({
        type: "success",
        message: `Successfully restored workspace to exact snapshot ${restored.id} (${restored.group_count} groups, ${restored.record_count} records).`,
      });
      setSelectedSnapshotForRestore(null);
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to restore snapshot";
      setFeedback({ type: "error", message: msg });
    } finally {
      setIsRestoring(false);
    }
  };

  return (
    <div className="space-y-6 pb-16 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-5 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-start gap-3">
            <div className="p-2 mt-1 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <History className="w-5 h-5" />
            </div>
            <div className="space-y-1.5">
              <h1 className="text-xl font-bold text-white flex flex-wrap items-center gap-x-3 gap-y-1">
                Version History & Exact Snapshot Restore
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  Level 2 Offline Core
                </span>
              </h1>
              <p className="text-sm text-slate-400 max-w-[70ch]">
                Inspect immutable review iterations, review cross-version diffs, and exact-restore previous states without re-fetching literature.
              </p>
            </div>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800 self-start xl:self-auto shrink-0 whitespace-nowrap">
          <button
            type="button"
            onClick={() => startTransition(() => setActiveTab("timeline"))}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === "timeline"
                ? "bg-slate-800 text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <GitCommit className="w-3.5 h-3.5" />
            <span>Timeline</span>
          </button>
          <button
            type="button"
            onClick={() => startTransition(() => setActiveTab("diff"))}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === "diff"
                ? "bg-slate-800 text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>Corpus Diff</span>
          </button>
          <button
            type="button"
            onClick={() => startTransition(() => setActiveTab("search_evolution"))}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === "search_evolution"
                ? "bg-slate-800 text-indigo-400 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Search Evolution</span>
          </button>
          <button
            type="button"
            onClick={() => startTransition(() => setActiveTab("conflicts"))}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === "conflicts"
                ? "bg-slate-800 text-amber-400 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Conflicts ({conflictedGroups.length})</span>
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-3.5 rounded-xl border text-xs font-medium flex items-center justify-between ${
            feedback.type === "success"
              ? "bg-emerald-950/50 border-emerald-800/80 text-emerald-300"
              : "bg-red-950/50 border-red-800/80 text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-slate-400 hover:text-white text-xs px-2 py-0.5"
          >
            ✕
          </button>
        </div>
      )}

      {/* Loading & Error States (the Search Evolution tab handles its own) */}
      {isLoading && activeTab !== "search_evolution" && (
        <LoadingRegion label="Loading review snapshots">
          {activeTab === "timeline" ? <SkeletonTimeline /> : <SkeletonCard lines={4} />}
        </LoadingRegion>
      )}

      {!isLoading && error != null && activeTab !== "search_evolution" && (
        <ErrorState error={error} onRetry={loadData} what="Review history" />
      )}

      {/* TAB: SEARCH EVOLUTION */}
      {activeTab === "search_evolution" && (
        <SearchEvolutionView workspaceId={activeWorkspaceId} />
      )}

      {/* TAB 1: TIMELINE */}
      {!isLoading && error == null && activeTab === "timeline" && (
        <div className="space-y-4">
          {revisions.length === 0 ? (
            <div className="glass-panel p-12 text-center text-slate-400 space-y-3">
              <Layers className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-sm font-medium text-white">No corpus revisions published yet</p>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Execute a literature query and import records to create immutable corpus snapshots.
              </p>
            </div>
          ) : (
            revisions.map((rev, index) => {
              const isCurrent = index === 0;
              const formattedDate = rev.published_at
                ? new Date(rev.published_at).toLocaleString()
                : "Building / Draft";

              return (
                <div
                  key={rev.id}
                  className={`glass-panel p-6 space-y-4 border transition hover:border-slate-700 ${
                    isCurrent ? "border-cyan-500/30 bg-cyan-950/10 shadow-lg shadow-cyan-950/20" : "border-slate-800"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
                    <div className="flex items-start sm:items-center gap-3">
                      <div
                        className={`p-2.5 rounded-xl border ${
                          isCurrent
                            ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30"
                            : "bg-slate-800 text-slate-400 border-slate-700"
                        }`}
                      >
                        <GitCommit className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-sm font-bold text-white">{rev.id}</span>
                          {isCurrent && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold">
                              ACTIVE REVISION
                            </span>
                          )}
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            Criteria: {rev.criteria_version_id}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
                          {rev.parent_id ? (
                            <span>Parent: <code className="font-mono text-slate-300">{rev.parent_id}</code></span>
                          ) : (
                            <span className="text-emerald-400">Root Snapshot</span>
                          )}
                          <span>•</span>
                          <span>Dedup: <code className="font-mono text-slate-300">{rev.dedup_version}</code></span>
                        </div>
                      </div>
                    </div>

                    <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5 self-start sm:self-auto">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>{formattedDate}</span>
                    </div>
                  </div>

                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-500 block text-[10px] font-semibold uppercase">Paper Groups (Studies)</span>
                      <span className="text-white font-bold text-base">{rev.group_count}</span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-500 block text-[10px] font-semibold uppercase">Source Records (Papers)</span>
                      <span className="text-cyan-400 font-bold text-base">{rev.record_count}</span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 col-span-2">
                      <span className="text-slate-500 block text-[10px] font-semibold uppercase flex items-center gap-1">
                        <Fingerprint className="w-3 h-3 text-cyan-400" />
                        Deterministic Fingerprint
                      </span>
                      <span className="text-slate-300 font-mono text-[11px] truncate block mt-0.5">
                        {rev.fingerprint}
                      </span>
                    </div>
                  </div>

                  {/* Bottom Controls */}
                  <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-800/40">
                    <div className="text-[11px] text-slate-400">
                      {isCurrent ? (
                        <span className="text-cyan-400/90 font-medium">Currently serving active review queue and exports.</span>
                      ) : (
                        <span>Historical immutable state. Restoring bypasses live queries and reinstates exact partitions.</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {index > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            setBaseRevId(rev.id);
                            setTargetRevId(revisions[index - 1].id);
                            setActiveTab("diff");
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition border border-slate-700"
                        >
                          <GitCompare className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Diff vs Prior</span>
                        </button>
                      )}

                      {!isCurrent && (
                        <button
                          type="button"
                          onClick={() => setSelectedSnapshotForRestore(rev)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 font-medium text-xs transition border border-cyan-500/30 shadow-sm"
                        >
                          <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Exact Restore</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* TAB 2: STRUCTURED DIFF VISUALIZER */}
      {!isLoading && error == null && activeTab === "diff" && (
        <div className="space-y-6">
          {/* Comparison selector */}
          <div className="glass-panel p-6 border-slate-800 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-cyan-400" />
              <span>Select Revisions to Compare</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Base Revision (Historical Reference)
                </label>
                <select
                  value={baseRevId}
                  onChange={(e) => setBaseRevId(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-slate-900 border border-slate-800 text-white font-mono focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Select Base Snapshot</option>
                  {revisions.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.id} ({r.record_count} records) - {r.published_at ? new Date(r.published_at).toLocaleDateString() : "Draft"}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Target Revision (Subsequent State)
                </label>
                <select
                  value={targetRevId}
                  onChange={(e) => setTargetRevId(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-slate-900 border border-slate-800 text-white font-mono focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Select Target Snapshot</option>
                  {revisions.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.id} ({r.record_count} records) - {r.published_at ? new Date(r.published_at).toLocaleDateString() : "Draft"}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Diff Result Display */}
          {isDiffLoading && (
            <LoadingRegion label="Comparing snapshots" className="space-y-4">
              <SkeletonStatRow count={6} />
              <SkeletonTable rows={3} cols={4} />
            </LoadingRegion>
          )}

          {!isDiffLoading && diffResult && (
            <div className="space-y-4">
              {/* Diff Metric Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="glass-panel p-4 border-slate-800 text-center">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Added Records</span>
                  <span className="text-xl font-bold font-mono text-emerald-400">+{diffResult.added_records}</span>
                </div>
                <div className="glass-panel p-4 border-slate-800 text-center">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Removed Records</span>
                  <span className="text-xl font-bold font-mono text-red-400">-{diffResult.removed_records}</span>
                </div>
                <div className="glass-panel p-4 border-slate-800 text-center">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Retained Records</span>
                  <span className="text-xl font-bold font-mono text-cyan-400">{diffResult.retained_records}</span>
                </div>
                <div className="glass-panel p-4 border-slate-800 text-center">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Merged Groups</span>
                  <span className="text-xl font-bold font-mono text-indigo-400 flex items-center justify-center gap-1">
                    <GitMerge className="w-4 h-4" />
                    {diffResult.merged_groups}
                  </span>
                </div>
                <div className="glass-panel p-4 border-slate-800 text-center">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Split Groups</span>
                  <span className="text-xl font-bold font-mono text-purple-400 flex items-center justify-center gap-1">
                    <Split className="w-4 h-4" />
                    {diffResult.split_groups}
                  </span>
                </div>
                <div className="glass-panel p-4 border-slate-800 text-center">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Changed Decisions</span>
                  <span className="text-xl font-bold font-mono text-amber-400">{diffResult.changed_decisions}</span>
                </div>
              </div>

              {/* Invalidation Fingerprint Badge */}
              <div className="glass-panel p-4 border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Fingerprint className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs text-slate-300 font-medium">Deterministic Invalidation Fingerprint:</span>
                </div>
                <code className="text-xs font-mono text-cyan-300 bg-cyan-950/40 px-3 py-1 rounded-lg border border-cyan-800/40">
                  {diffResult.invalidation_fingerprint}
                </code>
              </div>

              {/* Added / Removed Record Lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="glass-panel p-5 border-slate-800 space-y-3">
                  <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Added Source Records ({(diffResult.added_record_ids || []).length})</span>
                  </h3>
                  <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-xs pr-2">
                    {(diffResult.added_record_ids || []).length === 0 ? (
                      <p className="text-slate-500 italic">No records added</p>
                    ) : (
                      (diffResult.added_record_ids || []).map((rid) => (
                        <div key={rid} className="p-1.5 rounded bg-slate-900/80 text-slate-300 border border-slate-800 truncate">
                          + {rid}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="glass-panel p-5 border-slate-800 space-y-3">
                  <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Removed Source Records ({(diffResult.removed_record_ids || []).length})</span>
                  </h3>
                  <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-xs pr-2">
                    {(diffResult.removed_record_ids || []).length === 0 ? (
                      <p className="text-slate-500 italic">No records removed</p>
                    ) : (
                      (diffResult.removed_record_ids || []).map((rid) => (
                        <div key={rid} className="p-1.5 rounded bg-slate-900/80 text-slate-300 border border-slate-800 truncate">
                          - {rid}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: ACTIVE CONFLICTS */}
      {!isLoading && error == null && activeTab === "conflicts" && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 text-amber-300 text-xs flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
            <p>
              Groups with conflicting decisions inherited from merges or splits are barred from included export until deliberately resolved with reviewer rationale.
            </p>
          </div>

          {conflictedGroups.length === 0 ? (
            <div className="glass-panel p-12 text-center text-slate-400 space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
              <p className="text-sm font-semibold text-white">Zero Active Conflicts</p>
              <p className="text-xs text-slate-500">
                All merged groups and study splits have unanimous human decisions.
              </p>
            </div>
          ) : (
            conflictedGroups.map((grp) => (
              <div key={grp.id} className="glass-panel p-6 border-amber-500/30 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-amber-400">{grp.id}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {grp.member_count} duplicate records
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-white">
                      {grp.representative_revision.title}
                    </h3>
                  </div>

                  <button
                    type="button"
                    onClick={() => setActiveConflictGroup(grp)}
                    className="shrink-0 px-3.5 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-semibold transition"
                  >
                    Resolve Conflict
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Exact Restore Confirmation Dialog */}
      {selectedSnapshotForRestore && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="glass-panel w-full max-w-lg p-6 rounded-2xl border-cyan-500/40 shadow-2xl space-y-5">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
              <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <RotateCcw className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Confirm Exact Snapshot Restore</h3>
                <p className="text-xs text-slate-400">Reopen historical snapshot without network queries</p>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1 font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Target Snapshot:</span>
                  <span className="text-white font-bold">{selectedSnapshotForRestore.id}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Paper Groups:</span>
                  <span className="text-cyan-400">{selectedSnapshotForRestore.group_count}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Source Records:</span>
                  <span className="text-cyan-400">{selectedSnapshotForRestore.record_count}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Criteria Version:</span>
                  <span className="text-slate-300">{selectedSnapshotForRestore.criteria_version_id}</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/40 text-cyan-300 leading-relaxed">
                <strong>Offline Invariant Guarantee:</strong> This action restores historical record revisions, deduplication partition, and representatives exactly from saved SQLite tables. Zero live API calls will be made.
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setSelectedSnapshotForRestore(null)}
                disabled={isRestoring}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteRestore}
                disabled={isRestoring}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition shadow-lg shadow-cyan-600/30 disabled:opacity-50"
              >
                {isRestoring ? "Restoring Snapshot..." : "Restore Snapshot"}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Active Conflict Resolution Modal */}
      {activeConflictGroup && (
        <ConflictResolutionModal
          conflictId={`conf-${activeConflictGroup.id}`}
          groupId={activeConflictGroup.id}
          paperTitle={activeConflictGroup.representative_revision.title}
          expectedVersion={1}
          isOpen={true}
          onClose={() => setActiveConflictGroup(null)}
          onResolved={() => {
            setFeedback({
              type: "success",
              message: `Conflict for group ${activeConflictGroup.id} was successfully resolved.`,
            });
            loadData();
          }}
        />
      )}
    </div>
  );
};
