import React, { useState, useEffect } from "react";
import { X, History, Clock, User, AlertTriangle, Eye, CheckCircle2 } from "lucide-react";
import {
  api,
  PrismaSnapshotSummaryItem,
  PrismaReportResponse,
} from "../../api/client";

interface PrismaHistoryDrawerProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
  onSelectSnapshot: (snapshot: PrismaReportResponse) => void;
  activeSnapshotId?: string | null;
}

export const PrismaHistoryDrawer: React.FC<PrismaHistoryDrawerProps> = ({
  workspaceId,
  isOpen,
  onClose,
  onSelectSnapshot,
  activeSnapshotId,
}) => {
  const [snapshots, setSnapshots] = useState<PrismaSnapshotSummaryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchingId, setFetchingId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadSnapshots();
    }
  }, [isOpen, workspaceId]);

  const loadSnapshots = async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await api.prisma.listSnapshots(workspaceId);
      setSnapshots(items);
    } catch (err: any) {
      setError(err?.message || "Failed to load snapshot history.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (snapshotId: string) => {
    setFetchingId(snapshotId);
    try {
      const snap = await api.prisma.getSnapshot(workspaceId, snapshotId);
      onSelectSnapshot(snap);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to load snapshot details.");
    } finally {
      setFetchingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-md bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl">
        {/* Drawer Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-amber-400" />
            <h2 className="text-base font-bold text-slate-100">
              PRISMA Snapshots
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Snapshots List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <div className="py-12 text-center text-slate-400 text-xs">
              Loading saved snapshots...
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {error}
            </div>
          )}

          {!loading && !error && snapshots.length === 0 && (
            <div className="py-12 text-center text-slate-400 text-xs space-y-2">
              <Clock className="w-8 h-8 mx-auto text-slate-600" />
              <p>No snapshots saved yet.</p>
              <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                Click &quot;Save Snapshot&quot; on the main PRISMA page to preserve your review flow state for publication or audit.
              </p>
            </div>
          )}

          {!loading &&
            !error &&
            snapshots.map((snap) => {
              const isSelected = activeSnapshotId === snap.snapshot_id;
              return (
                <div
                  key={snap.snapshot_id}
                  className={`p-4 rounded-xl border transition ${
                    isSelected
                      ? "bg-amber-500/10 border-amber-500/50"
                      : "bg-slate-800/50 border-slate-750 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-xs font-bold text-slate-200">
                      {snap.name}
                    </h3>
                    {isSelected && (
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-semibold border border-amber-500/30">
                        Active View
                      </span>
                    )}
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                    <div>
                      <span className="text-slate-500">Identified:</span>{" "}
                      <strong className="text-slate-300">{snap.total_identified}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500">Duplicates:</span>{" "}
                      <strong className="text-slate-300">{snap.duplicates_removed}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500">Screened:</span>{" "}
                      <strong className="text-slate-300">{snap.records_screened}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500">Included:</span>{" "}
                      <strong className="text-emerald-400">{snap.studies_included}</strong>
                    </div>
                  </div>

                  <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                    <div className="flex items-center gap-1 text-slate-500">
                      <User className="w-3 h-3" />
                      <span>{snap.created_by}</span>
                    </div>
                    <div>
                      {new Date(snap.created_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </div>
                  </div>

                  {snap.has_warnings && (
                    <div className="mt-2 text-[10px] text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 shrink-0" />
                      <span>Has screening warnings / pending items</span>
                    </div>
                  )}

                  <div className="mt-3">
                    <button
                      onClick={() => handleSelect(snap.snapshot_id)}
                      disabled={fetchingId === snap.snapshot_id}
                      className="w-full py-1.5 px-3 rounded-lg bg-slate-750 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center justify-center gap-1.5 transition"
                    >
                      <Eye className="w-3.5 h-3.5 text-cyan-400" />
                      {fetchingId === snap.snapshot_id ? "Loading..." : "View Snapshot"}
                    </button>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
};
