import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle, HelpCircle, ShieldAlert, ArrowRight } from "lucide-react";
import { api, type ConflictResolveRequest, type EligibilityStatus } from "../../api/client";

interface ConflictResolutionModalProps {
  conflictId: string;
  groupId: string;
  paperTitle: string;
  expectedVersion: number;
  isOpen: boolean;
  onClose: () => void;
  onResolved: () => void;
}

export const ConflictResolutionModal: React.FC<ConflictResolutionModalProps> = ({
  conflictId,
  groupId,
  paperTitle,
  expectedVersion,
  isOpen,
  onClose,
  onResolved,
}) => {
  const [chosenStatus, setChosenStatus] = useState<EligibilityStatus>("include");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("A deliberate rationale is required to resolve a conflicting decision.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload: ConflictResolveRequest = {
        chosen_status: chosenStatus,
        reason: reason.trim(),
        expected_version: expectedVersion,
      };
      await api.conflicts.resolve(conflictId, payload);
      onResolved();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to resolve conflict";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-xl p-6 rounded-2xl border-amber-500/30 shadow-2xl space-y-6">
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Resolve Decision Conflict
              </h2>
              <p className="text-xs text-slate-400">
                Group <code className="text-cyan-400 font-mono">{groupId}</code>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5">
          <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
            Representative Paper
          </span>
          <p className="text-xs text-white font-medium line-clamp-2">
            {paperTitle}
          </p>
        </div>

        <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-amber-200">
              Competing Decisions Inherited From Merged/Split Papers
            </p>
            <p className="text-[11px] text-amber-300/80 leading-relaxed">
              Different source records merged into this paper group carry divergent reviewer decisions.
              Evidra prohibits automatic decision winners: choose the effective status and provide justification.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2">
              Select Definitive Eligibility Status
            </label>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setChosenStatus("include")}
                className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-semibold transition ${
                  chosenStatus === "include"
                    ? "bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                    : "bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>INCLUDE</span>
              </button>
              <button
                type="button"
                onClick={() => setChosenStatus("exclude")}
                className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-semibold transition ${
                  chosenStatus === "exclude"
                    ? "bg-red-500/20 border-red-500 text-red-300 shadow-[0_0_15px_rgba(239,68,68,0.2)]"
                    : "bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <XCircle className="w-4 h-4 text-red-400" />
                <span>EXCLUDE</span>
              </button>
              <button
                type="button"
                onClick={() => setChosenStatus("maybe")}
                className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-semibold transition ${
                  chosenStatus === "maybe"
                    ? "bg-amber-500/20 border-amber-500 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.2)]"
                    : "bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <HelpCircle className="w-4 h-4 text-amber-400" />
                <span>MAYBE</span>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Resolution Rationale <span className="text-red-400">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why this group's conflicting decisions are resolved with the chosen status..."
              rows={3}
              className="w-full px-3 py-2 text-xs rounded-xl bg-slate-900/80 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              required
            />
          </div>

          {error && (
            <div className="p-2.5 rounded-lg bg-red-950/50 border border-red-800/80 text-red-300 text-xs">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !reason.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition shadow-lg shadow-cyan-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Resolving..." : "Confirm Conflict Resolution"}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
