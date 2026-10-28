import React, { useEffect, useState, useTransition } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Sparkles,
  RotateCcw,
  Search,
  Filter,
  CheckCircle2,
  HelpCircle,
  AlertCircle,
  Clock,
  ShieldAlert,
  ArrowRight,
  Layers,
  FileText,
  AlertTriangle,
  UserCheck,
  ChevronRight,
  X,
} from "lucide-react";
import {
  api,
  type ReviewRadarResponse,
  type RadarEvidenceStatus,
  type ArticleRadarResponse,
} from "../../api/client";
import { ArticleRadarWidget } from "./ArticleRadarWidget";

export const ReviewRadarDashboard: React.FC = () => {
  const { id: workspaceIdParam } = useParams<{ id: string }>();
  const activeWorkspaceId = workspaceIdParam || "ws-synth-001";

  const [data, setData] = useState<ReviewRadarResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [query, setQuery] = useState("");
  const [dimensionFilter, setDimensionFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [needsReviewOnly, setNeedsReviewOnly] = useState<boolean>(false);

  // Active Article Radar Modal
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [activeArticleRadar, setActiveArticleRadar] = useState<ArticleRadarResponse | null>(null);
  const [isLoadingArticleRadar, setIsLoadingArticleRadar] = useState(false);

  const [, startTransition] = useTransition();

  const loadDashboard = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.radar.getOverview(activeWorkspaceId, {
        dimension_filter: dimensionFilter || undefined,
        status_filter: statusFilter || undefined,
        needs_review_only: needsReviewOnly,
        query: query.trim() || undefined,
        limit: 100,
        offset: 0,
      });
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load Missing-Evidence Radar dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, [activeWorkspaceId, dimensionFilter, statusFilter, needsReviewOnly]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadDashboard();
  };

  const openArticleRadar = async (groupId: string) => {
    setActiveGroupId(groupId);
    setIsLoadingArticleRadar(true);
    try {
      const res = await api.radar.getArticleRadar(activeWorkspaceId, groupId);
      setActiveArticleRadar(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load article radar");
    } finally {
      setIsLoadingArticleRadar(false);
    }
  };

  const getStatusCell = (status: RadarEvidenceStatus, value: string | null | undefined) => {
    switch (status) {
      case "supported":
        return (
          <div className="flex flex-col gap-0.5">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
              <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
              <span>Supported</span>
            </span>
            <span className="text-[11px] text-slate-300 truncate max-w-[150px]" title={value || ""}>
              {value || "—"}
            </span>
          </div>
        );
      case "uncertain":
        return (
          <div className="flex flex-col gap-0.5">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400">
              <HelpCircle className="w-3 h-3 text-amber-400 shrink-0" />
              <span>Uncertain</span>
            </span>
            <span className="text-[11px] text-slate-400 truncate max-w-[150px]" title={value || ""}>
              {value || "Ambiguous"}
            </span>
          </div>
        );
      case "not_found":
        return (
          <div className="flex flex-col gap-0.5">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400">
              <AlertCircle className="w-3 h-3 text-slate-500 shrink-0" />
              <span>Not found in text</span>
            </span>
            <span className="text-[10px] text-slate-500 italic">Examined abstract</span>
          </div>
        );
      case "conflicting":
        return (
          <div className="flex flex-col gap-0.5">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400">
              <ShieldAlert className="w-3 h-3 text-rose-400 shrink-0" />
              <span>Conflicting</span>
            </span>
            <span className="text-[11px] text-rose-300 truncate max-w-[150px]">Requires Review</span>
          </div>
        );
      case "stale":
        return (
          <div className="flex flex-col gap-0.5">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-400">
              <Clock className="w-3 h-3 text-purple-400 shrink-0" />
              <span>Stale</span>
            </span>
            <span className="text-[10px] text-purple-300">Revalidate</span>
          </div>
        );
      case "not_assessed":
      default:
        return (
          <div className="flex flex-col gap-0.5">
            <span className="text-[11px] text-slate-500 font-medium">Not Assessed</span>
            <span className="text-[10px] text-slate-600">No source text</span>
          </div>
        );
    }
  };

  const getScreeningBadge = (decision: string) => {
    switch (decision) {
      case "include":
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            Included
          </span>
        );
      case "exclude":
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
            Excluded
          </span>
        );
      case "maybe":
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
            Maybe
          </span>
        );
      case "conflict":
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
            Conflict
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[10px] font-medium rounded bg-slate-800 text-slate-400 border border-slate-700">
            Unscreened
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Top Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              <h1 className="text-lg font-bold text-white">Missing-Evidence Radar</h1>
              <span className="px-2 py-0.5 text-[10px] font-mono font-semibold uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded">
                PICO Evidence Coverage
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Track which PICO elements are supported by examined source text, which remain uncertain,
              and which could not be located. Missing evidence informs research prioritization and never
              silently excludes a study.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadDashboard}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Refresh Coverage</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-950/40 border border-rose-500/40 text-rose-300 rounded-lg text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Summary Metrics Ribbon */}
      {data && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span>Overall Evidence Support:</span>
              <strong className="text-cyan-400 font-mono text-sm">
                {data.total_fields_supported_percent}%
              </strong>
              <span>({data.total_articles} total articles evaluated)</span>
            </div>
            <div className="flex items-center gap-3">
              <span>
                Articles with source text:{" "}
                <strong className="text-white font-mono">{data.articles_with_source_text}</strong>
              </span>
              <span>
                Without text:{" "}
                <strong className="text-amber-400 font-mono">{data.articles_without_source_text}</strong>
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { key: "population", label: "Population", color: "cyan" },
              { key: "intervention", label: "Intervention", color: "indigo" },
              { key: "comparator", label: "Comparator", color: "amber" },
              { key: "outcome", label: "Outcome", color: "emerald" },
            ].map(({ key, label }) => {
              const summary = data.dimension_summaries[key];
              if (!summary) return null;

              return (
                <div
                  key={key}
                  className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      {label}
                    </span>
                    <span className="text-sm font-mono font-bold text-cyan-400">
                      {summary.supported_percent}%
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/80 text-slate-400">
                    <div>
                      Supported: <strong className="text-emerald-400 font-mono">{summary.supported_count}</strong>
                    </div>
                    <div>
                      Uncertain: <strong className="text-amber-400 font-mono">{summary.uncertain_count}</strong>
                    </div>
                    <div>
                      Not found: <strong className="text-slate-300 font-mono">{summary.not_found_count}</strong>
                    </div>
                    <div>
                      Conflicting: <strong className="text-rose-400 font-mono">{summary.conflicting_count}</strong>
                    </div>
                    <div>
                      Stale: <strong className="text-purple-400 font-mono">{summary.stale_count}</strong>
                    </div>
                    <div>
                      Confirmed: <strong className="text-cyan-400 font-mono">{summary.human_confirmed_count}</strong>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filter and Prioritization Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-md">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search articles by title, PMID, or DOI..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium"
            >
              Search
            </button>
          </form>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={dimensionFilter}
              onChange={(e) => setDimensionFilter(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs"
            >
              <option value="">All Dimensions</option>
              <option value="population">Population</option>
              <option value="intervention">Intervention</option>
              <option value="comparator">Comparator</option>
              <option value="outcome">Outcome</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs"
            >
              <option value="">All Statuses</option>
              <option value="supported">Supported</option>
              <option value="uncertain">Uncertain / Needs Review</option>
              <option value="not_found">Not Found in Examined Text</option>
              <option value="conflicting">Conflicting Evidence</option>
              <option value="stale">Stale (Text Changed)</option>
              <option value="not_assessed">Not Assessed</option>
            </select>

            <button
              type="button"
              onClick={() => setNeedsReviewOnly(!needsReviewOnly)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                needsReviewOnly
                  ? "bg-amber-600 text-white shadow-sm"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Prioritize Needs Review</span>
            </button>
          </div>
        </div>
      </div>

      {/* Evidence Coverage Matrix Table */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
          <RotateCcw className="w-4 h-4 animate-spin text-cyan-400" />
          <span>Aggregating review-wide PICO evidence radar...</span>
        </div>
      ) : !data || data.rows.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-xl text-slate-400 text-xs">
          No articles match the current radar filter criteria.
        </div>
      ) : (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4 min-w-[280px]">Article & Identifiers</th>
                  <th className="py-3 px-3">Decision</th>
                  <th className="py-3 px-3 min-w-[140px]">Population</th>
                  <th className="py-3 px-3 min-w-[140px]">Intervention</th>
                  <th className="py-3 px-3 min-w-[140px]">Comparator</th>
                  <th className="py-3 px-3 min-w-[140px]">Outcome</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {data.rows.map((row) => (
                  <tr
                    key={row.group_id}
                    className="hover:bg-slate-950/50 transition cursor-pointer"
                    onClick={() => openArticleRadar(row.group_id)}
                  >
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white leading-snug">{row.title}</div>
                      <div className="flex flex-wrap items-center gap-x-2 text-[11px] text-slate-400 mt-0.5">
                        {(row.authors && row.authors.length > 0) && <span>{row.authors.join(", ")}</span>}
                        {row.year && <span>• {row.year}</span>}
                        {row.journal && <span>• {row.journal}</span>}
                        {row.pmid && <span className="font-mono text-cyan-400">• PMID: {row.pmid}</span>}
                      </div>
                      {!row.has_source_text && (
                        <span className="text-[10px] text-amber-400 italic">No abstract text examined</span>
                      )}
                    </td>

                    <td className="py-3 px-3">{getScreeningBadge(row.effective_decision)}</td>

                    <td className="py-3 px-3">{getStatusCell(row.population_status, row.population_value)}</td>
                    <td className="py-3 px-3">{getStatusCell(row.intervention_status, row.intervention_value)}</td>
                    <td className="py-3 px-3">{getStatusCell(row.comparator_status, row.comparator_value)}</td>
                    <td className="py-3 px-3">{getStatusCell(row.outcome_status, row.outcome_value)}</td>

                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openArticleRadar(row.group_id);
                        }}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white rounded text-[11px] font-medium transition"
                      >
                        Inspect Radar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Article Radar Modal */}
      {activeGroupId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-4 max-h-[92vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white">Article Missing-Evidence Radar</h3>
              </div>
              <button
                onClick={() => {
                  setActiveGroupId(null);
                  setActiveArticleRadar(null);
                  loadDashboard();
                }}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {isLoadingArticleRadar ? (
              <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                <RotateCcw className="w-4 h-4 animate-spin text-cyan-400" />
                <span>Loading article PICO radar...</span>
              </div>
            ) : activeArticleRadar ? (
              <ArticleRadarWidget
                radar={activeArticleRadar}
                workspaceId={activeWorkspaceId}
                groupId={activeGroupId}
                onRadarUpdated={(updated) => setActiveArticleRadar(updated)}
              />
            ) : (
              <div className="p-8 text-center text-slate-400 text-xs">
                Failed to load article radar details.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
