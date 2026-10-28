import React, { useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  AlertCircle,
  Clock,
  Sparkles,
  Edit3,
  RotateCcw,
  ShieldAlert,
  ChevronRight,
  FileText,
  UserCheck,
  Check,
  X,
} from "lucide-react";
import {
  api,
  type ArticleRadarResponse,
  type RadarEvidenceStatus,
  type RadarFieldDetail,
  type RadarHumanReviewStatus,
} from "../../api/client";

interface ArticleRadarWidgetProps {
  radar: ArticleRadarResponse;
  workspaceId: string;
  groupId: string;
  onRadarUpdated: (updated: ArticleRadarResponse) => void;
}

export const ArticleRadarWidget: React.FC<ArticleRadarWidgetProps> = ({
  radar,
  workspaceId,
  groupId,
  onRadarUpdated,
}) => {
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Form states for human review actions
  const [mode, setMode] = useState<"view" | "correct" | "uncertain" | "conflict">("view");
  const [correctValue, setCorrectValue] = useState("");
  const [correctReason, setCorrectReason] = useState("");
  const [uncertainNote, setUncertainNote] = useState("");
  const [conflictNote, setConflictNote] = useState("");

  const activeFieldDetail: RadarFieldDetail | null = selectedField
    ? radar.pico[selectedField] || null
    : null;

  const handleOpenDetail = (fieldType: string) => {
    setSelectedField(fieldType);
    setMode("view");
    setActionError(null);
    setActionSuccess(null);
    const detail = radar.pico[fieldType];
    if (detail) {
      setCorrectValue(detail.claim_value || "");
      setCorrectReason("");
      setUncertainNote(detail.uncertainty_note || "");
      setConflictNote("");
    }
  };

  const handleConfirm = async () => {
    if (!selectedField) return;
    setIsSubmitting(true);
    setActionError(null);
    try {
      const updated = await api.radar.confirmField(workspaceId, groupId, selectedField, {
        actor_id: "reviewer",
        notes: "Confirmed by reviewer in PICO Radar",
      });
      onRadarUpdated(updated);
      setActionSuccess("Field successfully confirmed as verified.");
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to confirm field");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCorrect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedField) return;
    if (!correctReason.trim()) {
      setActionError("A rationale for the correction is mandatory for systematic review auditability.");
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      const updated = await api.radar.correctField(workspaceId, groupId, selectedField, {
        claim_value: correctValue.trim(),
        reason: correctReason.trim(),
        actor_id: "reviewer",
      });
      onRadarUpdated(updated);
      setMode("view");
      setActionSuccess("PICO correction saved with persistent audit history.");
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to save correction");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFlagUncertain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedField) return;
    if (!uncertainNote.trim()) {
      setActionError("Please provide an explanation for the ambiguity or uncertainty.");
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      const updated = await api.radar.flagUncertain(workspaceId, groupId, selectedField, {
        uncertainty_note: uncertainNote.trim(),
        actor_id: "reviewer",
      });
      onRadarUpdated(updated);
      setMode("view");
      setActionSuccess("Field flagged as uncertain and routed to human review.");
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to flag uncertainty");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFlagConflict = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedField) return;
    if (!conflictNote.trim()) {
      setActionError("Please describe the conflicting passages or interpretations.");
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      const updated = await api.radar.flagConflict(workspaceId, groupId, selectedField, {
        conflict_explanation: conflictNote.trim(),
        actor_id: "reviewer",
      });
      onRadarUpdated(updated);
      setMode("view");
      setActionSuccess("Conflicting evidence flagged and routed to conflict resolution.");
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to flag conflict");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevalidate = async () => {
    if (!selectedField) return;
    setIsSubmitting(true);
    setActionError(null);
    try {
      const updated = await api.radar.revalidateField(workspaceId, groupId, selectedField);
      onRadarUpdated(updated);
      setActionSuccess("Evidence quote revalidated against source text.");
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to revalidate evidence");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status: RadarEvidenceStatus) => {
    switch (status) {
      case "supported":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>Supported</span>
          </span>
        );
      case "uncertain":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <HelpCircle className="w-3 h-3 text-amber-400" />
            <span>Uncertain / Needs Review</span>
          </span>
        );
      case "not_found":
        return (
          <span
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700"
            title="No adequate evidence found in examined text (e.g. abstract only). This does NOT automatically exclude the paper."
          >
            <AlertCircle className="w-3 h-3 text-slate-400" />
            <span>Not found in examined text</span>
          </span>
        );
      case "conflicting":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            <span>Conflicting Evidence</span>
          </span>
        );
      case "stale":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <Clock className="w-3 h-3 text-purple-400" />
            <span>Stale Evidence (Text Changed)</span>
          </span>
        );
      case "not_assessed":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-900 text-slate-400 border border-slate-800">
            <span>Not Assessed / No Source</span>
          </span>
        );
    }
  };

  const getHumanReviewBadge = (hStatus: RadarHumanReviewStatus) => {
    if (hStatus === "confirmed") {
      return (
        <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 flex items-center gap-1">
          <UserCheck className="w-2.5 h-2.5" />
          <span>Human Confirmed</span>
        </span>
      );
    }
    if (hStatus === "corrected") {
      return (
        <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-indigo-950/60 text-indigo-300 border border-indigo-800/60 flex items-center gap-1">
          <Edit3 className="w-2.5 h-2.5" />
          <span>Human Corrected</span>
        </span>
      );
    }
    return null;
  };

  const fieldsOrder = ["population", "intervention", "comparator", "outcome"];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
            Missing-Evidence Radar (PICO)
          </h3>
          <span className="px-2 py-0.2 text-[10px] font-mono rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
            Coverage: {radar.overall_coverage_pct}%
          </span>
          {radar.needs_human_review && (
            <span className="px-2 py-0.2 text-[10px] font-medium rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Needs Human Review
            </span>
          )}
        </div>

        <span className="text-[11px] text-slate-400 italic">
          Examined: <strong className="text-slate-300 capitalize">{radar.source_field}</strong>
        </span>
      </div>

      {/* 4 PICO Dimension Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {fieldsOrder.map((key) => {
          const field = radar.pico[key];
          if (!field) return null;

          return (
            <div
              key={key}
              onClick={() => handleOpenDetail(key)}
              className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-950 hover:border-slate-700 transition cursor-pointer flex flex-col justify-between space-y-2 group"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-white group-hover:text-cyan-400 transition">
                    {field.field_label}
                  </span>
                  {getHumanReviewBadge(field.human_review_status)}
                </div>

                <div className="mb-2">{getStatusBadge(field.radar_status)}</div>

                <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                  {field.claim_value || <em className="text-slate-500">Not found in examined text</em>}
                </p>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span>{field.supporting_quote ? "Quote attached" : "No quote"}</span>
                <span className="text-cyan-400 group-hover:translate-x-0.5 transition flex items-center gap-0.5">
                  <span>Inspect</span>
                  <ChevronRight className="w-3 h-3" />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Evidence Detail & Human Review Modal */}
      {selectedField && activeFieldDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">
                    {activeFieldDetail.field_label} Evidence Radar
                  </h3>
                  {getStatusBadge(activeFieldDetail.radar_status)}
                  {getHumanReviewBadge(activeFieldDetail.human_review_status)}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Article: <span className="text-slate-200 font-medium">{radar.paper_title}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedField(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Notification messages */}
            {actionSuccess && (
              <div className="p-3 bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 rounded-lg text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{actionSuccess}</span>
              </div>
            )}
            {actionError && (
              <div className="p-3 bg-rose-950/40 border border-rose-500/40 text-rose-300 rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            {/* Mode Switcher */}
            <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-800 pb-2 text-xs">
              <button
                onClick={() => setMode("view")}
                className={`px-3 py-1.5 rounded-lg font-medium transition ${
                  mode === "view" ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                Evidence Details
              </button>
              <button
                onClick={() => setMode("correct")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1 ${
                  mode === "correct" ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Correct Value</span>
              </button>
              <button
                onClick={() => setMode("uncertain")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1 ${
                  mode === "uncertain" ? "bg-amber-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Flag Uncertain</span>
              </button>
              <button
                onClick={() => setMode("conflict")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1 ${
                  mode === "conflict" ? "bg-rose-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Flag Conflict</span>
              </button>
            </div>

            {/* Tab 1: View Evidence Details */}
            {mode === "view" && (
              <div className="space-y-4 text-xs">
                {/* Current Extracted Value */}
                <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Current Extracted Value
                  </span>
                  <p className="text-white text-sm font-medium leading-relaxed">
                    {activeFieldDetail.claim_value || (
                      <em className="text-slate-500 font-normal">
                        Not found in examined {radar.source_field}
                      </em>
                    )}
                  </p>
                  {activeFieldDetail.original_claim_value &&
                    activeFieldDetail.original_claim_value !== activeFieldDetail.claim_value && (
                      <div className="mt-2 pt-2 border-t border-slate-800 text-slate-400 text-[11px]">
                        <span>Original AI extraction: </span>
                        <span className="line-through text-slate-400">
                          {activeFieldDetail.original_claim_value}
                        </span>
                      </div>
                    )}
                </div>

                {/* Supporting Quote Passage */}
                <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Supporting Source Passage ({radar.source_field})
                    </span>
                    {activeFieldDetail.start_cp !== null && activeFieldDetail.end_cp !== null && (
                      <span className="font-mono text-[10px] text-cyan-400">
                        Offsets: [{activeFieldDetail.start_cp}:{activeFieldDetail.end_cp})
                      </span>
                    )}
                  </div>

                  {activeFieldDetail.supporting_quote ? (
                    <blockquote className="border-l-2 border-cyan-500 pl-3 py-1 text-slate-200 italic leading-relaxed bg-slate-900/60 rounded-r">
                      "{activeFieldDetail.supporting_quote}"
                    </blockquote>
                  ) : (
                    <p className="text-slate-400 italic">
                      No direct supporting passage located in examined {radar.source_field}.
                    </p>
                  )}

                  <div className="pt-2 text-[11px] text-slate-400 flex items-center justify-between">
                    <span>Validation: {activeFieldDetail.validation_message || "Not assessed"}</span>
                    {activeFieldDetail.radar_status === "stale" && (
                      <button
                        onClick={handleRevalidate}
                        disabled={isSubmitting}
                        className="px-2 py-0.5 rounded bg-purple-900/40 hover:bg-purple-800 text-purple-200 text-[11px] font-medium border border-purple-500/40 flex items-center gap-1 transition"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Revalidate against current text</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Audit & Uncertainty Notes */}
                {(activeFieldDetail.uncertainty_note ||
                  activeFieldDetail.reviewer_correction_reason ||
                  activeFieldDetail.reviewer_notes) && (
                  <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Audit Trail & Reviewer Notes
                    </span>
                    {activeFieldDetail.uncertainty_note && (
                      <p className="text-amber-300 text-xs bg-amber-950/30 p-2 rounded border border-amber-800/40">
                        <strong>Uncertainty note:</strong> {activeFieldDetail.uncertainty_note}
                      </p>
                    )}
                    {activeFieldDetail.reviewer_correction_reason && (
                      <p className="text-indigo-300 text-xs bg-indigo-950/30 p-2 rounded border border-indigo-800/40">
                        <strong>Correction rationale:</strong>{" "}
                        {activeFieldDetail.reviewer_correction_reason}
                      </p>
                    )}
                    {activeFieldDetail.reviewer_notes && (
                      <p className="text-slate-300 text-xs bg-slate-900/60 p-2 rounded border border-slate-800">
                        <strong>Reviewer note:</strong> {activeFieldDetail.reviewer_notes}
                      </p>
                    )}
                  </div>
                )}

                {/* Highlighted Full Abstract in Context */}
                {radar.source_text && (
                  <div className="space-y-1.5 pt-2 border-t border-slate-800">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                      <FileText className="w-3 h-3 text-cyan-400" />
                      <span>Full Examined Abstract (Passage In Context)</span>
                    </span>
                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-slate-300 text-xs max-h-48 overflow-y-auto leading-relaxed">
                      {activeFieldDetail.supporting_quote &&
                      radar.source_text.includes(activeFieldDetail.supporting_quote) ? (
                        <>
                          {radar.source_text
                            .split(activeFieldDetail.supporting_quote)
                            .map((part, i, arr) => (
                              <React.Fragment key={i}>
                                <span>{part}</span>
                                {i < arr.length - 1 && (
                                  <mark className="bg-cyan-500/30 text-cyan-200 border-b-2 border-cyan-400 px-0.5 rounded">
                                    {activeFieldDetail.supporting_quote}
                                  </mark>
                                )}
                              </React.Fragment>
                            ))}
                        </>
                      ) : (
                        <span>{radar.source_text}</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Action Footer */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                  <span className="text-[11px] text-slate-400">
                    SLR Guarantee: PICO edits do not change screening decisions.
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleConfirm}
                      disabled={isSubmitting || activeFieldDetail.human_review_status === "confirmed"}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 disabled:opacity-50"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Confirm as Verified</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 2: Correct Value */}
            {mode === "correct" && (
              <form onSubmit={handleCorrect} className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-200 block mb-1">
                    Corrected Clinical Value
                  </label>
                  <textarea
                    rows={2}
                    value={correctValue}
                    onChange={(e) => setCorrectValue(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-cyan-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-200 block mb-1">
                    Correction Rationale (Mandatory for systematic review audit)
                  </label>
                  <textarea
                    rows={2}
                    value={correctReason}
                    onChange={(e) => setCorrectReason(e.target.value)}
                    placeholder="e.g., Extracted pediatric population missed adolescent cohort mentioned in line 3..."
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-cyan-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setMode("view")}
                    className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-lg"
                  >
                    Save Correction
                  </button>
                </div>
              </form>
            )}

            {/* Tab 3: Flag Uncertain */}
            {mode === "uncertain" && (
              <form onSubmit={handleFlagUncertain} className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-200 block mb-1">
                    Uncertainty / Ambiguity Explanation
                  </label>
                  <textarea
                    rows={3}
                    value={uncertainNote}
                    onChange={(e) => setUncertainNote(e.target.value)}
                    placeholder="e.g., The abstract mentions multiple comparison groups without specifying primary control..."
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-amber-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setMode("view")}
                    className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-lg"
                  >
                    Mark Uncertain & Flag for Review
                  </button>
                </div>
              </form>
            )}

            {/* Tab 4: Flag Conflict */}
            {mode === "conflict" && (
              <form onSubmit={handleFlagConflict} className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-200 block mb-1">
                    Conflicting Evidence Explanation
                  </label>
                  <textarea
                    rows={3}
                    value={conflictNote}
                    onChange={(e) => setConflictNote(e.target.value)}
                    placeholder="e.g., Abstract states dose was 50mg in methods but reports 100mg in results table..."
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-rose-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setMode("view")}
                    className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-lg"
                  >
                    Flag Conflicting Evidence
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
