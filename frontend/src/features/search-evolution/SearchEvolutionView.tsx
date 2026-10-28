import React, { useEffect, useState, useTransition } from "react";
import {
  Clock,
  GitCompare,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileText,
  Search,
  ArrowRight,
  Filter,
  Layers,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  History,
  ShieldAlert,
} from "lucide-react";
import {
  api,
  type SearchEvolutionVersionSummary,
  type SearchEvolutionDiffResponse,
  type SearchEvolutionRecordDiff,
  type SearchEvolutionCategory,
} from "../../api/client";

interface SearchEvolutionViewProps {
  workspaceId: string;
}

export const SearchEvolutionView: React.FC<SearchEvolutionViewProps> = ({ workspaceId }) => {
  const [versions, setVersions] = useState<SearchEvolutionVersionSummary[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Comparison selection
  const [baseVersionId, setBaseVersionId] = useState<string>("");
  const [targetVersionId, setTargetVersionId] = useState<string>("");
  const [diffResult, setDiffResult] = useState<SearchEvolutionDiffResponse | null>(null);
  const [isLoadingDiff, setIsLoadingDiff] = useState(false);

  // Filtering & expanded states
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string>("all");
  const [expandedRecordIds, setExpandedRecordIds] = useState<Set<string>>(new Set());

  // Restore Modal State
  const [restoreModalVersion, setRestoreModalVersion] = useState<SearchEvolutionVersionSummary | null>(null);
  const [restoreReason, setRestoreReason] = useState<string>("");
  const [isRestoring, setIsRestoring] = useState(false);

  const [, startTransition] = useTransition();

  const loadVersions = async (autoSelect = false) => {
    setIsLoadingVersions(true);
    setError(null);
    try {
      const data = await api.searchEvolution.listVersions(workspaceId);
      setVersions(data);
      if (data.length > 0 && (autoSelect || !targetVersionId)) {
        setTargetVersionId(data[0].id);
        if (data.length > 1) {
          setBaseVersionId(data[1].id);
        } else {
          setBaseVersionId("");
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load search evolution history";
      setError(msg);
    } finally {
      setIsLoadingVersions(false);
    }
  };

  useEffect(() => {
    loadVersions(true);
  }, [workspaceId]);

  // Load Diff when target or base changes
  useEffect(() => {
    if (!targetVersionId) return;

    let isMounted = true;
    setIsLoadingDiff(true);

    api.searchEvolution
      .getDiff(workspaceId, targetVersionId, baseVersionId || undefined)
      .then((diff) => {
        if (isMounted) {
          setDiffResult(diff);
          setIsLoadingDiff(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to compute search diff";
          setError(msg);
          setIsLoadingDiff(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [workspaceId, targetVersionId, baseVersionId]);

  const handleRestore = async () => {
    if (!restoreModalVersion) return;
    setIsRestoring(true);
    try {
      const res = await api.searchEvolution.restoreVersion(workspaceId, restoreModalVersion.id, {
        reason: restoreReason.trim() || undefined,
        actor_id: "researcher",
      });
      setFeedback({
        type: "success",
        message: res.message || `Successfully restored Version ${restoreModalVersion.sequence}`,
      });
      setRestoreModalVersion(null);
      setRestoreReason("");
      // Reload versions and set new latest as target
      await loadVersions(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to restore search configuration";
      setFeedback({ type: "error", message: msg });
    } finally {
      setIsRestoring(false);
    }
  };

  const toggleRecordExpand = (recordId: string) => {
    setExpandedRecordIds((prev) => {
      const next = new Set(prev);
      if (next.has(recordId)) {
        next.delete(recordId);
      } else {
        next.add(recordId);
      }
      return next;
    });
  };

  // Filtered records
  const filteredRecords = (diffResult?.records || []).filter((rec) => {
    if (activeCategoryFilter === "all") return true;
    return rec.category === activeCategoryFilter;
  });

  const getCategoryBadge = (cat: SearchEvolutionCategory) => {
    switch (cat) {
      case "newly_discovered":
        return (
          <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            Newly Discovered
          </span>
        );
      case "repeated":
        return (
          <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
            Previously Known (Repeated)
          </span>
        );
      case "missing_from_newer":
        return (
          <span
            className="px-2 py-0.5 text-[11px] font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/30"
            title="Absent from this search query execution, but retained in review project without deletion"
          >
            No Longer Returned
          </span>
        );
      case "metadata_changed":
        return (
          <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
            Metadata Changed
          </span>
        );
      case "conflict":
        return (
          <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
            Conflict
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-slate-800 text-slate-300">
            {cat}
          </span>
        );
    }
  };

  const getScreeningBadge = (rec: SearchEvolutionRecordDiff) => {
    const decision = rec.screening_decision;
    if (decision === "include") {
      return (
        <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          Included {rec.screening_preserved_from_version_id && "(Preserved)"}
        </span>
      );
    }
    if (decision === "exclude") {
      return (
        <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">
          Excluded {rec.screening_preserved_from_version_id && "(Preserved)"}
        </span>
      );
    }
    if (decision === "maybe") {
      return (
        <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
          Maybe {rec.screening_preserved_from_version_id && "(Preserved)"}
        </span>
      );
    }
    if (decision === "conflict") {
      return (
        <span className="px-2 py-0.5 text-[11px] font-semibold rounded bg-purple-500/20 text-purple-300 border border-purple-500/40">
          Conflict
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-[11px] font-medium rounded bg-slate-800 text-slate-400 border border-slate-700">
        Unscreened
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-bold text-white">Search Evolution Time Machine</h2>
              <span className="px-2 py-0.5 text-[10px] font-mono font-semibold uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded">
                SLR Versioning
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Understand how your systematic review's search strategy and retrieved evidence evolve over time.
              Identify newly discovered records, track metadata changes, preserve screening decisions across runs,
              and safely restore prior search configurations non-destructively.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => loadVersions(false)}
              disabled={isLoadingVersions}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isLoadingVersions ? "animate-spin" : ""}`} />
              <span>Refresh History</span>
            </button>
          </div>
        </div>

        {feedback && (
          <div
            className={`mt-4 p-3 rounded-lg text-xs flex items-center justify-between ${
              feedback.type === "success"
                ? "bg-emerald-950/40 border border-emerald-500/40 text-emerald-300"
                : "bg-rose-950/40 border border-rose-500/40 text-rose-300"
            }`}
          >
            <div className="flex items-center gap-2">
              {feedback.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
            <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-white text-xs">
              Dismiss
            </button>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 rounded-lg text-xs bg-rose-950/40 border border-rose-500/40 text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Version Selector Ribbon */}
      {versions.length === 0 && !isLoadingVersions ? (
        <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-xl">
          <History className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-300">No Search Versions Recorded</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            Construct and execute search queries in the Query Builder. Each executed search version will appear here for longitudinal comparison.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Version History Timeline */}
          <div className="lg:col-span-1 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span>Search Versions ({versions.length})</span>
              </h3>
            </div>

            <div className="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
              {versions.map((ver) => {
                const isTarget = ver.id === targetVersionId;
                const isBase = ver.id === baseVersionId;

                return (
                  <div
                    key={ver.id}
                    className={`p-3.5 rounded-xl border transition-all text-xs cursor-pointer ${
                      isTarget
                        ? "bg-indigo-950/40 border-indigo-500/60 shadow-md ring-1 ring-indigo-500/30"
                        : isBase
                        ? "bg-slate-900/90 border-amber-500/40"
                        : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                    }`}
                    onClick={() => {
                      if (!isTarget) {
                        setTargetVersionId(ver.id);
                      }
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-white text-sm">v{ver.sequence}</span>
                        {isTarget && (
                          <span className="px-1.5 py-0.2 text-[10px] font-semibold rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                            Target
                          </span>
                        )}
                        {isBase && (
                          <span className="px-1.5 py-0.2 text-[10px] font-semibold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            Baseline
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setRestoreModalVersion(ver);
                          }}
                          className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] font-medium transition flex items-center gap-1"
                          title="Restore this search configuration into a new active version"
                        >
                          <RotateCcw className="w-3 h-3 text-indigo-400" />
                          <span>Restore</span>
                        </button>
                      </div>
                    </div>

                    {ver.change_description && (
                      <p className="text-slate-300 text-[11px] mt-1.5 italic bg-slate-950/40 p-1.5 rounded border border-slate-800/80">
                        "{ver.change_description}"
                      </p>
                    )}

                    <div className="grid grid-cols-2 gap-2 mt-2.5 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                      <div>
                        <span className="text-slate-400">Retrieved: </span>
                        <strong className="text-white font-mono">{ver.total_records}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400">Screened: </span>
                        <strong className="text-emerald-400 font-mono">{ver.screened_records}</strong>
                        <span className="text-slate-400 font-mono"> / {ver.total_records}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">New: </span>
                        <strong className="text-emerald-400 font-mono">+{ver.new_records_count}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400">Repeated: </span>
                        <strong className="text-blue-400 font-mono">={ver.repeated_records_count}</strong>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-1 mt-2 text-[10px] text-slate-400">
                      <span>{new Date(ver.created_at).toLocaleString()}</span>
                      <div className="flex gap-1">
                        {ver.sources.map((s) => (
                          <span key={s} className="px-1 py-0.2 bg-slate-800 rounded text-slate-300">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Comparative Diff & Evolution Inspector */}
          <div className="lg:col-span-2 space-y-4">
            {/* Version Selectors Bar */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-400 font-medium">Compare:</span>
                  <select
                    value={baseVersionId}
                    onChange={(e) => setBaseVersionId(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 text-xs focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="">None (Empty baseline)</option>
                    {versions.map((v) => (
                      <option key={v.id} value={v.id} disabled={v.id === targetVersionId}>
                        v{v.sequence} ({v.total_records} records)
                      </option>
                    ))}
                  </select>
                </div>

                <ArrowRight className="w-4 h-4 text-slate-400" />

                <div className="flex items-center gap-1.5">
                  <span className="text-slate-400 font-medium">Target:</span>
                  <select
                    value={targetVersionId}
                    onChange={(e) => setTargetVersionId(e.target.value)}
                    className="bg-slate-950 border border-indigo-600 rounded-lg px-2.5 py-1 text-white text-xs focus:ring-1 focus:ring-indigo-500"
                  >
                    {versions.map((v) => (
                      <option key={v.id} value={v.id} disabled={v.id === baseVersionId}>
                        v{v.sequence} ({v.total_records} records)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {diffResult && (
                <div className="text-[11px] text-slate-400">
                  Comparing <strong className="text-amber-400">v{diffResult.summary.base_sequence}</strong> →{" "}
                  <strong className="text-indigo-400">v{diffResult.summary.target_sequence}</strong>
                </div>
              )}
            </div>

            {/* Diff Metric Cards */}
            {diffResult && (
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                <div className="bg-slate-900/80 border border-emerald-500/30 rounded-xl p-3 text-center">
                  <div className="text-emerald-400 text-lg font-bold font-mono">
                    +{diffResult.summary.newly_discovered_count}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-semibold mt-0.5">Newly Discovered</div>
                </div>

                <div className="bg-slate-900/80 border border-blue-500/30 rounded-xl p-3 text-center">
                  <div className="text-blue-400 text-lg font-bold font-mono">
                    ={diffResult.summary.repeated_count}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-semibold mt-0.5">Previously Known</div>
                </div>

                <div className="bg-slate-900/80 border border-amber-500/30 rounded-xl p-3 text-center">
                  <div className="text-amber-400 text-lg font-bold font-mono">
                    -{diffResult.summary.missing_from_newer_count}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-semibold mt-0.5" title="Absence without deletion">
                    No Longer Returned
                  </div>
                </div>

                <div className="bg-slate-900/80 border border-purple-500/30 rounded-xl p-3 text-center">
                  <div className="text-purple-400 text-lg font-bold font-mono">
                    ~{diffResult.summary.metadata_changed_count}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-semibold mt-0.5">Metadata Changed</div>
                </div>

                <div className="bg-slate-900/80 border border-indigo-500/30 rounded-xl p-3 text-center">
                  <div className="text-indigo-400 text-lg font-bold font-mono">
                    {diffResult.summary.screened_target_count}/{diffResult.summary.total_target_records}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-semibold mt-0.5">Screened In Target</div>
                </div>
              </div>
            )}

            {/* Filter Tabs */}
            {diffResult && (
              <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-800 pb-2">
                {[
                  { id: "all", label: "All Records", count: diffResult.records.length },
                  { id: "newly_discovered", label: "Newly Discovered", count: diffResult.summary.newly_discovered_count },
                  { id: "repeated", label: "Previously Known", count: diffResult.summary.repeated_count },
                  { id: "missing_from_newer", label: "No Longer Returned", count: diffResult.summary.missing_from_newer_count },
                  { id: "metadata_changed", label: "Metadata Changed", count: diffResult.summary.metadata_changed_count },
                  { id: "conflict", label: "Conflicts", count: diffResult.summary.conflicts_count },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveCategoryFilter(tab.id)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                      activeCategoryFilter === tab.id
                        ? "bg-indigo-600 text-white shadow-sm"
                        : "bg-slate-900/70 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                    }`}
                  >
                    <span>{tab.label}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                        activeCategoryFilter === tab.id ? "bg-indigo-700 text-white" : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {tab.count}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Records List */}
            {isLoadingDiff ? (
              <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                <RotateCcw className="w-4 h-4 animate-spin text-indigo-400" />
                <span>Computing search evolution diff...</span>
              </div>
            ) : filteredRecords.length === 0 ? (
              <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400 text-xs">
                No records match category filter "{activeCategoryFilter}".
              </div>
            ) : (
              <div className="space-y-3">
                {filteredRecords.map((rec) => {
                  const isExpanded = expandedRecordIds.has(rec.source_record_id);

                  return (
                    <div
                      key={rec.source_record_id}
                      className="bg-slate-900/90 border border-slate-800 hover:border-slate-700/80 rounded-xl p-4 transition shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1.5">
                            {getCategoryBadge(rec.category)}
                            {getScreeningBadge(rec)}
                            {rec.metadata_changed_since_screening && (
                              <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3 text-amber-400" />
                                <span>Metadata updated since screening</span>
                              </span>
                            )}
                            <span className="text-[11px] font-mono text-slate-400">
                              {rec.source}:{rec.external_id}
                            </span>
                          </div>

                          <h4 className="text-sm font-semibold text-white leading-snug">{rec.title}</h4>

                          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400 mt-1.5">
                            {(rec.authors && rec.authors.length > 0) && <span>{rec.authors.join(", ")}</span>}
                            {rec.year && <span>• {rec.year}</span>}
                            {rec.journal && <span>• {rec.journal}</span>}
                            {rec.doi && <span className="font-mono text-slate-400">• DOI: {rec.doi}</span>}
                          </div>

                          {rec.screening_reason && (
                            <p className="text-xs text-slate-400 mt-1.5 italic bg-slate-950/40 px-2 py-1 rounded border border-slate-800/80">
                              Decision note: {rec.screening_reason}
                            </p>
                          )}
                        </div>

                        {(rec.field_diffs && rec.field_diffs.length > 0) && (
                          <button
                            onClick={() => toggleRecordExpand(rec.source_record_id)}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 transition shrink-0"
                          >
                            <span>Field Diffs ({(rec.field_diffs || []).length})</span>
                            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>

                      {/* Expandable Field-Level Diff Inspector */}
                      {isExpanded && (rec.field_diffs && rec.field_diffs.length > 0) && (
                        <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                          <h5 className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                            Field-Level Metadata Diff (Base vs Target)
                          </h5>
                          <div className="space-y-2 text-xs">
                            {(rec.field_diffs || []).map((fd) => (
                              <div
                                key={fd.field_name}
                                className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-2"
                              >
                                <div>
                                  <div className="text-[10px] font-mono text-rose-400 uppercase font-semibold">
                                    Base Version ({fd.field_name})
                                  </div>
                                  <div className="text-slate-300 text-xs mt-0.5 line-through opacity-80 break-words">
                                    {fd.base_value || <em className="text-slate-600">none</em>}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">
                                    Target Version ({fd.field_name})
                                  </div>
                                  <div className="text-emerald-300 text-xs mt-0.5 break-words font-medium">
                                    {fd.target_value || <em className="text-slate-600">none</em>}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Restore Confirmation Modal */}
      {restoreModalVersion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/30">
                <RotateCcw className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  Restore Search Strategy v{restoreModalVersion.sequence}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Safe, non-destructive search configuration rollback
                </p>
              </div>
            </div>

            <div className="p-3.5 bg-indigo-950/30 border border-indigo-500/30 rounded-xl text-xs text-slate-300 space-y-1.5">
              <div className="flex items-center gap-1.5 text-indigo-300 font-semibold">
                <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Non-Destructive Invariant Guarantee</span>
              </div>
              <p>
                Restoring this version will create a <strong>new search query version</strong> with the exact Boolean AST,
                date filters, and provider targets from Version {restoreModalVersion.sequence}.
              </p>
              <p className="text-slate-400">
                • No existing search versions, executions, or papers will be deleted.
                <br />
                • All completed human screening decisions remain completely intact.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Restore Rationale / Audit Note (Optional)
              </label>
              <textarea
                value={restoreReason}
                onChange={(e) => setRestoreReason(e.target.value)}
                placeholder="e.g., Returning to broader sensitivity query after strict filter yielded too few hits..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setRestoreModalVersion(null)}
                disabled={isRestoring}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRestore}
                disabled={isRestoring}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 disabled:opacity-50"
              >
                {isRestoring && <RotateCcw className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm Restore</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
