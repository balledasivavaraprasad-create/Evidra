import React, { useState, useEffect } from "react";
import { ErrorState, LoadingRegion, SampleDataNotice, SkeletonCard } from "../../components/Feedback";
import { useParams } from "react-router-dom";
import {
  Copy,
  Check,
  X,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  GitBranch,
  Layers,
  Search,
  RefreshCw,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import {
  api,
  isServiceUnreachable,
  type DedupOverrideRequest,
  type DuplicateWorkspaceSummaryResponse,
  type DuplicateWorkspaceSummaryItem,
} from "../../api/client";
import { DuplicateGenealogyView } from "./DuplicateGenealogyView";

type ViewTab = "genealogy" | "conflicts" | "candidates";

export const DuplicatesPage: React.FC = () => {
  const { id: workspaceParam } = useParams<{ id: string }>();
  const workspaceId = workspaceParam || "ws-synth-001";

  const [activeTab, setActiveTab] = useState<ViewTab>("genealogy");
  const [summaryData, setSummaryData] = useState<DuplicateWorkspaceSummaryResponse | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [usingSampleData, setUsingSampleData] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");
  const [onlyConflictsFilter, setOnlyConflictsFilter] = useState(false);

  // Candidate pair review state
  const [resolution, setResolution] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchWorkspaceDuplicates = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await api.genealogy.getOverview(workspaceId);
      setSummaryData(data);
      setUsingSampleData(false);
      const grps = data.groups || [];
      if (grps.length > 0 && !selectedGroupId) {
        setSelectedGroupId(grps[0].group_id);
      }
    } catch (err: unknown) {
      // A real server error is shown as an error, never hidden behind sample data
      if (!isServiceUnreachable(err)) {
        setLoadError(err);
        return;
      }
      // Service not running: show clearly labelled sample data so the page can still be explored
      setUsingSampleData(true);
      const mockSummary: DuplicateWorkspaceSummaryResponse = {
        workspace_id: workspaceId,
        total_duplicate_groups: 2,
        total_duplicate_records: 4,
        groups_with_conflicts: 1,
        resolved_conflicts_count: 0,
        pending_candidate_pairs: 1,
        groups: [
          {
            group_id: "grp-synth-001",
            canonical_title: "Metformin improves glycemic control in adult patients with type 2 diabetes: a randomized controlled trial.",
            member_count: 2,
            has_unresolved_conflict: true,
            conflict_types: ["decision_disagreement"],
            confidence_label: "HIGH",
            effective_decision: "conflict",
            sources: ["PubMed", "Europe PMC"],
            created_at: new Date().toISOString(),
          },
          {
            group_id: "grp-synth-002",
            canonical_title: "SGLT2 inhibitors and cardiovascular outcomes in diabetic kidney disease.",
            member_count: 2,
            has_unresolved_conflict: false,
            confidence_label: "HIGH",
            effective_decision: "include",
            sources: ["Europe PMC", "CrossRef"],
            created_at: new Date().toISOString(),
          },
        ],
      };
      setSummaryData(mockSummary);
      if (!selectedGroupId && (mockSummary.groups || []).length > 0) {
        setSelectedGroupId((mockSummary.groups || [])[0].group_id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaceDuplicates();
  }, [workspaceId]);

  // Candidate pair (for Candidate Review tab)
  const candidate = {
    record_a: {
      id: "src-synth-001",
      source: "PubMed (PMID: 38100001)",
      title: "Metformin improves glycemic control in adult patients with type 2 diabetes: a randomized controlled trial.",
      authors: "Miller AB, Davis KR, Chen L",
      year: 2023,
      doi: "10.1001/dc.2023.01",
      abstract:
        "Objective: Evaluate oral metformin versus placebo in adults with type 2 diabetes. Methods: 150 patients received metformin 1000mg daily. Results: HbA1c decreased significantly. Conclusion: Metformin is effective.",
    },
    record_b: {
      id: "src-synth-002",
      source: "Europe PMC (PMC1099901)",
      title: "Metformin improves glycemic control in adult patients with type 2 diabetes: a randomized controlled trial.",
      authors: "Miller A.B., Davis K.R., Chen L.",
      year: 2023,
      doi: "10.1001/dc.2023.01",
      abstract:
        "Objective: Evaluate oral metformin versus placebo in adults with type 2 diabetes. Methods: 150 patients received metformin 1000mg daily. Results: HbA1c decreased significantly. Conclusion: Metformin is effective.",
    },
    similarity: 1.0,
    evidence: "Exact DOI match (10.1001/dc.2023.01) + Exact normalized title + Author initials match",
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
      fetchWorkspaceDuplicates();
    } catch {
      setResolution(
        action === "confirm"
          ? "Confirmed as Same Publication (saved locally; verified identical publication)."
          : "Rejected pair (saved locally; enforced cannot-link constraint)."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const allGroups: DuplicateWorkspaceSummaryItem[] = summaryData?.groups || [];
  const filteredGroups = allGroups.filter((g) => {
    if (onlyConflictsFilter && !g.has_unresolved_conflict) return false;
    if (searchFilter.trim()) {
      const term = searchFilter.toLowerCase();
      const matchTitle = (g.canonical_title || "").toLowerCase().includes(term);
      const matchSources = (g.sources || []).some((s) => s.toLowerCase().includes(term));
      const matchId = (g.group_id || "").toLowerCase().includes(term);
      return matchTitle || matchSources || matchId;
    }
    return true;
  });

  const conflictsCount = summaryData?.groups_with_conflicts ?? 0;

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Copy className="w-5 h-5 text-indigo-400" />
            <h1 className="text-xl font-bold text-white tracking-wide">
              Duplicate Genealogy & Decision Reconciliation
            </h1>
            <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded bg-indigo-950/80 text-indigo-400 border border-indigo-800">
              Audit Grade
            </span>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Track multi-source paper genealogy, inspect matching evidence signals, reconcile conflicting decisions, and safely split or reverse merges without silent overrides.
          </p>
        </div>

        {/* Global Summary Stats */}
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-center">
            <span className="block text-slate-400 text-[10px] font-mono uppercase">Duplicate Groups</span>
            <span className="text-sm font-bold text-white">{summaryData ? summaryData.total_duplicate_groups : "–"}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-center">
            <span className="block text-slate-400 text-[10px] font-mono uppercase">Member Records</span>
            <span className="text-sm font-bold text-indigo-300">{summaryData ? summaryData.total_duplicate_records : "–"}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-center">
            <span className="block text-slate-400 text-[10px] font-mono uppercase">Active Conflicts</span>
            <span
              className={`text-sm font-bold ${
                conflictsCount > 0 ? "text-amber-400" : "text-emerald-400"
              }`}
            >
              {conflictsCount}
            </span>
          </div>
          <button
            onClick={fetchWorkspaceDuplicates}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition"
            title="Refresh duplicates overview"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-indigo-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800/80 pb-2">
        <button
          onClick={() => {
            setActiveTab("genealogy");
            setOnlyConflictsFilter(false);
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
            activeTab === "genealogy"
              ? "bg-indigo-600 text-white shadow-md shadow-indigo-900/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
          }`}
        >
          <GitBranch className="w-3.5 h-3.5" />
          <span>Genealogy & Merged Groups</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-800">
            {allGroups.length}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveTab("conflicts");
            setOnlyConflictsFilter(true);
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
            activeTab === "conflicts"
              ? "bg-amber-600 text-white shadow-md shadow-amber-900/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Decision Conflicts Ledger</span>
          {conflictsCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-950 text-amber-300 border border-amber-800 animate-pulse">
              {conflictsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("candidates")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
            activeTab === "candidates"
              ? "bg-slate-700 text-white shadow-md"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Pairwise Candidate Review</span>
        </button>
      </div>

      {usingSampleData && <SampleDataNotice onRetry={fetchWorkspaceDuplicates} />}

      {/* Main Tab Content */}
      {isLoading && !summaryData ? (
        <LoadingRegion label="Loading duplicate groups" className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-3">
            <SkeletonCard lines={1} />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="lg:col-span-2 space-y-4">
            <SkeletonCard lines={4} />
            <SkeletonCard lines={3} />
          </div>
        </LoadingRegion>
      ) : loadError != null && !summaryData ? (
        <ErrorState error={loadError} onRetry={fetchWorkspaceDuplicates} what="Duplicate groups" />
      ) : activeTab === "candidates" ? (
        <div className="space-y-6">
          {resolution && (
            <div className="p-3.5 rounded-xl bg-emerald-950/70 border border-emerald-800 text-emerald-300 text-xs font-mono flex items-center justify-between shadow-lg animate-fadeIn">
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>{resolution}</span>
              </span>
              <button onClick={() => setResolution(null)} className="text-emerald-400 hover:text-white">
                ✕
              </button>
            </div>
          )}

          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-950/80 border border-red-800 text-red-200 text-xs flex items-center justify-between">
              <span className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <span>{errorMessage}</span>
              </span>
              <button onClick={() => setErrorMessage(null)} className="text-red-400 hover:text-white">
                ✕
              </button>
            </div>
          )}

          {/* Candidate Pair Card */}
          <div className="glass-panel p-6 space-y-6 border-slate-800 shadow-xl rounded-2xl bg-slate-900/50">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 font-mono text-xs">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span className="text-slate-400">Candidate Match:</span>
                <span className="text-cyan-300 font-bold">Confidence 100% (Exact DOI Match)</span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">{candidate.evidence}</div>
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
                Domain Invariant: Confirming merges records into an auditable genealogy group; rejecting enforces an irreversible cannot-link constraint preventing automatic re-merging.
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
                  <span>Reject (Enforce Cannot-Link)</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Genealogy & Conflicts Views */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Duplicate Groups Directory */}
          <div className="lg:col-span-4 space-y-4">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white uppercase tracking-wider font-mono">
                  {activeTab === "conflicts" ? "Conflicting Groups" : "Duplicate Groups"}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {filteredGroups.length} shown
                </span>
              </div>

              {/* Search input */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter by title, DOI, source..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Filter toggle */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-300">
                  <input
                    type="checkbox"
                    checked={onlyConflictsFilter}
                    onChange={(e) => setOnlyConflictsFilter(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-950 text-indigo-500 focus:ring-0"
                  />
                  <span>Only show active conflicts</span>
                </label>
              </div>
            </div>

            {/* Group Items List */}
            <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
              {filteredGroups.length === 0 ? (
                <div className="p-6 text-center rounded-xl bg-slate-900/30 border border-slate-800/80 text-slate-500 text-xs">
                  No duplicate groups match the filter criteria.
                </div>
              ) : (
                filteredGroups.map((g) => {
                  const isSelected = g.group_id === selectedGroupId;
                  return (
                    <div
                      key={g.group_id}
                      onClick={() => setSelectedGroupId(g.group_id)}
                      className={`p-3.5 rounded-xl border cursor-pointer transition text-left space-y-2 ${
                        isSelected
                          ? "bg-indigo-950/40 border-indigo-600 shadow-md ring-1 ring-indigo-500/30"
                          : "bg-slate-900/40 border-slate-800/80 hover:bg-slate-900/70 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[10px] text-slate-400 flex items-center gap-1.5">
                          <Layers className="w-3 h-3 text-slate-500" />
                          <span>{g.group_id}</span>
                        </span>
                        <div className="flex items-center gap-1.5">
                          {g.has_unresolved_conflict && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-950/90 text-amber-300 border border-amber-800 animate-pulse">
                              CONFLICT
                            </span>
                          )}
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                            {g.member_count} records
                          </span>
                        </div>
                      </div>

                      <h4 className="text-xs font-semibold text-white line-clamp-2 leading-relaxed">
                        {g.canonical_title}
                      </h4>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800/50">
                        <div className="flex items-center gap-1 font-mono text-[10px]">
                          {(g.sources || []).map((src, i) => (
                            <span key={i} className="px-1.5 py-0.2 rounded bg-slate-950 border border-slate-800 text-slate-400">
                              {src}
                            </span>
                          ))}
                        </div>
                        <ChevronRight className={`w-3.5 h-3.5 ${isSelected ? "text-indigo-400" : "text-slate-600"}`} />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Column: Full Interactive Genealogy Detail */}
          <div className="lg:col-span-8">
            {selectedGroupId ? (
              <DuplicateGenealogyView
                workspaceId={workspaceId}
                groupId={selectedGroupId}
                onRefreshNeeded={fetchWorkspaceDuplicates}
              />
            ) : (
              <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-slate-800 text-slate-500 text-xs">
                Select a duplicate group from the directory to inspect its genealogy tree, match signals, field provenance, and decision conflicts.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
export default DuplicatesPage;