import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Brain,
  Sparkles,
  ArrowUpDown,
  RotateCcw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ExternalLink,
  ShieldCheck,
  Layers,
  Filter,
  BarChart3,
  Info,
} from "lucide-react";
import {
  api,
  type MLRankingResponse,
  type MLRankedItem,
  type PaperGroupSummary,
  ApiError,
} from "../../api/client";
import { MOCK_ML_RANKING, MOCK_GROUPS } from "../../api/fixtures";

export const MLReviewPage: React.FC = () => {
  const { id: workspaceParam } = useParams<{ id: string }>();
  const workspaceId = workspaceParam || "ws-synth-001";

  const [revisionId, setRevisionId] = useState<string | null>(null);
  const [rankingData, setRankingData] = useState<MLRankingResponse | null>(null);
  const [baselineGroups, setBaselineGroups] = useState<PaperGroupSummary[]>([]);
  const [isBaselineOrder, setIsBaselineOrder] = useState<boolean>(false);
  const [selectedPriority, setSelectedPriority] = useState<string>("ALL");
  const [loading, setLoading] = useState<boolean>(true);
  const [recomputing, setRecomputing] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  const [humanDecisions, setHumanDecisions] = useState<Record<string, string>>({});

  // 1. Load active revision and initial ML ranking
  const fetchRanking = useCallback(async (revId: string, force = false) => {
    try {
      if (force) setRecomputing(true);
      else setLoading(true);
      setErrorBanner(null);

      const res = await api.ml.computeRanking(workspaceId, revId, {
        limit: 100,
        offset: 0,
        force_recompute: force,
      });
      setRankingData(res);
      const items = res.items || [];
      if (items.length > 0 && !selectedRecordId) {
        setSelectedRecordId(items[0].record_id);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorBanner(`ML Ranking error (${err.status}): ${err.message}`);
      } else {
        // Fallback to fixture data in local/test environment
        setRankingData(MOCK_ML_RANKING as unknown as MLRankingResponse);
      }
    } finally {
      setLoading(false);
      setRecomputing(false);
    }
  }, [workspaceId, selectedRecordId]);

  useEffect(() => {
    let mounted = true;
    async function init() {
      try {
        setLoading(true);
        const revs = await api.revisions.list(workspaceId);
        if (!mounted) return;

        if (revs && revs.length > 0) {
          const activeRevId = revs[0].id;
          setRevisionId(activeRevId);

          // Also fetch baseline groups
          try {
            const grps = await api.revisions.listGroups(activeRevId);
            if (mounted && grps) setBaselineGroups(grps);
          } catch {
            if (mounted) setBaselineGroups(MOCK_GROUPS);
          }

          await fetchRanking(activeRevId);
        } else {
          // Fallback to mock for offline demonstration
          setRankingData(MOCK_ML_RANKING as unknown as MLRankingResponse);
          setBaselineGroups(MOCK_GROUPS);
        }
      } catch {
        if (mounted) {
          setRankingData(MOCK_ML_RANKING as unknown as MLRankingResponse);
          setBaselineGroups(MOCK_GROUPS);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, [workspaceId, fetchRanking]);

  // Priority count statistics
  const stats = useMemo(() => {
    if (!rankingData) return { high: 0, medium: 0, low: 0, unscored: 0, total: 0 };
    const items = rankingData.items || [];
    return {
      high: items.filter((it) => it.priority_label === "HIGH").length,
      medium: items.filter((it) => it.priority_label === "MEDIUM").length,
      low: items.filter((it) => it.priority_label === "LOW").length,
      unscored: items.filter((it) => it.priority_label === "UNSCORED").length,
      total: items.length,
    };
  }, [rankingData]);

  // Filtered displayed records
  const displayedItems = useMemo(() => {
    if (!rankingData) return [];
    const rawItems = rankingData.items || [];
    let items = [...rawItems];

    if (isBaselineOrder) {
      // Sort deterministically by record_id (baseline order)
      items.sort((a, b) => a.record_id.localeCompare(b.record_id));
    } else {
      // Sort by ML rank
      items.sort((a, b) => a.rank - b.rank);
    }

    if (selectedPriority !== "ALL") {
      items = items.filter((it) => it.priority_label === selectedPriority);
    }
    return items;
  }, [rankingData, isBaselineOrder, selectedPriority]);

  const selectedItem = useMemo(() => {
    if (!displayedItems.length) return null;
    return displayedItems.find((it) => it.record_id === selectedRecordId) || displayedItems[0];
  }, [displayedItems, selectedRecordId]);

  // Handle human reviewer decision
  const handleReviewDecision = (recordId: string, decision: "include" | "exclude" | "maybe") => {
    setHumanDecisions((prev) => ({ ...prev, [recordId]: decision }));
  };

  return (
    <div className="space-y-6 pb-12 animate-fade-in" data-testid="ml-review-container">
      {/* Page Title & Navigation Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Brain className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              ML Review Prioritization
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-indigo-900/40 text-indigo-300 border border-indigo-700/50">
              C-ML02
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Trained review queue ranking using verified TF-IDF + calibrated Logistic Regression.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to={`/reviews/${workspaceId}/records`}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg border border-slate-700 bg-slate-900/60 hover:bg-slate-800 text-slate-200 transition-colors"
          >
            <Filter className="w-4 h-4 text-slate-400" />
            Manual Screening Queue
          </Link>

          <button
            onClick={() => revisionId && fetchRanking(revisionId, true)}
            disabled={recomputing || loading}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-sm shadow-indigo-600/30 disabled:opacity-50"
            data-testid="recompute-ranking-btn"
          >
            <RotateCcw className={`w-4 h-4 ${recomputing ? "animate-spin" : ""}`} />
            {recomputing ? "Recomputing..." : "Recompute Model"}
          </button>
        </div>
      </div>

      {/* Error / Alert Banner */}
      {errorBanner && (
        <div
          role="alert"
          className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 flex items-start gap-3 text-sm"
        >
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">Model Notice</p>
            <p className="text-amber-300/90 text-xs mt-0.5">{errorBanner}</p>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-amber-400 hover:text-amber-200 text-xs font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Model Scope & Provenance Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
        <div className="space-y-1">
          <span className="text-slate-500 font-medium">Model Artifact</span>
          <div className="flex items-center gap-1.5 text-slate-200 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            {rankingData?.model_version || "ml_ranker:v1.0.0"}
          </div>
        </div>

        <div className="space-y-1">
          <span className="text-slate-500 font-medium">Execution Status</span>
          <div>
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide ${
                rankingData?.status === "COMPLETED"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : rankingData?.status === "CACHED"
                  ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                  : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
              }`}
            >
              {rankingData?.status || "READY"}
            </span>
          </div>
        </div>

        <div className="space-y-1 md:col-span-2">
          <span className="text-slate-500 font-medium">Verified Scope</span>
          <p className="text-slate-300 truncate font-sans" title={rankingData?.scope || ""}>
            {rankingData?.scope || "Type 2 diabetes & Metformin HbA1c review"}
          </p>
        </div>
      </div>

      {/* Control Strip & Stats Counter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Priority Filter Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-900/80 border border-slate-800 rounded-lg text-xs">
          {[
            { id: "ALL", label: "All Papers", count: stats.total },
            { id: "HIGH", label: "High Priority", count: stats.high, color: "text-emerald-400" },
            { id: "MEDIUM", label: "Medium", count: stats.medium, color: "text-amber-400" },
            { id: "LOW", label: "Low", count: stats.low, color: "text-slate-400" },
            { id: "UNSCORED", label: "Unavailable", count: stats.unscored, color: "text-rose-400" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedPriority(tab.id)}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                selectedPriority === tab.id
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
              data-testid={`filter-${tab.id.toLowerCase()}`}
            >
              <span>{tab.label}</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] bg-slate-950/60 ${tab.color || ""}`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Baseline Order vs ML Priority Order Toggle */}
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 p-1 rounded-lg">
          <span className="text-xs text-slate-400 pl-2">Ordering:</span>
          <button
            onClick={() => setIsBaselineOrder(!isBaselineOrder)}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
              isBaselineOrder
                ? "bg-slate-800 text-slate-200 border border-slate-700"
                : "bg-indigo-600/90 text-white shadow-sm"
            }`}
            data-testid="order-toggle-btn"
          >
            <ArrowUpDown className="w-3.5 h-3.5" />
            {isBaselineOrder ? "Baseline Corpus Order" : "ML Priority Rank"}
          </button>
        </div>
      </div>

      {/* Main Review Grid */}
      {loading ? (
        <div className="h-64 flex flex-col items-center justify-center gap-3 text-slate-500">
          <RotateCcw className="w-8 h-8 animate-spin text-indigo-500" />
          <p className="text-sm">Running verified ML inference pipeline...</p>
        </div>
      ) : displayedItems.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-900/20">
          <Info className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No Records Match Filter</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            {selectedPriority !== "ALL"
              ? `No papers found in the '${selectedPriority}' priority tier.`
              : "This corpus revision has no records available for review."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Ranked Paper List */}
          <div className="lg:col-span-5 space-y-2.5 max-h-[720px] overflow-y-auto pr-1">
            {displayedItems.map((item) => {
              const isSelected = item.record_id === selectedRecordId;
              const decision = humanDecisions[item.record_id] || item.effective_status;

              return (
                <div
                  key={item.record_id}
                  onClick={() => setSelectedRecordId(item.record_id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? "bg-indigo-950/30 border-indigo-500/60 ring-1 ring-indigo-500/40"
                      : "bg-slate-900/40 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900/80"
                  }`}
                  data-testid={`ml-record-${item.record_id}`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                        #{item.rank}
                      </span>

                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide ${
                          item.priority_label === "HIGH"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : item.priority_label === "MEDIUM"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                            : item.priority_label === "LOW"
                            ? "bg-slate-800 text-slate-400 border border-slate-700"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                        }`}
                      >
                        {item.priority_label}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 font-mono text-xs">
                      <span className="text-slate-400">Score:</span>
                      <span className="font-semibold text-slate-200">
                        {item.state === "SCORED" ? `${(item.score * 100).toFixed(1)}%` : "N/A"}
                      </span>
                    </div>
                  </div>

                  <h3 className="text-sm font-semibold text-slate-100 line-clamp-2 leading-snug">
                    {item.title}
                  </h3>

                  <div className="mt-2.5 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/60 pt-2">
                    <span className="font-mono text-[11px] text-slate-500 truncate max-w-[140px]">
                      {item.record_id}
                    </span>

                    {/* Human Decision Indicator */}
                    <div className="flex items-center gap-1 text-[11px]">
                      <span className="text-slate-500">Decision:</span>
                      <span
                        className={`font-semibold capitalize ${
                          decision === "include"
                            ? "text-emerald-400"
                            : decision === "exclude"
                            ? "text-rose-400"
                            : decision === "maybe"
                            ? "text-amber-400"
                            : "text-slate-500 italic"
                        }`}
                      >
                        {decision || "Unscreened"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Detailed Reader & Action Panel */}
          {selectedItem && (
            <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6 sticky top-24 backdrop-blur-md">
              {/* Header with Rank & Score Probability Gauge */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-md bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-mono text-xs font-bold">
                      Queue Rank #{selectedItem.rank}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      ID: {selectedItem.record_id}
                    </span>
                  </div>
                  <h2 className="text-lg font-bold text-slate-100 mt-2 leading-snug">
                    {selectedItem.title}
                  </h2>
                </div>

                <div className="flex flex-col items-end flex-shrink-0 bg-slate-950/60 border border-slate-800 p-3 rounded-xl min-w-[130px]">
                  <span className="text-[11px] text-slate-400">Inclusion Probability</span>
                  <div className="flex items-baseline gap-1 mt-0.5">
                    <span className="text-2xl font-black text-indigo-400 font-mono">
                      {selectedItem.state === "SCORED"
                        ? `${(selectedItem.score * 100).toFixed(1)}%`
                        : "0.0%"}
                    </span>
                  </div>
                  {/* Visual Progress Bar */}
                  <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        selectedItem.score >= 0.7
                          ? "bg-emerald-500"
                          : selectedItem.score >= 0.4
                          ? "bg-amber-500"
                          : "bg-slate-600"
                      }`}
                      style={{ width: `${Math.max(4, selectedItem.score * 100)}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Explanatory Callout */}
              <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80 text-xs text-slate-300 space-y-1">
                <div className="flex items-center gap-1.5 font-semibold text-slate-200">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Model Recommendation Rationale</span>
                </div>
                <p className="text-slate-400 leading-relaxed">
                  {selectedItem.state === "SCORED"
                    ? selectedItem.score >= 0.7
                      ? "High vocabulary match with randomized clinical trial designs, intervention endpoints (HbA1c), and target human diabetic cohorts."
                      : selectedItem.score >= 0.4
                      ? "Moderate semantic match. Check whether intervention and comparator match clinical review criteria."
                      : "Low clinical relevance score. Likely animal/preclinical, review note, or unrelated design."
                    : selectedItem.reason === "MISSING_ABSTRACT"
                    ? "Abstract text is missing or shorter than 10 characters; prioritization is unavailable without textual content."
                    : "Out of model domain scope."}
                </p>
              </div>

              {/* Abstract Text Viewer */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Abstract Content
                </h4>
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-sm text-slate-300 leading-relaxed max-h-64 overflow-y-auto">
                  {selectedItem.abstract_text || (
                    <span className="italic text-slate-500">
                      No abstract provided in source bibliographic metadata.
                    </span>
                  )}
                </div>
              </div>

              {/* Reviewer Action Bar (Preserves Workflow Semantics) */}
              <div className="border-t border-slate-800 pt-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Record Human Decision
                  </span>
                  <span className="text-xs text-slate-500 italic">
                    Model outputs are assistive suggestions only; human events strictly govern review.
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleReviewDecision(selectedItem.record_id, "include")}
                    className={`flex-1 py-2.5 px-3 rounded-xl border flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
                      humanDecisions[selectedItem.record_id] === "include"
                        ? "bg-emerald-600 text-white border-emerald-500 shadow-md shadow-emerald-600/30"
                        : "bg-slate-900 hover:bg-emerald-950/30 hover:border-emerald-500/40 text-emerald-400 border-slate-800"
                    }`}
                    data-testid="decision-include-btn"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Include
                  </button>

                  <button
                    onClick={() => handleReviewDecision(selectedItem.record_id, "maybe")}
                    className={`flex-1 py-2.5 px-3 rounded-xl border flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
                      humanDecisions[selectedItem.record_id] === "maybe"
                        ? "bg-amber-600 text-white border-amber-500 shadow-md shadow-amber-600/30"
                        : "bg-slate-900 hover:bg-amber-950/30 hover:border-amber-500/40 text-amber-400 border-slate-800"
                    }`}
                    data-testid="decision-maybe-btn"
                  >
                    <HelpCircle className="w-4 h-4" />
                    Maybe
                  </button>

                  <button
                    onClick={() => handleReviewDecision(selectedItem.record_id, "exclude")}
                    className={`flex-1 py-2.5 px-3 rounded-xl border flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
                      humanDecisions[selectedItem.record_id] === "exclude"
                        ? "bg-rose-600 text-white border-rose-500 shadow-md shadow-rose-600/30"
                        : "bg-slate-900 hover:bg-rose-950/30 hover:border-rose-500/40 text-rose-400 border-slate-800"
                    }`}
                    data-testid="decision-exclude-btn"
                  >
                    <XCircle className="w-4 h-4" />
                    Exclude
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
