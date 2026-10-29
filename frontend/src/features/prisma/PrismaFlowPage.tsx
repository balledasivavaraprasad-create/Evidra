import React, { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import {
  FileText,
  Download,
  Camera,
  History,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Layers,
  ArrowRight,
  Filter,
  Info,
  Share2,
} from "lucide-react";
import {
  api,
  PrismaReportResponse,
  PrismaStage,
} from "../../api/client";
import { PrismaDiagram } from "./PrismaDiagram";
import { PrismaStageRecordsModal } from "./PrismaStageRecordsModal";
import { PrismaSnapshotModal } from "./PrismaSnapshotModal";
import { PrismaHistoryDrawer } from "./PrismaHistoryDrawer";

export const PrismaFlowPage: React.FC = () => {
  const { id: routeWorkspaceId } = useParams<{ id: string }>();
  const [workspaceId, setWorkspaceId] = useState<string>(routeWorkspaceId || "");
  const [report, setReport] = useState<PrismaReportResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Modals & Drawers
  const [selectedStage, setSelectedStage] = useState<PrismaStage | null>(null);
  const [selectedStageLabel, setSelectedStageLabel] = useState<string>("");
  const [showSnapshotModal, setShowSnapshotModal] = useState<boolean>(false);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState<boolean>(false);

  // SVG ref for exporting
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (routeWorkspaceId && routeWorkspaceId !== workspaceId) {
      setWorkspaceId(routeWorkspaceId);
    }
  }, [routeWorkspaceId]);

  useEffect(() => {
    if (workspaceId) {
      fetchReport();
    }
  }, [workspaceId]);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.prisma.getReport(workspaceId);
      setReport(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load PRISMA 2020 report.");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await api.prisma.getReport(workspaceId);
      setReport(res);
    } catch (err: any) {
      setError(err?.message || "Failed to refresh PRISMA counts.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleExportCsv = async () => {
    try {
      const csvText = await api.prisma.downloadCsv(workspaceId);
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `prisma_2020_${workspaceId}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert("Failed to export CSV: " + (err?.message || err));
    }
  };

  const handleExportSvg = () => {
    if (!svgRef.current) return;
    try {
      const serializer = new XMLSerializer();
      let source = serializer.serializeToString(svgRef.current);
      if (!source.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
        source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
      }
      const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `prisma_flow_${workspaceId}.svg`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert("Failed to export SVG: " + (err?.message || err));
    }
  };

  const handleStageClick = (stage: PrismaStage, label: string) => {
    setSelectedStage(stage);
    setSelectedStageLabel(label);
  };

  const handleSnapshotSelected = (snapshot: PrismaReportResponse) => {
    setReport(snapshot);
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-400">Computing PRISMA 2020 flow counts from database...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4">
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 space-y-4">
          <div className="flex items-center gap-2 font-bold text-base">
            <AlertTriangle className="w-5 h-5" />
            <span>Error Generating PRISMA Flow</span>
          </div>
          <p className="text-sm">{error || "Review workspace data could not be retrieved."}</p>
          <button
            onClick={fetchReport}
            className="px-4 py-2 bg-rose-500 text-white rounded-lg text-xs font-semibold hover:bg-rose-600 transition"
          >
            Retry Calculation
          </button>
        </div>
      </div>
    );
  }

  const { stages, reconciliation, validation_issues } = report;
  const exclusionSummary = report.exclusion_reasons_summary || [];
  const dbSources = stages.identification.database_sources || [];

  return (
    <div className="space-y-6 pb-16">
      {/* Top Banner if Snapshot is active */}
      {!report.is_live && (
        <div className="p-3 bg-amber-500/20 border border-amber-500/40 rounded-xl flex items-center justify-between text-xs text-amber-200">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              Viewing historical snapshot: <strong>{report.snapshot_id}</strong> (Captured: {new Date(report.generated_at).toLocaleString()})
            </span>
          </div>
          <button
            onClick={fetchReport}
            className="px-3 py-1 rounded-lg bg-amber-500 text-slate-950 font-bold hover:bg-amber-400 transition"
          >
            Exit to Live Data
          </button>
        </div>
      )}

      {/* Header and Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
            <span>WORKSPACE: {workspaceId}</span>
            <span>•</span>
            <span>SCHEMA: PRISMA {report.schema_version}</span>
            {report.is_live && (
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-sans font-semibold text-[10px]">
                LIVE RECONCILED
              </span>
            )}
          </div>
          <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2.5">
            <FileText className="w-6 h-6 text-amber-400" />
            PRISMA 2020 Flow Diagram & Reporting
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated, audited study flow calculation derived directly from database records and deduplication trees.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition"
            title="Recalculate counts live"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <button
            onClick={() => setShowSnapshotModal(true)}
            className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition"
          >
            <Camera className="w-3.5 h-3.5 text-amber-400" />
            Save Snapshot
          </button>

          <button
            onClick={() => setShowHistoryDrawer(true)}
            className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition"
          >
            <History className="w-3.5 h-3.5 text-cyan-400" />
            Snapshots
          </button>

          <button
            onClick={handleExportCsv}
            className="px-3 py-2 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-semibold flex items-center gap-1.5 border border-amber-500/30 transition"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>

          <button
            onClick={handleExportSvg}
            className="px-3 py-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 border border-cyan-500/30 transition"
          >
            <Share2 className="w-3.5 h-3.5" />
            Export SVG
          </button>
        </div>
      </div>

      {/* Summary KPI Cards Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div
          onClick={() => handleStageClick("identification", "Records Identified")}
          className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-cyan-500/50 cursor-pointer transition"
        >
          <div className="text-[11px] font-medium text-slate-400">Total Identified</div>
          <div className="text-xl font-extrabold text-cyan-400 mt-0.5">
            {stages.identification.total_identified}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Database & register queries</div>
        </div>

        <div
          onClick={() => handleStageClick("pre_screening", "Duplicates Removed")}
          className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-amber-500/50 cursor-pointer transition"
        >
          <div className="text-[11px] font-medium text-slate-400">Duplicates Removed</div>
          <div className="text-xl font-extrabold text-amber-400 mt-0.5">
            {stages.pre_screening.duplicate_records_removed}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Deduplication clustering</div>
        </div>

        <div
          onClick={() => handleStageClick("screening", "Records Screened")}
          className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-blue-500/50 cursor-pointer transition"
        >
          <div className="text-[11px] font-medium text-slate-400">Records Screened</div>
          <div className="text-xl font-extrabold text-sky-400 mt-0.5">
            {stages.screening.records_screened}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Title & abstract evaluations</div>
        </div>

        <div
          onClick={() => handleStageClick("screening", "Records Excluded")}
          className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-rose-500/50 cursor-pointer transition"
        >
          <div className="text-[11px] font-medium text-slate-400">Records Excluded</div>
          <div className="text-xl font-extrabold text-rose-400 mt-0.5">
            {stages.screening.records_excluded}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Categorized with reasons</div>
        </div>

        <div
          onClick={() => handleStageClick("included", "Studies Included")}
          className="p-3.5 rounded-xl bg-slate-900 border border-emerald-900/60 hover:border-emerald-500 cursor-pointer transition"
        >
          <div className="text-[11px] font-medium text-slate-400">Included Studies</div>
          <div className="text-xl font-extrabold text-emerald-400 mt-0.5">
            {stages.included.studies_included}
          </div>
          <div className="text-[10px] text-emerald-300/70 mt-1">Unique canonical studies</div>
        </div>

        <div
          onClick={() => handleStageClick("included", "Reports of Included Studies")}
          className="p-3.5 rounded-xl bg-slate-900 border border-emerald-900/60 hover:border-emerald-500 cursor-pointer transition"
        >
          <div className="text-[11px] font-medium text-slate-400">Included Reports</div>
          <div className="text-xl font-extrabold text-emerald-300 mt-0.5">
            {stages.included.reports_included}
          </div>
          <div className="text-[10px] text-emerald-300/70 mt-1">All publication copies</div>
        </div>
      </div>

      {/* Mathematical Reconciliation & Validation Alert */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            {reconciliation.is_reconciled ? (
              <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" /> Flow Arithmetic Reconciled
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
                <AlertTriangle className="w-4 h-4" /> Reconciliation Discrepancy Detected
              </span>
            )}
            <span className="text-[11px] text-slate-500">•</span>
            <span className="text-[11px] text-slate-400">
              Identification Balance: <code>{reconciliation.identification_balance}</code> | Screening Balance: <code>{reconciliation.screening_balance}</code>
            </span>
          </div>
          <p className="text-xs text-slate-400">
            {reconciliation.discrepancy_explanation || "All database records, duplicate groups, screening decisions, and final inclusions balance exactly."}
          </p>
        </div>

        {validation_issues && validation_issues.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            {validation_issues.map((issue, idx) => (
              <span
                key={idx}
                className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                  issue.severity === "error"
                    ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
                    : issue.severity === "warning"
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                    : "bg-slate-800 text-slate-300 border-slate-700"
                }`}
                title={issue.message}
              >
                {issue.stage}: {issue.message}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Main Interactive Diagram */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-400 px-1">
          <span className="font-semibold text-slate-300">Interactive PRISMA 2020 Flow Diagram</span>
          <span className="italic text-[11px]">Click any box to inspect underlying records</span>
        </div>
        <PrismaDiagram
          stages={stages}
          onSelectStage={handleStageClick}
          svgRef={svgRef}
        />
      </div>

      {/* Detailed Breakdowns Grid: Sources & Exclusion Reasons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Exclusion Reasons Breakdown */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Filter className="w-4 h-4 text-rose-400" />
              Exclusion Reasons Frequency
            </h3>
            <span className="text-xs text-slate-400">
              Total: {exclusionSummary.reduce((acc, r) => acc + r.count, 0)} records
            </span>
          </div>

          {exclusionSummary.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 italic">
              No exclusion reasons logged for this review yet.
            </div>
          ) : (
            <div className="space-y-3">
              {exclusionSummary.map((item) => (
                <div
                  key={item.reason}
                  onClick={() => handleStageClick("screening", `Excluded: ${item.reason}`)}
                  className="p-2.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 cursor-pointer border border-slate-755 transition space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{item.reason}</span>
                    <span className="text-rose-400 font-bold">
                      {item.count} ({item.percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-rose-500 h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, item.percentage)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Database Sources Breakdown */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              Identification Sources Breakdown
            </h3>
            <span className="text-xs text-slate-400">
              {dbSources.length} sources
            </span>
          </div>

          <div className="space-y-3">
            {dbSources.map((src) => {
              const total = stages.identification.total_identified || 1;
              const pct = ((src.records_count / total) * 100).toFixed(1);
              return (
                <div
                  key={src.source_name}
                  onClick={() => handleStageClick("identification", `Source: ${src.source_name}`)}
                  className="p-2.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 cursor-pointer border border-slate-755 transition space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{src.source_name}</span>
                    <span className="text-cyan-400 font-bold">
                      {src.records_count} records ({pct}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-750/50 flex items-start gap-2 text-xs text-slate-400">
            <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong>Transparent Methodology:</strong> Evidra records source database namespaces for every citation imported. In-flight duplicates are matched across databases and linked into canonical study groups.
            </div>
          </div>
        </div>
      </div>

      {/* Record Drill-down Modal */}
      {selectedStage && (
        <PrismaStageRecordsModal
          workspaceId={workspaceId}
          stage={selectedStage}
          stageLabel={selectedStageLabel}
          onClose={() => setSelectedStage(null)}
          corpusRevisionId={report.corpus_revision_id || undefined}
          queryVersionId={report.query_version_id || undefined}
        />
      )}

      {/* Snapshot Creation Modal */}
      {showSnapshotModal && (
        <PrismaSnapshotModal
          workspaceId={workspaceId}
          corpusRevisionId={report.corpus_revision_id || undefined}
          queryVersionId={report.query_version_id || undefined}
          onClose={() => setShowSnapshotModal(false)}
          onSnapshotCreated={handleSnapshotSelected}
        />
      )}

      {/* Snapshot History Drawer */}
      <PrismaHistoryDrawer
        workspaceId={workspaceId}
        isOpen={showHistoryDrawer}
        onClose={() => setShowHistoryDrawer(false)}
        onSelectSnapshot={handleSnapshotSelected}
        activeSnapshotId={report.snapshot_id}
      />
    </div>
  );
};
