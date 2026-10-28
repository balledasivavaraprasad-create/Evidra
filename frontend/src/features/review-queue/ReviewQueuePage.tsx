import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  BookOpen,
  CheckCircle,
  XCircle,
  HelpCircle,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Download,
  History,
  Layers,
  FileSpreadsheet,
  AlertCircle,
  RefreshCw,
  X,
  ExternalLink,
} from "lucide-react";
import { api, type PaperGroupSummary, type PaperGroupDetail, type PicoSpan, ApiError } from "../../api/client";
import { MOCK_GROUPS } from "../../api/fixtures";
import { PicoViewer } from "../pico/PicoViewer";
import { AssistantPanel } from "./AssistantPanel";
import { EvidencePassportPanel } from "../evidence-passport/EvidencePassportPanel";
import { ArticleRadarWidget } from "../pico-radar/ArticleRadarWidget";
import type { ArticleRadarResponse } from "../../api/client";
import { ShieldCheck } from "lucide-react";

const EXCLUSION_REASONS = [
  "Preclinical animal model without human participants",
  "In vitro or computational simulation only",
  "Case report, editorial, or narrative review",
  "Wrong target population (e.g. non-diabetic or pediatric)",
  "No relevant clinical comparator",
  "Non-English publication without translation",
  "Study protocol without outcome data",
];

export const ReviewQueuePage: React.FC = () => {
  const { id: workspaceParam } = useParams<{ id: string }>();
  const workspaceId = workspaceParam || "ws-synth-001";

  const [revisionId, setRevisionId] = useState<string | null>(null);
  const [groups, setGroups] = useState<PaperGroupSummary[]>(MOCK_GROUPS);
  const [selectedGroupId, setSelectedGroupId] = useState<string>(MOCK_GROUPS[0].id);
  const [groupDetail, setGroupDetail] = useState<PaperGroupDetail | null>(null);
  const [filter, setFilter] = useState<"all" | "include" | "exclude" | "maybe" | "conflict">("all");
  const [loading, setLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Exclusion Modal State
  const [excludeModalOpen, setExcludeModalOpen] = useState(false);
  const [selectedReason, setSelectedReason] = useState<string>(EXCLUSION_REASONS[0]);
  const [customReason, setCustomReason] = useState<string>("");

  // 409 Stale Concurrency State
  const [concurrencyConflict, setConcurrencyConflict] = useState<boolean>(false);

  const [groupVersions, setGroupVersions] = useState<Record<string, number>>({});
  const getVersion = (id: string) => groupVersions[id] || 1;

  // Active Tab: Reader vs Audit Timeline vs Member Copies vs AI Assistant
  const [activeTab, setActiveTab] = useState<"reader" | "radar" | "passport" | "audit" | "members" | "assistant">("reader");
  const [articleRadar, setArticleRadar] = useState<ArticleRadarResponse | null>(null);

  // Load Revisions & Groups
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        setLoading(true);
        const revList = await api.revisions.list(workspaceId);
        if (!isMounted) return;
        if (revList && revList.length > 0) {
          const latestRev = revList[0];
          setRevisionId(latestRev.id);
          const groupList = await api.revisions.listGroups(latestRev.id);
          if (groupList && groupList.length > 0) {
            setGroups(groupList);
            setSelectedGroupId(groupList[0].id);
          }
        }
      } catch {
        // Fall back gracefully to mock groups if backend not yet seeded
        if (isMounted) {
          setGroups(MOCK_GROUPS);
          setSelectedGroupId(MOCK_GROUPS[0].id);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, [workspaceId]);

  // Load Selected Group Detail
  useEffect(() => {
    let isMounted = true;
    async function fetchDetail() {
      if (!selectedGroupId) return;
      try {
        const detail = await api.groups.getDetail(selectedGroupId, revisionId || undefined);
        if (isMounted) {
          setGroupDetail(detail);
          setConcurrencyConflict(false);
        }
      } catch {
        // Fallback detail using mock group
        const found = groups.find((g) => g.id === selectedGroupId) || MOCK_GROUPS[0];
        if (isMounted) {
          setGroupDetail({
            group: found,
            members: [found.representative_revision],
            screen_result: null,
            events: [],
            conflicts: [],
          });
        }
      }
    }
    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedGroupId, revisionId, groups]);

  const selectedGroup = groups.find((g) => g.id === selectedGroupId) || groups[0];

  const filteredGroups = groups.filter((g) => {
    if (filter === "all") return true;
    if (filter === "conflict") return g.has_conflict;
    return g.effective_status === filter;
  });

  const handleDecision = async (status: "include" | "exclude" | "maybe", reasonText?: string) => {
    if (!selectedGroup) return;
    setErrorBanner(null);
    setConcurrencyConflict(false);
    try {
      const currentVersion = getVersion(selectedGroup.id);
      await api.groups.recordDecision(selectedGroup.id, {
        status: status as any,
        reason: reasonText || (status === "include" ? "Meets clinical criteria" : "Uncertain eligibility"),
        expected_version: currentVersion,
      });

      setStatusMessage(`Decision '${status.toUpperCase()}' successfully saved for group ${selectedGroup.id}.`);
      setGroupVersions((prev) => ({ ...prev, [selectedGroup.id]: currentVersion + 1 }));

      // Update local group effective status
      setGroups((prev) =>
        prev.map((g) =>
          g.id === selectedGroup.id
            ? { ...g, effective_status: status as any, has_human_decision: true }
            : g
        )
      );
      // Refresh detail
      const updatedDetail = await api.groups.getDetail(selectedGroup.id, revisionId || undefined);
      setGroupDetail(updatedDetail);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setConcurrencyConflict(true);
        setErrorBanner("Stale version conflict (409): Another reviewer has updated this group. Please reload to inspect.");
      } else {
        const msg = err instanceof Error ? err.message : "Failed to record screening decision";
        setErrorBanner(msg);
      }
    }
  };

  const handleConfirmExclusion = async () => {
    const finalReason = selectedReason === "Custom reason..." ? customReason.trim() : selectedReason;
    if (!finalReason) {
      setErrorBanner("A mandatory exclusion reason must be provided.");
      return;
    }
    setExcludeModalOpen(false);
    await handleDecision("exclude", finalReason);
  };

  const handleSavePico = async (spans: PicoSpan[]) => {
    if (!selectedGroup) return;
    const rep = selectedGroup.representative_revision;
    const currentVersion = getVersion(selectedGroup.id);
    await api.groups.savePico(selectedGroup.id, {
      record_revision_id: rep.id,
      content_hash: rep.content_hash,
      expected_version: currentVersion,
      spans,
    });
    setStatusMessage("PICO annotations saved with verified Unicode code-point spans.");
    setGroupVersions((prev) => ({ ...prev, [selectedGroup.id]: currentVersion + 1 }));
  };

  const handleExportCsv = async () => {
    if (!revisionId) {
      setErrorBanner("No active corpus revision available to export. Run Process Corpus first.");
      return;
    }
    try {
      setStatusMessage("Generating sanitized CSV export of confirmed included studies...");
      const res = await api.exports.create(revisionId, { format: "csv", revision_id: revisionId });
      const downloadUrl = api.exports.downloadUrl(res.id);
      window.open(downloadUrl, "_blank");
      setStatusMessage(`CSV Export complete! ${res.record_count} included studies exported (SHA-256: ${res.sha256_checksum.slice(0, 12)}...)`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate CSV export";
      setErrorBanner(msg);
    }
  };

  const handleProcessCorpus = async () => {
    try {
      setLoading(true);
      setStatusMessage("Executing deterministic deduplication, screening rules, and PICO pipeline...");
      const rev = await api.revisions.processCorpus(workspaceId);
      setRevisionId(rev.id);
      const groupList = await api.revisions.listGroups(rev.id);
      setGroups(groupList);
      if (groupList.length > 0) setSelectedGroupId(groupList[0].id);
      setStatusMessage(`Corpus processed successfully! Generated revision ${rev.id} with ${rev.group_count} paper groups.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to process corpus";
      setErrorBanner(msg);
    } finally {
      setLoading(false);
    }
  };

  const rep = selectedGroup?.representative_revision;

  return (
    <div className="space-y-6 pb-16">
      {/* Top Header & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-cyan-400" />
            <span>Screening Review Workbench</span>
            {revisionId && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Rev: {revisionId.slice(0, 10)}
              </span>
            )}
          </h1>
          <p className="text-slate-400 text-xs">
            Review literature abstracts, annotate PICO entities, verify machine suggestions, and export audit-ready evidence.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={handleProcessCorpus}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Process Corpus</span>
          </button>

          <Link
            to={`/reviews/${workspaceId}/radar`}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white rounded-lg text-xs font-medium transition border border-slate-700"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>PICO Radar Dashboard</span>
          </Link>
          <button
            type="button"
            onClick={handleExportCsv}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shadow-md transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          {/* Filter Pills */}
          <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs font-medium">
            {(["all", "include", "exclude", "maybe", "conflict"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded-md capitalize transition ${
                  filter === f
                    ? "bg-slate-800 text-cyan-300 font-semibold shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications / Alerts */}
      {statusMessage && (
        <div className="p-3 rounded-lg bg-cyan-950/60 border border-cyan-800/80 text-cyan-300 text-xs font-mono flex items-center justify-between animate-fadeIn">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="text-cyan-400 hover:text-white">✕</button>
        </div>
      )}

      {errorBanner && (
        <div className="p-3.5 rounded-lg bg-red-950/80 border border-red-800 text-red-200 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorBanner}</span>
          </span>
          <button onClick={() => setErrorBanner(null)} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* 409 Concurrency Banner */}
      {concurrencyConflict && (
        <div className="p-4 rounded-xl bg-amber-950/90 border border-amber-600 text-amber-200 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <div>
              <div className="font-bold text-white">Stale Concurrency Conflict (409)</div>
              <div>This group has been modified by another reviewer. Your draft is preserved.</div>
            </div>
          </div>
          <button
            type="button"
            onClick={async () => {
              if (selectedGroup) {
                const detail = await api.groups.getDetail(selectedGroup.id, revisionId || undefined);
                setGroupDetail(detail);
                setConcurrencyConflict(false);
              }
            }}
            className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs"
          >
            Reload Group
          </button>
        </div>
      )}

      {/* 3-Panel Review Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[560px]">
        {/* Left Column: Paper Group List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-mono text-slate-400 px-1 flex items-center justify-between">
            <span>Showing {filteredGroups.length} of {groups.length} groups</span>
            {selectedGroup && (
              <span className="text-[11px] text-slate-500">v{getVersion(selectedGroup.id)}</span>
            )}
          </div>

          <div className="space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
            {filteredGroups.map((group) => {
              const isSelected = selectedGroupId === group.id;
              const gRep = group.representative_revision;
              return (
                <div
                  key={group.id}
                  onClick={() => setSelectedGroupId(group.id)}
                  className={`p-3.5 rounded-xl border text-left cursor-pointer transition ${
                    isSelected
                      ? "bg-slate-800/90 border-cyan-500 shadow-md shadow-cyan-500/10"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      {gRep.source.toUpperCase()} • {gRep.external_id}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {group.member_count > 1 && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {group.member_count} copies
                        </span>
                      )}
                      <span
                        className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                          group.effective_status === "include"
                            ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                            : group.effective_status === "exclude"
                            ? "bg-red-950/80 text-red-300 border border-red-800"
                            : group.effective_status === "conflict"
                            ? "bg-amber-950/80 text-amber-300 border border-amber-800"
                            : "bg-slate-800 text-slate-300 border border-slate-700"
                        }`}
                      >
                        {group.effective_status}
                      </span>
                    </div>
                  </div>
                  <h4 className="text-xs font-semibold text-white line-clamp-2 leading-snug">
                    {gRep.title}
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                    {(gRep.authors || []).join(", ")} ({gRep.year || "n.d."})
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Center / Right Column: Detailed Abstract Reader & PICO Spans */}
        <div className="lg:col-span-8 space-y-4">
          <div className="glass-panel p-6 space-y-5 border-slate-800">
            {/* Header info */}
            <div className="space-y-2 border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2 flex-wrap justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                    GROUP: {selectedGroup.id} ({selectedGroup.member_count} record{selectedGroup.member_count > 1 ? "s" : ""})
                  </span>
                  {selectedGroup.has_conflict && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1 font-bold">
                      <AlertTriangle className="w-3 h-3" /> MERGE CONFLICT DETECTED
                    </span>
                  )}
                  {rep?.doi && (
                    <span className="text-[10px] font-mono text-slate-400">
                      DOI: {rep.doi}
                    </span>
                  )}
                </div>

                {/* Sub-Tabs: Reader vs Audit Timeline vs Member Copies */}
                <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs font-mono">
                  <button
                    type="button"
                    onClick={() => setActiveTab("reader")}
                    className={`px-2.5 py-1 rounded transition ${activeTab === "reader" ? "bg-slate-800 text-cyan-300 font-bold" : "text-slate-400"}`}
                  >
                    Abstract & PICO
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveTab("radar");
                      if (selectedGroupId) {
                        api.radar.getArticleRadar(workspaceId, selectedGroupId).then(setArticleRadar);
                      }
                    }}
                    className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${
                      activeTab === "radar"
                        ? "bg-slate-800 text-cyan-300 font-bold"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Sparkles className="w-3 h-3 text-cyan-400" />
                    <span>PICO Radar</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("passport")}
                    className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${
                      activeTab === "passport"
                        ? "bg-slate-800 text-indigo-300 font-bold"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <ShieldCheck className="w-3 h-3 text-indigo-400" />
                    <span>Passport</span>
                    {groupDetail?.evidence_bundle?.summary && (
                      <span className="text-[10px] px-1 py-0.2 rounded-full bg-indigo-500/20 text-indigo-300 font-mono">
                        {groupDetail.evidence_bundle.summary.total_claims}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("audit")}
                    className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${activeTab === "audit" ? "bg-slate-800 text-cyan-300 font-bold" : "text-slate-400"}`}
                  >
                    <History className="w-3 h-3" />
                    <span>Audit ({groupDetail?.events?.length || 0})</span>
                  </button>
                  {selectedGroup.member_count > 1 && (
                    <button
                      type="button"
                      onClick={() => setActiveTab("members")}
                      className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${activeTab === "members" ? "bg-slate-800 text-cyan-300 font-bold" : "text-slate-400"}`}
                    >
                      <Layers className="w-3 h-3" />
                      <span>Copies ({selectedGroup.member_count})</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setActiveTab("assistant")}
                    className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${activeTab === "assistant" ? "bg-slate-800 text-indigo-300 font-bold" : "text-slate-400"}`}
                  >
                    <Sparkles className="w-3 h-3 text-indigo-400" />
                    <span>AI Assistant</span>
                  </button>
                </div>
              </div>

              <h2 className="text-base sm:text-lg font-bold text-white leading-snug">
                {rep?.title}
              </h2>

              <div className="text-xs text-slate-400 font-mono flex items-center gap-3 flex-wrap">
                <span>{(rep?.authors || []).join(", ")}</span>
                <span>•</span>
                <span>{rep?.journal} ({rep?.year || "n.d."})</span>
                {rep?.pmid && (
                  <>
                    <span>•</span>
                    <span>PMID: {rep.pmid}</span>
                  </>
                )}
              </div>
            </div>

            {/* TAB CONTENT */}
            {activeTab === "radar" && (
              articleRadar ? (
                <ArticleRadarWidget
                  radar={articleRadar}
                  workspaceId={workspaceId}
                  groupId={selectedGroup.id}
                  onRadarUpdated={(updated) => setArticleRadar(updated)}
                />
              ) : (
                <div className="p-8 text-center text-slate-400 text-xs">
                  Loading Missing-Evidence Radar...
                </div>
              )
            )}

            {activeTab === "reader" && (
              <PicoViewer
                key={rep?.id || selectedGroup.id}
                abstractText={rep?.abstract_text || null}
                contentHash={rep?.content_hash || ""}
                initialSpans={[]}
                comparatorAbsent={false}
                onSaveSpans={handleSavePico}
              />
            )}

            {activeTab === "passport" && (
              <EvidencePassportPanel
                workspaceId={workspaceId}
                groupId={selectedGroup.id}
                initialBundle={groupDetail?.evidence_bundle}
                onRefreshGroup={() => {
                  api.groups.getDetail(selectedGroupId, revisionId || undefined).then((d) => setGroupDetail(d));
                }}
              />
            )}

            {activeTab === "audit" && (
              <div className="space-y-3">
                <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5 pb-2 border-b border-slate-800">
                  <History className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Append-Only Reviewer History & Lineage:</span>
                </div>
                {groupDetail?.events && groupDetail.events.length > 0 ? (
                  <div className="space-y-2">
                    {groupDetail.events.map((ev) => (
                      <div
                        key={ev.id}
                        className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono space-y-1"
                      >
                        <div className="flex items-center justify-between text-slate-400">
                          <span className="text-cyan-300 font-semibold">{ev.event_type}</span>
                          <span>{new Date(ev.created_at).toLocaleString()}</span>
                        </div>
                        <div className="text-slate-300">
                          Actor: <span className="text-white font-bold">{ev.actor_id}</span>
                        </div>
                        {ev.payload && (
                          <div className="text-[11px] text-slate-400 bg-slate-950 p-2 rounded">
                            {JSON.stringify(ev.payload)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400 text-xs italic">
                    No reviewer events logged yet for this group.
                  </div>
                )}
              </div>
            )}

            {activeTab === "members" && (
              <div className="space-y-3">
                <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5 pb-2 border-b border-slate-800">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Deduplicated Record Revisions in this Study Group:</span>
                </div>
                <div className="space-y-2.5">
                  {groupDetail?.members.map((mem) => (
                    <div
                      key={mem.id}
                      className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-cyan-300 font-bold">{mem.source.toUpperCase()} • {mem.external_id}</span>
                        {mem.doi && <span className="text-slate-400">DOI: {mem.doi}</span>}
                      </div>
                      <div className="text-slate-200 font-sans">{mem.title}</div>
                      <div className="text-[11px] text-slate-400">{mem.journal} ({mem.year})</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "assistant" && (
              <div className="space-y-3">
                <AssistantPanel
                  workspaceId={workspaceId}
                  targetGroupId={selectedGroup.id}
                />
              </div>
            )}

            {/* Screening Decision Actions Bar */}
            <div className="pt-4 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={() => handleDecision("include")}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow transition"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>Include Study</span>
                </button>

                <button
                  type="button"
                  onClick={() => setExcludeModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-xs shadow transition"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  <span>Exclude (Select Reason...)</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleDecision("maybe", "Uncertain eligibility / Requires reviewer consensus")}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 font-medium text-xs border border-slate-700 transition"
                >
                  <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                  <span>Maybe</span>
                </button>
              </div>

              <button
                type="button"
                onClick={() => handleDecision("maybe", "Reverted decision")}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 text-xs transition font-mono border border-slate-800"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Status</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mandatory Exclusion Reason Modal */}
      {excludeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="glass-panel p-6 rounded-2xl max-w-md w-full space-y-4 border border-red-900/60 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <XCircle className="w-4 h-4 text-red-400" />
                <span>Specify Mandatory Exclusion Reason</span>
              </h3>
              <button
                type="button"
                onClick={() => setExcludeModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Domain Invariant: Excluded records require clinical or methodological justification and evidence.
            </p>

            <div className="space-y-2">
              {EXCLUSION_REASONS.map((reason) => (
                <label
                  key={reason}
                  className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs cursor-pointer transition ${
                    selectedReason === reason
                      ? "bg-red-950/60 border-red-600 text-white font-medium"
                      : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
                  }`}
                >
                  <input
                    type="radio"
                    name="exclusion_reason"
                    checked={selectedReason === reason}
                    onChange={() => setSelectedReason(reason)}
                    className="text-red-500 focus:ring-0"
                  />
                  <span>{reason}</span>
                </label>
              ))}

              <label
                className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs cursor-pointer transition ${
                  selectedReason === "Custom reason..."
                    ? "bg-red-950/60 border-red-600 text-white font-medium"
                    : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
                }`}
              >
                <input
                  type="radio"
                  name="exclusion_reason"
                  checked={selectedReason === "Custom reason..."}
                  onChange={() => setSelectedReason("Custom reason...")}
                  className="text-red-500 focus:ring-0"
                />
                <span>Custom reason...</span>
              </label>

              {selectedReason === "Custom reason..." && (
                <textarea
                  value={customReason}
                  onChange={(e) => setCustomReason(e.target.value)}
                  placeholder="State the explicit methodological or clinical reason for exclusion..."
                  rows={3}
                  className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500"
                />
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setExcludeModalOpen(false)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmExclusion}
                className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs shadow-md transition"
              >
                Confirm Exclude
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
