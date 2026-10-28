import React, { useState, useEffect } from "react";
import { ErrorState, LoadingRegion, Skeleton, SkeletonText, errorKind } from "../../components/Feedback";
import { Scale } from "lucide-react";
import {
  api,
  DevilsAdvocateChallengeResponse,
  ChallengeDisposition,
  ChallengeRecommendation,
  VulnerabilityFlag,
} from "../../api/client";

interface DevilsAdvocateCardProps {
  workspaceId: string;
  groupId: string;
  effectiveDecision?: string;
  exclusionReason?: string | null;
  onDecisionUpdated?: () => void;
}

export const DevilsAdvocateCard: React.FC<DevilsAdvocateCardProps> = ({
  workspaceId,
  groupId,
  effectiveDecision,
  exclusionReason,
  onDecisionUpdated,
}) => {
  const [challenge, setChallenge] = useState<DevilsAdvocateChallengeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<unknown>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  // Disposition dialog states
  const [actionType, setActionType] = useState<"concede" | "uphold" | "dismiss" | null>(null);
  const [concededDecision, setConcededDecision] = useState<"include" | "maybe">("maybe");
  const [dispositionNotes, setDispositionNotes] = useState<string>("");
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);

  useEffect(() => {
    loadChallenge();
  }, [workspaceId, groupId]);

  const loadChallenge = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.devilsAdvocate.getChallenge(workspaceId, groupId);
      setChallenge(data);
    } catch (err: unknown) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleForceRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const data = await api.devilsAdvocate.generateChallenge(workspaceId, groupId, {
        force_refresh: true,
        proposed_decision: effectiveDecision,
        exclusion_reason: exclusionReason || undefined,
      });
      setChallenge(data);
    } catch (err: any) {
      setError(err?.message || "Failed to regenerate Devil's Advocate challenge.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleSubmitDisposition = async () => {
    if (!actionType) return;
    setSubmittingAction(true);
    try {
      let disp: ChallengeDisposition;
      if (actionType === "concede") disp = "conceded";
      else if (actionType === "uphold") disp = "upheld";
      else disp = "dismissed";

      const updated = await api.devilsAdvocate.recordDisposition(workspaceId, groupId, {
        disposition: disp,
        notes: dispositionNotes.trim() || undefined,
        actor_id: "human-reviewer",
        conceded_decision: actionType === "concede" ? concededDecision : undefined,
      });
      setChallenge(updated);
      setActionType(null);
      setDispositionNotes("");
      if (actionType === "concede" && onDecisionUpdated) {
        onDecisionUpdated();
      }
    } catch (err: any) {
      alert(err?.message || "Failed to record disposition.");
    } finally {
      setSubmittingAction(false);
    }
  };

  if (loading) {
    return (
      <LoadingRegion label="Loading the devil's advocate assessment" className="glass-panel p-6 space-y-4">
        <Skeleton className="h-5 w-1/2" />
        <SkeletonText lines={3} />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-24 rounded-lg" />
          <Skeleton className="h-8 w-24 rounded-lg" />
        </div>
      </LoadingRegion>
    );
  }

  if (error != null && errorKind(error) !== "notFound") {
    return <ErrorState compact error={error} onRetry={loadChallenge} what="The devil's advocate assessment" />;
  }

  if (!challenge) {
    return (
      <div className="glass-panel p-6 text-center space-y-1">
        <p className="text-sm font-semibold text-[var(--text-primary)]">No challenge for this record yet</p>
        <p className="text-sm text-[var(--text-muted)]">
          A challenge is created automatically when a record is excluded, so you can check the exclusion holds up.
        </p>
      </div>
    );
  }

  const getRecommendationBadge = (rec: ChallengeRecommendation) => {
    switch (rec) {
      case "reconsider_exclusion":
        return {
          bg: "bg-rose-500/10 text-rose-400 border-rose-500/30",
          label: "Reconsider exclusion",
          desc: "Substantial evidence identified that challenges this exclusion.",
        };
      case "needs_human_review":
        return {
          bg: "bg-amber-500/10 text-amber-400 border-amber-500/30",
          label: "🔍 Needs Human Review",
          desc: "Ambiguity or textual limitation warrants dual-screening deliberation.",
        };
      default:
        return {
          bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
          label: "✓ Exclusion Upheld",
          desc: "Stated exclusion criteria align with examined study text.",
        };
    }
  };

  const getDispositionBadge = (disp: ChallengeDisposition) => {
    switch (disp) {
      case "conceded":
        return { bg: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40", label: "Conceded (Reversed)" };
      case "upheld":
        return { bg: "bg-slate-700 text-slate-300 border-slate-600", label: "Upheld by Reviewer" };
      case "dismissed":
        return { bg: "bg-slate-800 text-slate-400 border-slate-700", label: "Dismissed" };
      default:
        return { bg: "bg-amber-500/20 text-amber-300 border-amber-500/40", label: "Pending Review" };
    }
  };

  const formatFlagLabel = (flag: VulnerabilityFlag): string => {
    switch (flag) {
      case "abstract_only_limitation":
        return "Abstract Only Limitation";
      case "uncertain_pico_element":
        return "Uncertain PICO Element";
      case "overlooked_subgroup":
        return "Overlooked Subgroup";
      case "indirect_comparator":
        return "Indirect Comparator";
      case "surrogate_outcome":
        return "Surrogate Outcome";
      case "weak_rationale":
        return "Weak Rationale";
      case "criteria_ambiguity":
        return "Criteria Ambiguity";
      case "counter_evidence_found":
        return "Counter-Evidence Found";
      default:
        return flag;
    }
  };

  const recBadge = getRecommendationBadge(challenge.recommendation);
  const dispBadge = getDispositionBadge(challenge.disposition);
  const vulnPercent = Math.round(challenge.vulnerability_score * 100);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      {/* Header & Score Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <Scale className="w-4 h-4 text-amber-400" aria-hidden="true" /> Devil's Advocate Reviewer
            </h3>
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${dispBadge.bg}`}>
              {dispBadge.label}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Independent challenge pass to protect against false exclusions in systematic reviews.
          </p>
        </div>

        <button
          onClick={handleForceRefresh}
          disabled={refreshing}
          className="self-start sm:self-auto px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-md font-medium transition-colors flex items-center gap-1.5"
        >
          {refreshing ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
              Re-evaluating...
            </>
          ) : (
            <>
              <span>↺</span> Re-evaluate Challenge
            </>
          )}
        </button>
      </div>

      {/* Recommendation Banner */}
      <div className={`p-4 rounded-lg border ${recBadge.bg}`}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h4 className="text-sm font-semibold">{recBadge.label}</h4>
            <p className="text-xs opacity-90 mt-0.5">{recBadge.desc}</p>
          </div>
          <div className="text-right flex-shrink-0">
            <span className="text-xs uppercase tracking-wider font-semibold opacity-75">Vulnerability</span>
            <div className="text-lg font-bold">{vulnPercent}%</div>
          </div>
        </div>

        {/* Vulnerability Progress Bar */}
        <div className="w-full bg-slate-800/80 rounded-full h-1.5 mt-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              vulnPercent >= 60 ? "bg-rose-500" : vulnPercent >= 35 ? "bg-amber-500" : "bg-emerald-500"
            }`}
            style={{ width: `${vulnPercent}%` }}
          />
        </div>
      </div>

      {/* Challenged Rationale Summary */}
      <div className="bg-slate-950/60 p-3.5 rounded-lg border border-slate-800/80 text-xs">
        <div className="text-slate-400 font-medium mb-1">Challenged Exclusion Rationale:</div>
        <div className="text-slate-200 italic font-mono bg-slate-900/80 px-2.5 py-1.5 rounded border border-slate-800">
          "{challenge.original_exclusion_reason || "No explicit reason specified"}"
        </div>
      </div>

      {/* Vulnerability Flags */}
      {(challenge.vulnerability_flags && challenge.vulnerability_flags.length > 0) && (
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Identified Fragility Factors
          </div>
          <div className="flex flex-wrap gap-1.5">
            {challenge.vulnerability_flags.map((flag) => (
              <span
                key={flag}
                className="px-2 py-0.5 text-xs bg-slate-800 text-slate-300 border border-slate-700 rounded-md font-medium"
              >
                🚩 {formatFlagLabel(flag)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Critique */}
      <div>
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
          Adversarial Critique
        </div>
        <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800">
          {challenge.critique}
        </p>
      </div>

      {/* Counter-Arguments & Quotes */}
      <div>
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Counter-Evidence & Quotes ({(challenge.counter_arguments || []).length})
        </div>

        {(!challenge.counter_arguments || challenge.counter_arguments.length === 0) ? (
          <div className="text-xs text-slate-500 italic p-3 bg-slate-950/30 rounded border border-slate-800/60">
            No strong counter-evidence located in examined title or abstract text.
          </div>
        ) : (
          <div className="space-y-2">
            {challenge.counter_arguments.map((ca, idx) => (
              <div
                key={idx}
                className="p-3 bg-slate-950/50 border border-slate-800/90 rounded-lg space-y-1.5 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">{ca.argument}</span>
                  <span className="px-2 py-0.5 text-[10px] font-medium bg-slate-800 text-slate-300 rounded border border-slate-700 capitalize">
                    {ca.relevance_aspect}
                  </span>
                </div>
                <div className="text-emerald-400 font-mono bg-emerald-950/30 px-2 py-1.5 rounded border border-emerald-900/40 italic">
                  "{ca.supporting_quote}"
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reviewer Action Bar */}
      <div className="pt-3 border-t border-slate-800">
        {actionType === null ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-slate-400">
              Reviewer Action:{" "}
              <strong className="text-slate-200">
                {challenge.disposition === "pending"
                  ? "Deliberation Needed"
                  : `Currently ${challenge.disposition}`}
              </strong>
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setActionType("concede")}
                className="px-3 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-md transition-colors shadow-sm"
              >
                Concede & Reconsider
              </button>
              <button
                onClick={() => setActionType("uphold")}
                className="px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-md transition-colors"
              >
                Uphold Exclusion
              </button>
              <button
                onClick={() => setActionType("dismiss")}
                className="px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-300 transition-colors"
              >
                Dismiss
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h5 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                {actionType === "concede" && "Concede to Challenge: Reconsider Paper"}
                {actionType === "uphold" && "Uphold Exclusion Rationale"}
                {actionType === "dismiss" && "Dismiss Challenge"}
              </h5>
              <button
                onClick={() => setActionType(null)}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                Cancel
              </button>
            </div>

            {actionType === "concede" && (
              <div>
                <label className="block text-xs text-slate-400 font-medium mb-1">
                  New Screening Decision:
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setConcededDecision("maybe")}
                    className={`px-3 py-1 text-xs rounded border font-medium ${
                      concededDecision === "maybe"
                        ? "bg-amber-600 border-amber-500 text-white"
                        : "bg-slate-800 border-slate-700 text-slate-300"
                    }`}
                  >
                    Mark Maybe (Full-Text Retrieval)
                  </button>
                  <button
                    type="button"
                    onClick={() => setConcededDecision("include")}
                    className={`px-3 py-1 text-xs rounded border font-medium ${
                      concededDecision === "include"
                        ? "bg-emerald-600 border-emerald-500 text-white"
                        : "bg-slate-800 border-slate-700 text-slate-300"
                    }`}
                  >
                    Include Paper
                  </button>
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs text-slate-400 font-medium mb-1">
                Reviewer Rationale & Notes:
              </label>
              <textarea
                value={dispositionNotes}
                onChange={(e) => setDispositionNotes(e.target.value)}
                placeholder={
                  actionType === "concede"
                    ? "Explain why the challenge was accepted (e.g., abstract mentions subgroup; warrants full-text review)..."
                    : actionType === "uphold"
                    ? "Explain why the exclusion stands despite the counter-arguments..."
                    : "Notes on why this challenge was dismissed..."
                }
                rows={2}
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setActionType(null)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitDisposition}
                disabled={submittingAction}
                className="px-3 py-1.5 text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white rounded transition-colors"
              >
                {submittingAction ? "Submitting..." : "Submit Reviewer Response"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
