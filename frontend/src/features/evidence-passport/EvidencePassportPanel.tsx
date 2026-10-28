import React, { useState, useEffect, useRef } from "react";
import {
  ShieldCheck,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  RefreshCw,
  XCircle,
  HelpCircle,
  FileText,
  UserCheck,
  Download,
  Edit3,
  ExternalLink,
  ChevronRight,
  Filter,
  Sparkles,
  Info,
} from "lucide-react";
import {
  api,
  type EvidencePassportBundle,
  type EvidenceItemResponse,
  type EvidenceClaimType,
  type EvidenceValidationStatus,
  type EvidenceSemanticAssessment,
  type EvidenceCorrectionRequest,
} from "../../api/client";

interface EvidencePassportPanelProps {
  workspaceId: string;
  groupId: string;
  initialBundle?: EvidencePassportBundle | null;
  onRefreshGroup?: () => void;
}

export const EvidencePassportPanel: React.FC<EvidencePassportPanelProps> = ({
  workspaceId,
  groupId,
  initialBundle,
  onRefreshGroup,
}) => {
  const [bundle, setBundle] = useState<EvidencePassportBundle | null>(initialBundle || null);
  const [loading, setLoading] = useState(false);
  const [revalidating, setRevalidating] = useState(false);
  const [filter, setFilter] = useState<"all" | "pico" | "screening_rationale" | "needs_review">("all");
  const [selectedItem, setSelectedItem] = useState<EvidenceItemResponse | null>(null);

  // Correction Modal
  const [correctingItem, setCorrectingItem] = useState<EvidenceItemResponse | null>(null);
  const [editClaimValue, setEditClaimValue] = useState("");
  const [editQuote, setEditQuote] = useState("");
  const [editSemantic, setEditSemantic] = useState<EvidenceSemanticAssessment>("supports");
  const [editReason, setEditReason] = useState("");
  const [submittingCorrection, setSubmittingCorrection] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const abstractRef = useRef<HTMLDivElement>(null);

  // Fetch bundle if not provided or on groupId change
  useEffect(() => {
    let isMounted = true;
    async function loadBundle() {
      try {
        setLoading(true);
        setActionError(null);
        const data = await api.evidence.getBundle(workspaceId, groupId);
        if (isMounted) {
          setBundle(data);
          if (data.items && data.items.length > 0 && !selectedItem) {
            setSelectedItem(data.items[0]);
          }
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load Evidence Passport";
          setActionError(msg);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadBundle();
    return () => {
      isMounted = false;
    };
  }, [workspaceId, groupId]);

  const handleRevalidate = async () => {
    try {
      setRevalidating(true);
      setActionError(null);
      await api.evidence.revalidateGroup(workspaceId, groupId);
      const updated = await api.evidence.getBundle(workspaceId, groupId);
      setBundle(updated);
      setActionSuccess("All evidence claims revalidated against stored source text.");
      setTimeout(() => setActionSuccess(null), 4000);
      if (onRefreshGroup) onRefreshGroup();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Revalidation failed");
    } finally {
      setRevalidating(false);
    }
  };

  const openCorrectionModal = (item: EvidenceItemResponse) => {
    setCorrectingItem(item);
    setEditClaimValue(item.claim_value);
    setEditQuote(item.supporting_quote);
    setEditSemantic(item.semantic_assessment === "unassessed" ? "supports" : item.semantic_assessment);
    setEditReason("");
    setActionError(null);
  };

  const handleSaveCorrection = async () => {
    if (!correctingItem) return;
    if (!editClaimValue.trim()) {
      setActionError("Claim text cannot be empty.");
      return;
    }
    if (!editReason.trim()) {
      setActionError("Please provide a short justification reason for this correction.");
      return;
    }

    try {
      setSubmittingCorrection(true);
      setActionError(null);
      const req: EvidenceCorrectionRequest = {
        claim_value: editClaimValue.trim(),
        supporting_quote: editQuote.trim() || undefined,
        semantic_assessment: editSemantic,
        reason: editReason.trim(),
        actor_id: "reviewer_lead",
      };

      await api.evidence.correctItem(workspaceId, correctingItem.id, req);
      const updated = await api.evidence.getBundle(workspaceId, groupId);
      setBundle(updated);
      setCorrectingItem(null);
      setActionSuccess("Reviewer correction saved and auditable history updated.");
      setTimeout(() => setActionSuccess(null), 4000);
      if (onRefreshGroup) onRefreshGroup();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to save correction");
    } finally {
      setSubmittingCorrection(false);
    }
  };

  const getValidationBadge = (status: EvidenceValidationStatus) => {
    switch (status) {
      case "verified":
        return {
          icon: <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />,
          label: "Quotation Verified",
          classes: "bg-emerald-950/80 text-emerald-300 border-emerald-700/60",
          tooltip: "Quotation and code-point offsets strictly match stored source text.",
        };
      case "stale":
        return {
          icon: <RefreshCw className="w-3.5 h-3.5 text-amber-400" />,
          label: "Source Changed (Stale)",
          classes: "bg-amber-950/80 text-amber-300 border-amber-700/60",
          tooltip: "Source text fingerprint changed since evidence was generated.",
        };
      case "mismatched":
        return {
          icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
          label: "Quotation Mismatch",
          classes: "bg-rose-950/80 text-rose-300 border-rose-700/60",
          tooltip: "Quotation was not found in the stored source text.",
        };
      case "missing_source":
        return {
          icon: <AlertTriangle className="w-3.5 h-3.5 text-slate-400" />,
          label: "Source Missing",
          classes: "bg-slate-900 text-slate-300 border-slate-700",
          tooltip: "Source text is unavailable or empty in record revision.",
        };
      case "insufficient_evidence":
        return {
          icon: <HelpCircle className="w-3.5 h-3.5 text-blue-400" />,
          label: "Insufficient Evidence",
          classes: "bg-blue-950/80 text-blue-300 border-blue-700/60",
          tooltip: "Passage is absent or insufficient to establish this characteristic (e.g. no comparator).",
        };
      case "needs_review":
      default:
        return {
          icon: <AlertCircle className="w-3.5 h-3.5 text-amber-400" />,
          label: "Requires Review",
          classes: "bg-amber-950/80 text-amber-300 border-amber-700/60",
          tooltip: "Quotation is ambiguous or requires human verification.",
        };
    }
  };

  const getSemanticBadge = (assessment: EvidenceSemanticAssessment) => {
    switch (assessment) {
      case "supports":
        return {
          label: "Supports Claim",
          classes: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30",
        };
      case "contradicts":
        return {
          label: "Contradictory Evidence",
          classes: "bg-rose-500/10 text-rose-400 border border-rose-500/30",
        };
      case "insufficient":
        return {
          label: "Insufficient Info",
          classes: "bg-slate-500/10 text-slate-400 border border-slate-500/30",
        };
      case "unassessed":
      default:
        return {
          label: "Support Unassessed",
          classes: "bg-slate-800 text-slate-400 border border-slate-700",
        };
    }
  };

  // Filter items
  const items = bundle?.items || [];
  const filteredItems = items.filter((item) => {
    if (filter === "pico") {
      return ["population", "intervention", "comparator", "outcome"].includes(item.claim_type);
    }
    if (filter === "screening_rationale") {
      return item.claim_type === "screening_rationale";
    }
    if (filter === "needs_review") {
      return ["needs_review", "stale", "mismatched"].includes(item.validation_status);
    }
    return true;
  });

  const summary = bundle?.summary;

  return (
    <div className="space-y-4">
      {/* HEADER & TRANSPARENCY NOTICE */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-900/40 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              <ShieldCheck className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide">Evidence Passport</h3>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 font-mono">
                  ISO-Audit Trail
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Auditable evidence trail linking claims, exact quotations, offset validation, and human overrides.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRevalidate}
              disabled={revalidating}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition disabled:opacity-50"
              title="Deterministically revalidate quotations against current stored text"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${revalidating ? "animate-spin text-cyan-400" : ""}`} />
              <span>{revalidating ? "Validating..." : "Revalidate All"}</span>
            </button>

            <a
              href={api.evidence.exportUrl(workspaceId)}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition"
              title="Export workspace Evidence Passports with CSV formula injection protection"
            >
              <Download className="w-3.5 h-3.5 text-cyan-400" />
              <span>Export CSV</span>
            </a>
          </div>
        </div>

        {/* METRICS SUMMARY BAR */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2 border-t border-slate-800/80 text-xs font-mono">
            <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-slate-400 text-[11px]">Verified Quotes</div>
              <div className="text-base font-bold text-emerald-400 flex items-center gap-1">
                <span>{summary.verified_quotes_count}</span>
                <span className="text-xs text-slate-500">/ {summary.total_claims}</span>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-slate-400 text-[11px]">Requires Review</div>
              <div className="text-base font-bold text-amber-400">
                {summary.needs_review_count + summary.stale_count + summary.mismatched_count}
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-slate-400 text-[11px]">PICO Evidence</div>
              <div className="text-base font-bold text-cyan-400 flex items-center gap-1">
                <span>{summary.pico_fields_with_evidence}</span>
                <span className="text-xs text-slate-500">/ 4 fields</span>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-slate-400 text-[11px]">Human Corrected</div>
              <div className="text-base font-bold text-purple-400">
                {summary.human_corrected_count}
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-slate-400 text-[11px]">Contradictory Evidence</div>
              <div className="text-base font-bold text-rose-400">
                {summary.contradictory_count}
              </div>
            </div>
          </div>
        )}

        {/* Core Principle Notice */}
        <div className="flex items-start gap-2 p-2.5 rounded-xl bg-indigo-950/30 border border-indigo-900/30 text-[11px] text-slate-300">
          <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <span>
            <strong>Transparency Principle:</strong> Exact quotation matching verifies structural passage existence in the source text.
            Semantic support reflects logical agreement and is never falsely marked as verified without explicit human or semantic assessment.
          </span>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {actionError && (
        <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* FILTER TABS */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
        <div className="flex items-center gap-1 text-xs">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1.5 rounded-lg transition font-mono ${
              filter === "all" ? "bg-slate-800 text-cyan-300 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            All Claims ({items.length})
          </button>
          <button
            onClick={() => setFilter("pico")}
            className={`px-3 py-1.5 rounded-lg transition font-mono ${
              filter === "pico" ? "bg-slate-800 text-cyan-300 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            PICO Elements
          </button>
          <button
            onClick={() => setFilter("screening_rationale")}
            className={`px-3 py-1.5 rounded-lg transition font-mono ${
              filter === "screening_rationale" ? "bg-slate-800 text-cyan-300 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            Screening Rationales
          </button>
          <button
            onClick={() => setFilter("needs_review")}
            className={`px-3 py-1.5 rounded-lg transition font-mono ${
              filter === "needs_review" ? "bg-slate-800 text-amber-300 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            Requires Review
          </button>
        </div>

        <div className="text-[11px] font-mono text-slate-500">
          Source SHA: {bundle?.source_fingerprint ? `${bundle.source_fingerprint.slice(0, 12)}...` : "None"}
        </div>
      </div>

      {/* TWO-COLUMN LAYOUT: CLAIM CARDS & INTERACTIVE SOURCE TEXT */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT COLUMN: CLAIM CARDS */}
        <div className="lg:col-span-7 space-y-3">
          {filteredItems.length === 0 ? (
            <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-2">
              <FileText className="w-8 h-8 text-slate-500 mx-auto" />
              <div className="text-sm font-semibold text-slate-300">No evidence claims match this filter</div>
              <p className="text-xs text-slate-500">
                Evidence claims are generated during screening and PICO extraction. Click Revalidate to sync.
              </p>
            </div>
          ) : (
            filteredItems.map((item) => {
              const valBadge = getValidationBadge(item.validation_status);
              const semBadge = getSemanticBadge(item.semantic_assessment);
              const isSelected = selectedItem?.id === item.id;

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedItem(item)}
                  className={`p-4 rounded-2xl border transition cursor-pointer space-y-3 ${
                    isSelected
                      ? "bg-slate-900 border-cyan-500/70 shadow-lg shadow-cyan-950/30"
                      : "bg-slate-900/70 hover:bg-slate-900 border-slate-800"
                  }`}
                >
                  {/* Top Header: Claim Type + Validation Badge + Semantic Badge */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-bold font-mono px-2 py-0.5 rounded-md bg-slate-800 text-cyan-300 border border-slate-700 uppercase">
                        {item.claim_type.replace("_", " ")}
                      </span>

                      {item.provenance === "human_corrected" ? (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/80 flex items-center gap-1">
                          <UserCheck className="w-3 h-3" />
                          <span>Human Corrected</span>
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                          {item.provenance}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full border flex items-center gap-1 ${valBadge.classes}`}
                        title={valBadge.tooltip}
                      >
                        {valBadge.icon}
                        <span>{valBadge.label}</span>
                      </span>

                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${semBadge.classes}`}>
                        {semBadge.label}
                      </span>
                    </div>
                  </div>

                  {/* Claim Text */}
                  <div>
                    <div className="text-xs font-semibold text-slate-200">
                      {item.claim_value}
                    </div>
                    {item.original_claim_value && item.original_claim_value !== item.claim_value && (
                      <div className="text-[11px] text-slate-400 line-through mt-0.5">
                        Original AI claim: {item.original_claim_value}
                      </div>
                    )}
                  </div>

                  {/* Supporting Quotation Box */}
                  {item.supporting_quote ? (
                    <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs font-mono space-y-1">
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Supporting Quotation (source: {item.source_field}):</span>
                        {item.start_cp !== null && item.end_cp !== null && (
                          <span className="text-cyan-400">
                            offsets [{item.start_cp}:{item.end_cp})
                          </span>
                        )}
                      </div>
                      <blockquote className="text-cyan-100 italic border-l-2 border-cyan-500/60 pl-2">
                        "{item.supporting_quote}"
                      </blockquote>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-[11px] text-slate-400 italic">
                      No exact supporting passage quoted in abstract.
                    </div>
                  )}

                  {/* Validation message / reviewer rationale */}
                  {item.validation_message && (
                    <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>{item.validation_message}</span>
                    </div>
                  )}

                  {item.reviewer_correction_reason && (
                    <div className="text-[11px] text-purple-300 bg-purple-950/30 p-2 rounded-lg border border-purple-900/40">
                      <strong>Reviewer Note:</strong> {item.reviewer_correction_reason}
                    </div>
                  )}

                  {/* Action Bar */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
                    <span className="text-[10px] text-slate-500 font-mono">
                      Updated: {new Date(item.updated_at).toLocaleTimeString()}
                    </span>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openCorrectionModal(item);
                      }}
                      className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 flex items-center gap-1 transition"
                    >
                      <Edit3 className="w-3 h-3 text-cyan-400" />
                      <span>Correct Claim</span>
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* RIGHT COLUMN: INTERACTIVE SOURCE TEXT HIGHLIGHTER */}
        <div className="lg:col-span-5 space-y-3">
          <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3 sticky top-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                <FileText className="w-4 h-4 text-cyan-400" />
                <span>Source Text Inspection</span>
              </div>
              {selectedItem && (
                <span className="text-[10px] font-mono text-cyan-300 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/80">
                  {selectedItem.claim_type}
                </span>
              )}
            </div>

            {bundle?.abstract_text ? (
              <div
                ref={abstractRef}
                className="max-h-[500px] overflow-y-auto text-xs text-slate-300 leading-relaxed font-sans p-3 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2 select-text"
              >
                {selectedItem && selectedItem.supporting_quote && selectedItem.start_cp !== null && selectedItem.end_cp !== null ? (
                  <div>
                    <span>{bundle.abstract_text.slice(0, selectedItem.start_cp)}</span>
                    <mark className="bg-cyan-500/30 text-cyan-100 font-semibold px-1 py-0.5 rounded border border-cyan-400/60 shadow-sm">
                      {bundle.abstract_text.slice(selectedItem.start_cp, selectedItem.end_cp)}
                    </mark>
                    <span>{bundle.abstract_text.slice(selectedItem.end_cp)}</span>
                  </div>
                ) : (
                  <div>{bundle.abstract_text}</div>
                )}
              </div>
            ) : (
              <div className="p-6 rounded-xl bg-slate-950 text-center text-xs text-slate-500 italic">
                No stored abstract text available for this study.
              </div>
            )}

            {/* Selected Claim Inspector */}
            {selectedItem && (
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] font-mono space-y-1.5">
                <div className="text-slate-400 font-bold uppercase tracking-wide">
                  Active Claim Details:
                </div>
                <div className="text-slate-200">
                  <span className="text-slate-400">Claim: </span>
                  {selectedItem.claim_value}
                </div>
                <div className="text-slate-200">
                  <span className="text-slate-400">Offsets: </span>
                  {selectedItem.start_cp !== null && selectedItem.end_cp !== null
                    ? `[${selectedItem.start_cp} : ${selectedItem.end_cp}) code points`
                    : "No offsets available"}
                </div>
                <div className="text-slate-200">
                  <span className="text-slate-400">Validation: </span>
                  <span className="text-cyan-300">{selectedItem.validation_status}</span>
                </div>
                <div className="text-slate-200">
                  <span className="text-slate-400">Semantic: </span>
                  <span className="text-indigo-300">{selectedItem.semantic_assessment}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* REVIEWER CORRECTION MODAL */}
      {correctingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-cyan-400" />
                <h4 className="text-sm font-bold text-white">Reviewer Evidence Correction</h4>
              </div>
              <button
                onClick={() => setCorrectingItem(null)}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Claim / Clinical Value:
                </label>
                <input
                  type="text"
                  value={editClaimValue}
                  onChange={(e) => setEditClaimValue(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-cyan-500 font-sans"
                  placeholder="e.g. Adults with type 2 diabetes"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Supporting Quotation from Source:
                </label>
                <textarea
                  value={editQuote}
                  onChange={(e) => setEditQuote(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-cyan-500 font-mono"
                  placeholder="Paste exact sentence or passage from abstract..."
                />
                <span className="text-[11px] text-slate-500">
                  Backend will deterministically re-verify offsets against stored text.
                </span>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Semantic Support Assessment:
                </label>
                <select
                  value={editSemantic}
                  onChange={(e) => setEditSemantic(e.target.value as EvidenceSemanticAssessment)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-cyan-500 font-sans"
                >
                  <option value="supports">Passage supports the claim</option>
                  <option value="contradicts">Passage contradicts the claim (contradictory evidence)</option>
                  <option value="insufficient">Passage provides insufficient information</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Correction Rationale (Mandatory for Audit Trail):
                </label>
                <textarea
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-cyan-500 font-sans"
                  placeholder="Why was this claim or quotation adjusted? (Saved to immutable audit ledger)"
                />
              </div>
            </div>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={() => setCorrectingItem(null)}
                className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveCorrection}
                disabled={submittingCorrection}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-900/40 transition disabled:opacity-50 flex items-center gap-1.5"
              >
                {submittingCorrection ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Verifying & Saving...</span>
                  </>
                ) : (
                  <span>Save Correction</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
