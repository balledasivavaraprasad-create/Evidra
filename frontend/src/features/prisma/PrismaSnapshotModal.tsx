import React, { useState } from "react";
import { X, Camera, Save, AlertCircle } from "lucide-react";
import { api, PrismaReportResponse } from "../../api/client";

interface PrismaSnapshotModalProps {
  workspaceId: string;
  corpusRevisionId?: string;
  queryVersionId?: string;
  onClose: () => void;
  onSnapshotCreated: (snapshot: PrismaReportResponse) => void;
}

export const PrismaSnapshotModal: React.FC<PrismaSnapshotModalProps> = ({
  workspaceId,
  corpusRevisionId,
  queryVersionId,
  onClose,
  onSnapshotCreated,
}) => {
  const [name, setName] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [actorId, setActorId] = useState<string>("reviewer");
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const res = await api.prisma.createSnapshot(
        workspaceId,
        {
          name: name.trim() || undefined,
          notes: notes.trim() || undefined,
          actor_id: actorId.trim() || "reviewer",
        },
        {
          corpus_revision_id: corpusRevisionId,
          query_version_id: queryVersionId,
        }
      );
      onSnapshotCreated(res);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to save PRISMA snapshot.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-750 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2">
            <Camera className="w-5 h-5 text-amber-400" />
            <h2 className="text-base font-bold text-slate-100">
              Save PRISMA Report Snapshot
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-xs text-slate-400">
            Snapshots capture the exact state of your PRISMA 2020 flow counts, database sources, and exclusion reasons at a specific point in time (e.g. for manuscript submission or protocol auditing).
          </p>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Snapshot Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Manuscript Submission v1.0"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Audit Notes
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add optional contextual details, search date cutoff, or milestone notes..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Reviewer / Actor ID
            </label>
            <input
              type="text"
              value={actorId}
              onChange={(e) => setActorId(e.target.value)}
              placeholder="reviewer"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-slate-800 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? "Saving Snapshot..." : "Save Snapshot"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
