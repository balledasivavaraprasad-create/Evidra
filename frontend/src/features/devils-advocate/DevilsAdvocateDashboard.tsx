import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  api,
  DevilsAdvocateDashboardResponse,
  DevilsAdvocateDashboardItem,
} from "../../api/client";
import { DevilsAdvocateCard } from "./DevilsAdvocateCard";

export const DevilsAdvocateDashboard: React.FC = () => {
  const { id: routeWorkspaceId } = useParams<{ id: string }>();
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string>(routeWorkspaceId || "");
  const [data, setData] = useState<DevilsAdvocateDashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [activeTab, setActiveTab] = useState<"all" | "high_vuln" | "pending" | "conceded" | "upheld" | "dismissed">("all");
  const [selectedGroup, setSelectedGroup] = useState<DevilsAdvocateDashboardItem | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) {
      loadDefaultWorkspace();
    } else {
      fetchDashboard();
    }
  }, [activeWorkspaceId, activeTab]);

  const loadDefaultWorkspace = () => {
    setActiveWorkspaceId("ws-synth-001");
  };

  const fetchDashboard = async () => {
    if (!activeWorkspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.devilsAdvocate.getDashboard(activeWorkspaceId, {
        disposition: activeTab === "pending" || activeTab === "conceded" || activeTab === "upheld" || activeTab === "dismissed"
          ? activeTab
          : undefined,
        high_vulnerability_only: activeTab === "high_vuln",
      });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load Devil's Advocate dashboard.");
    } finally {
      setLoading(false);
    }
  };

  const getRecColor = (rec: string) => {
    switch (rec) {
      case "reconsider_exclusion":
        return "bg-rose-500/20 text-rose-300 border-rose-500/30";
      case "needs_human_review":
        return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      default:
        return "bg-slate-700 text-slate-300 border-slate-600";
    }
  };

  const getDispColor = (disp: string) => {
    switch (disp) {
      case "conceded":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "upheld":
        return "bg-slate-700 text-slate-300 border-slate-600";
      case "dismissed":
        return "bg-slate-800 text-slate-400 border-slate-700";
      default:
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-3xl">⚖️</span>
            <div>
              <h1 className="text-2xl font-bold text-slate-100">
                Devil's Advocate Reviewer
              </h1>
              <p className="text-sm text-slate-400">
                Adversarial audit workflow to challenge exclusions and reduce false negatives in systematic reviews.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to={activeWorkspaceId ? `/reviews/${activeWorkspaceId}` : "/reviews"}
            className="px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
          >
            ← Back to Workbench
          </Link>
          <button
            onClick={fetchDashboard}
            className="px-3.5 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-lg shadow transition-colors"
          >
            Refresh Dashboard
          </button>
        </div>
      </div>

      {/* Metrics Ribbon */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Total Challenged
            </div>
            <div className="text-2xl font-bold text-slate-100 mt-1">
              {data.total_challenged}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Exclusion records</div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">
              Pending Deliberation
            </div>
            <div className="text-2xl font-bold text-amber-300 mt-1">
              {data.pending_challenges}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Awaiting reviewer</div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <div className="text-xs font-medium text-rose-400 uppercase tracking-wider">
              High Vulnerability
            </div>
            <div className="text-2xl font-bold text-rose-300 mt-1">
              {data.high_vulnerability_count}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Score ≥ 60%</div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <div className="text-xs font-medium text-emerald-400 uppercase tracking-wider">
              Concession Rate
            </div>
            <div className="text-2xl font-bold text-emerald-300 mt-1">
              {data.concession_rate}%
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">{data.conceded_count} accepted</div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <div className="text-xs font-medium text-cyan-400 uppercase tracking-wider">
              False Exclusions Saved
            </div>
            <div className="text-2xl font-bold text-cyan-300 mt-1">
              {data.false_exclusions_prevented}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Reversed to Include/Maybe</div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab("all")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "all"
              ? "bg-amber-600 text-white font-semibold"
              : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
        >
          All Challenges ({data?.total_challenged || 0})
        </button>
        <button
          onClick={() => setActiveTab("high_vuln")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "high_vuln"
              ? "bg-rose-600 text-white font-semibold"
              : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
        >
          ⚠️ High Vulnerability ({data?.high_vulnerability_count || 0})
        </button>
        <button
          onClick={() => setActiveTab("pending")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "pending"
              ? "bg-amber-600 text-white font-semibold"
              : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
        >
          Pending Review ({data?.pending_challenges || 0})
        </button>
        <button
          onClick={() => setActiveTab("conceded")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "conceded"
              ? "bg-emerald-600 text-white font-semibold"
              : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
        >
          Conceded ({data?.conceded_count || 0})
        </button>
        <button
          onClick={() => setActiveTab("upheld")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "upheld"
              ? "bg-slate-700 text-white font-semibold"
              : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
        >
          Upheld ({data?.upheld_count || 0})
        </button>
      </div>

      {/* Main Ledger Table */}
      {loading ? (
        <div className="text-center py-12 text-slate-400">
          <div className="inline-block animate-spin w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full mr-3" />
          Loading challenged exclusion records...
        </div>
      ) : error ? (
        <div className="text-center py-12 text-rose-400 bg-slate-900 border border-slate-800 rounded-xl">
          {error}
        </div>
      ) : !data || !data.challenges || data.challenges.length === 0 ? (
        <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
          <div className="text-3xl mb-2">⚖️</div>
          <p className="text-base font-semibold text-slate-200">No challenged exclusions match this filter.</p>
          <p className="text-xs text-slate-500 mt-1">
            Exclusions marked in the review workbench are automatically audited here.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Study Title & Metadata</th>
                  <th className="py-3 px-4">Exclusion Rationale</th>
                  <th className="py-3 px-4">Recommendation</th>
                  <th className="py-3 px-4 text-center">Vulnerability</th>
                  <th className="py-3 px-4 text-center">Counter-Quotes</th>
                  <th className="py-3 px-4 text-center">Disposition</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {(data.challenges || []).map((row) => (
                  <tr key={row.challenge_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 max-w-xs sm:max-w-md">
                      <div className="font-semibold text-slate-200 line-clamp-1">{row.title}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        {row.authors && row.authors.length > 0 ? row.authors.slice(0, 2).join(", ") : "Unknown"}{" "}
                        {row.year ? `(${row.year})` : ""} {row.pmid ? `• PMID: ${row.pmid}` : ""}
                      </div>
                    </td>
                    <td className="py-3 px-4 max-w-xs">
                      <div className="text-slate-300 italic font-mono bg-slate-950/60 px-2 py-1 rounded border border-slate-800 line-clamp-2">
                        "{row.original_exclusion_reason || "Unspecified"}"
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full border text-[11px] font-semibold whitespace-nowrap ${getRecColor(row.recommendation)}`}>
                        {row.recommendation === "reconsider_exclusion"
                          ? "Reconsider"
                          : row.recommendation === "needs_human_review"
                          ? "Needs Review"
                          : "Uphold"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center font-bold">
                      <span
                        className={
                          row.vulnerability_score >= 0.6
                            ? "text-rose-400"
                            : row.vulnerability_score >= 0.35
                            ? "text-amber-400"
                            : "text-emerald-400"
                        }
                      >
                        {Math.round(row.vulnerability_score * 100)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center text-slate-300 font-medium">
                      {row.counter_argument_count}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded-full border text-[11px] font-medium capitalize ${getDispColor(row.disposition)}`}>
                        {row.disposition}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedGroup(row)}
                        className="px-3 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 rounded font-medium text-xs transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Inspect Challenge Modal */}
      {selectedGroup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-3xl w-full p-6 space-y-4 shadow-2xl my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-100 line-clamp-1">
                  {selectedGroup.title}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  PMID: {selectedGroup.pmid || "N/A"} • Year: {selectedGroup.year || "N/A"}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedGroup(null);
                  fetchDashboard();
                }}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold px-2 py-1"
              >
                ✕ Close
              </button>
            </div>

            <DevilsAdvocateCard
              workspaceId={activeWorkspaceId}
              groupId={selectedGroup.group_id}
              effectiveDecision={selectedGroup.proposed_decision}
              exclusionReason={selectedGroup.original_exclusion_reason}
              onDecisionUpdated={() => {
                fetchDashboard();
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
