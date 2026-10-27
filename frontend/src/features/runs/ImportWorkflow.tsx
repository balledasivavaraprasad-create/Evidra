import React, { useState, useEffect, useRef } from "react";
import { Download, CheckCircle2, AlertTriangle, XCircle, RotateCcw, Clock, Ban } from "lucide-react";
import { api, type JobResponse } from "../../api/client";

interface ImportWorkflowProps {
  workspaceId: string;
  selectedExecutionIds: string[];
  onImportComplete?: (job: JobResponse) => void;
}

export const ImportWorkflow: React.FC<ImportWorkflowProps> = ({
  workspaceId,
  selectedExecutionIds,
  onImportComplete,
}) => {
  const [cap, setCap] = useState<number>(200);
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() => crypto.randomUUID());
  const [activeJob, setActiveJob] = useState<JobResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollTimerRef = useRef<number | null>(null);
  const backoffDelayRef = useRef<number>(1000);

  // Restore active job from sessionStorage if available
  useEffect(() => {
    const savedJobId = sessionStorage.getItem(`active_import_job_${workspaceId}`);
    if (savedJobId && !activeJob) {
      api.jobs
        .get(savedJobId)
        .then((job) => {
          setActiveJob(job);
        })
        .catch(() => {
          sessionStorage.removeItem(`active_import_job_${workspaceId}`);
        });
    }
  }, [workspaceId]);

  // Polling loop with backoff
  useEffect(() => {
    if (!activeJob) return;

    const isTerminal = ["succeeded", "partial", "failed", "cancelled"].includes(activeJob.state);
    if (isTerminal) {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      sessionStorage.removeItem(`active_import_job_${workspaceId}`);
      if (onImportComplete && activeJob.state === "succeeded") {
        onImportComplete(activeJob);
      }
      return;
    }

    const pollJob = async () => {
      try {
        const updated = await api.jobs.get(activeJob.id);
        setActiveJob(updated);
        // Gradually backoff up to 5s
        backoffDelayRef.current = Math.min(backoffDelayRef.current * 1.5, 5000);
      } catch (err: unknown) {
        console.error("Error polling job status:", err);
      }

      pollTimerRef.current = window.setTimeout(pollJob, backoffDelayRef.current);
    };

    pollTimerRef.current = window.setTimeout(pollJob, backoffDelayRef.current);

    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [activeJob?.id, activeJob?.state]);

  const handleStartImport = async () => {
    if (selectedExecutionIds.length === 0) {
      setError("Please select at least one search execution to import.");
      return;
    }

    setSubmitting(true);
    setError(null);
    backoffDelayRef.current = 1000;

    try {
      const job = await api.imports.trigger(workspaceId, {
        search_execution_ids: selectedExecutionIds,
        cap: cap > 0 ? cap : 200,
        idempotency_key: idempotencyKey,
      });

      setActiveJob(job);
      sessionStorage.setItem(`active_import_job_${workspaceId}`, job.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to queue import job";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelJob = async () => {
    if (!activeJob) return;
    setCancelling(true);
    try {
      const cancelled = await api.jobs.cancel(activeJob.id);
      setActiveJob(cancelled);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to cancel job";
      setError(msg);
    } finally {
      setCancelling(false);
    }
  };

  const resetForm = () => {
    setActiveJob(null);
    setIdempotencyKey(crypto.randomUUID());
    setError(null);
    sessionStorage.removeItem(`active_import_job_${workspaceId}`);
  };

  return (
    <div className="card p-6 border border-slate-700/60 bg-slate-900/40 rounded-xl mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Download className="w-5 h-5 text-indigo-400" />
          <h2 className="text-lg font-semibold text-white">Approved Literature Ingestion</h2>
        </div>
        {activeJob && (
          <span className="text-xs px-2.5 py-1 bg-slate-800 border border-slate-700 rounded text-slate-300">
            Job ID: {activeJob.id.slice(0, 8)}
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-950/40 border border-red-800/60 rounded-lg text-sm text-red-300 flex items-center gap-2">
          <XCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!activeJob ? (
        <div>
          <p className="text-xs text-slate-400 mb-4">
            Imports are non-destructive and idempotent. Each batch fetches records, normalizes metadata, generates
            cryptographic content hashes, and stores immutable raw source copies.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-slate-950/50 border border-slate-800 rounded-lg mb-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Selected Search Executions
              </label>
              <div className="text-sm font-medium text-indigo-300">
                {selectedExecutionIds.length === 0 ? (
                  <span className="text-slate-500">None selected (select from searches above)</span>
                ) : (
                  <span>{selectedExecutionIds.length} execution(s) queued for fetch</span>
                )}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Import Record Cap (per source)
              </label>
              <input
                type="number"
                min={10}
                max={5000}
                value={cap}
                onChange={(e) => setCap(parseInt(e.target.value) || 200)}
                className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-[11px] text-slate-500 font-mono">
              Idempotency Key: {idempotencyKey.slice(0, 13)}...
            </span>
            <button
              type="button"
              disabled={submitting || selectedExecutionIds.length === 0}
              onClick={handleStartImport}
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-40"
            >
              <Download className="w-4 h-4" />
              <span>{submitting ? "Initiating Import Job..." : "Approve & Start Import"}</span>
            </button>
          </div>
        </div>
      ) : (
        /* Active / Completed Job Tracker */
        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {activeJob.state === "succeeded" && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
              {activeJob.state === "running" && <Clock className="w-5 h-5 text-indigo-400 animate-spin" />}
              {activeJob.state === "queued" && <Clock className="w-5 h-5 text-amber-400" />}
              {activeJob.state === "failed" && <XCircle className="w-5 h-5 text-red-400" />}
              {activeJob.state === "partial" && <AlertTriangle className="w-5 h-5 text-amber-400" />}
              {activeJob.state === "cancelled" && <Ban className="w-5 h-5 text-slate-400" />}

              <div>
                <span className="text-xs font-semibold uppercase text-white tracking-wider">
                  State: {activeJob.state}
                </span>
                {activeJob.stage && (
                  <span className="text-xs text-slate-400 ml-2">({activeJob.stage})</span>
                )}
              </div>
            </div>

            {["queued", "running"].includes(activeJob.state) && (
              <button
                type="button"
                disabled={cancelling}
                onClick={handleCancelJob}
                className="px-3 py-1 bg-red-950/60 hover:bg-red-900 border border-red-700/60 text-red-200 rounded text-xs transition"
              >
                {cancelling ? "Cancelling..." : "Cancel Job"}
              </button>
            )}

            {["succeeded", "partial", "failed", "cancelled"].includes(activeJob.state) && (
              <button
                type="button"
                onClick={resetForm}
                className="flex items-center gap-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs transition"
              >
                <RotateCcw className="w-3 h-3" />
                <span>New Import</span>
              </button>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-800 rounded-full h-2 mb-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                activeJob.state === "failed"
                  ? "bg-red-500"
                  : activeJob.state === "succeeded"
                  ? "bg-emerald-500"
                  : "bg-indigo-500"
              }`}
              style={{ width: `${Math.max(5, Math.min(100, activeJob.progress * 100))}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>
              Processed: {activeJob.processed_items ?? 0} of {activeJob.total_items ?? "?"} records
            </span>
            <span>{Math.round(activeJob.progress * 100)}%</span>
          </div>

          {activeJob.error && (
            <div className="mt-3 p-2.5 bg-red-950/50 border border-red-800/60 rounded text-xs text-red-300">
              <span className="font-semibold">{activeJob.error.code}: </span>
              <span>{activeJob.error.message}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
