import React, { useState, useEffect } from "react";
import { X, Search, ExternalLink, Filter, CheckCircle2, XCircle, HelpCircle } from "lucide-react";
import {
  api,
  PrismaStage,
  PrismaStageRecordItem,
  PrismaStageRecordsResponse,
} from "../../api/client";

interface PrismaStageRecordsModalProps {
  workspaceId: string;
  stage: PrismaStage | null;
  stageLabel: string;
  onClose: () => void;
  corpusRevisionId?: string;
  queryVersionId?: string;
}

export const PrismaStageRecordsModal: React.FC<PrismaStageRecordsModalProps> = ({
  workspaceId,
  stage,
  stageLabel,
  onClose,
  corpusRevisionId,
  queryVersionId,
}) => {
  const [data, setData] = useState<PrismaStageRecordsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState<number>(0);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const limit = 20;

  useEffect(() => {
    if (!stage) return;
    fetchRecords(0);
  }, [stage, workspaceId, corpusRevisionId, queryVersionId]);

  const fetchRecords = async (currentOffset: number) => {
    if (!stage) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.prisma.getStageRecords(workspaceId, {
        stage,
        limit,
        offset: currentOffset,
        corpus_revision_id: corpusRevisionId,
        query_version_id: queryVersionId,
      });
      setData(res);
      setOffset(currentOffset);
    } catch (err: any) {
      setError(err?.message || "Failed to load stage records.");
    } finally {
      setLoading(false);
    }
  };

  if (!stage) return null;

  const filteredRecords = (data?.records || []).filter((r) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      r.title.toLowerCase().includes(term) ||
      (r.journal && r.journal.toLowerCase().includes(term)) ||
      (r.authors && r.authors.some((a) => a.toLowerCase().includes(term))) ||
      (r.doi && r.doi.toLowerCase().includes(term)) ||
      (r.pmid && r.pmid.toLowerCase().includes(term))
    );
  });

  const getDecisionBadge = (decision: string) => {
    switch (decision.toLowerCase()) {
      case "include":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
            <CheckCircle2 className="w-3 h-3" /> Included
          </span>
        );
      case "exclude":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/40">
            <XCircle className="w-3 h-3" /> Excluded
          </span>
        );
      case "maybe":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/40">
            <HelpCircle className="w-3 h-3" /> Maybe / Uncertain
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-slate-700 text-slate-300">
            Pending / Ineligible
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-750 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Filter className="w-5 h-5 text-amber-400" />
              {stageLabel}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {data ? data.total_count : "..."} records contributing to this PRISMA flow stage
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="px-6 py-3 border-b border-slate-800 bg-slate-900/40 flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter records by title, author, journal, DOI..."
              className="w-full bg-slate-800/80 border border-slate-700 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-amber-500"
            />
          </div>
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="text-xs text-slate-400 hover:text-slate-200 underline"
            >
              Clear
            </button>
          )}
        </div>

        {/* Record List */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {loading && (
            <div className="py-16 text-center text-slate-400 text-sm">
              Loading stage records...
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
              {error}
            </div>
          )}

          {!loading && !error && filteredRecords.length === 0 && (
            <div className="py-16 text-center text-slate-400 text-sm">
              No matching records found for this stage.
            </div>
          )}

          {!loading &&
            !error &&
            filteredRecords.map((r, i) => (
              <div
                key={r.source_record_id || r.group_id || i}
                className="p-4 rounded-xl bg-slate-800/50 border border-slate-750/70 hover:border-slate-700 transition"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <h3 className="text-sm font-semibold text-slate-200 leading-snug">
                      {r.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      {r.authors && r.authors.length > 0 && (
                        <span>{r.authors.slice(0, 3).join(", ")}{r.authors.length > 3 ? " et al." : ""}</span>
                      )}
                      {r.year && <span>• {r.year}</span>}
                      {r.journal && <span>• <em className="text-slate-300">{r.journal}</em></span>}
                      {r.source_namespace && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-300 uppercase text-[10px] font-mono">
                          {r.source_namespace}
                        </span>
                      )}
                      {r.is_duplicate && (
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-semibold border border-amber-500/30">
                          Duplicate Entry
                        </span>
                      )}
                    </div>
                    {r.decision_reason && (
                      <div className="text-xs text-rose-300/90 bg-rose-950/30 border border-rose-900/40 rounded px-2.5 py-1 mt-1 inline-block">
                        <strong>Exclusion Reason:</strong> {r.decision_reason}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {getDecisionBadge(r.decision)}
                    <div className="flex items-center gap-2">
                      {r.doi && (
                        <a
                          href={`https://doi.org/${encodeURIComponent(r.doi)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-cyan-400 hover:underline flex items-center gap-0.5"
                        >
                          DOI <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                      {r.pmid && (
                        <a
                          href={`https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(r.pmid)}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-cyan-400 hover:underline flex items-center gap-0.5"
                        >
                          PMID <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
        </div>

        {/* Footer with Pagination */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            {data && data.total_count > 0 ? (
              <>
                Showing {offset + 1}–{Math.min(offset + limit, data.total_count)} of{" "}
                {data.total_count} records
              </>
            ) : (
              "0 records"
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchRecords(Math.max(0, offset - limit))}
              disabled={offset === 0 || loading}
              className="px-3 py-1 rounded bg-slate-800 text-xs text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Previous
            </button>
            <button
              onClick={() => fetchRecords(offset + limit)}
              disabled={!data || offset + limit >= data.total_count || loading}
              className="px-3 py-1 rounded bg-slate-800 text-xs text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
