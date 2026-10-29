import React from "react";
import type { PrismaStages, PrismaStage } from "../../api/client";

interface PrismaDiagramProps {
  stages: PrismaStages;
  onSelectStage: (stage: PrismaStage, label: string) => void;
  svgRef?: React.RefObject<SVGSVGElement | null>;
}

export const PrismaDiagram: React.FC<PrismaDiagramProps> = ({
  stages,
  onSelectStage,
  svgRef,
}) => {
  const {
    identification,
    pre_screening,
    screening,
    retrieval,
    included,
  } = stages;

  const dbSources = identification.database_sources || [];
  const exclusionReasons = screening.exclusion_reasons || [];

  return (
    <div className="w-full overflow-x-auto bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl">
      <svg
        ref={svgRef}
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 960 840"
        className="w-full h-auto max-w-4xl mx-auto font-sans select-none"
        style={{ minWidth: "720px" }}
      >
        <defs>
          <marker
            id="prisma-arrow"
            viewBox="0 0 10 10"
            refX="6"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 8 5 L 0 9 z" fill="#94a3b8" />
          </marker>
        </defs>

        {/* Phase Banners on Left Margin */}
        <g id="phase-labels" className="text-xs font-bold uppercase tracking-wider fill-slate-400">
          {/* Identification Phase */}
          <rect x="10" y="20" width="30" height="230" rx="4" fill="#1e293b" />
          <text
            x="-135"
            y="30"
            transform="rotate(-90)"
            textAnchor="middle"
            className="fill-amber-400 font-semibold text-xs tracking-widest"
          >
            IDENTIFICATION
          </text>

          {/* Screening Phase */}
          <rect x="10" y="270" width="30" height="370" rx="4" fill="#1e293b" />
          <text
            x="-455"
            y="30"
            transform="rotate(-90)"
            textAnchor="middle"
            className="fill-cyan-400 font-semibold text-xs tracking-widest"
          >
            SCREENING
          </text>

          {/* Included Phase */}
          <rect x="10" y="660" width="30" height="150" rx="4" fill="#1e293b" />
          <text
            x="-735"
            y="30"
            transform="rotate(-90)"
            textAnchor="middle"
            className="fill-emerald-400 font-semibold text-xs tracking-widest"
          >
            INCLUDED
          </text>
        </g>

        {/* ============================================================== */}
        {/* PHASE 1: IDENTIFICATION                                        */}
        {/* ============================================================== */}

        {/* Box 1: Records identified from databases */}
        <g
          id="box-identification"
          onClick={() => onSelectStage("identification", "Records Identified via Databases & Sources")}
          className="cursor-pointer group"
          role="button"
          tabIndex={0}
        >
          <rect
            x="60"
            y="20"
            width="420"
            height="140"
            rx="8"
            fill="#0f172a"
            stroke="#38bdf8"
            strokeWidth="2"
            className="transition-all duration-200 hover:fill-slate-800"
          />
          <text x="80" y="48" className="fill-slate-100 font-bold text-sm">
            Records identified from databases & registers
          </text>
          <text x="80" y="70" className="fill-cyan-400 font-semibold text-xs">
            Total records: {identification.total_identified}
          </text>
          {dbSources.map((src, i) => (
            <text key={src.source_name} x="90" y={92 + i * 20} className="fill-slate-300 text-xs">
              • {src.source_name}: {src.records_count} records
            </text>
          ))}
          {dbSources.length === 0 && (
            <text x="90" y="92" className="fill-slate-400 text-xs italic">
              No database records identified yet
            </text>
          )}
        </g>

        {/* Connector from Box 1 down to Records Screened */}
        <path
          d="M 270 160 L 270 270"
          fill="none"
          stroke="#64748b"
          strokeWidth="2"
          markerEnd="url(#prisma-arrow)"
        />

        {/* Branch Arrow to Pre-screening Exclusions */}
        <path
          d="M 270 215 L 530 215"
          fill="none"
          stroke="#64748b"
          strokeWidth="2"
          markerEnd="url(#prisma-arrow)"
        />

        {/* Box 2: Records removed before screening */}
        <g
          id="box-prescreening"
          onClick={() => onSelectStage("pre_screening", "Records Removed Before Screening")}
          className="cursor-pointer group"
          role="button"
          tabIndex={0}
        >
          <rect
            x="540"
            y="150"
            width="390"
            height="130"
            rx="8"
            fill="#0f172a"
            stroke="#f59e0b"
            strokeWidth="2"
            className="transition-all duration-200 hover:fill-slate-800"
          />
          <text x="560" y="178" className="fill-slate-100 font-bold text-sm">
            Records removed before screening
          </text>
          <text x="560" y="198" className="fill-amber-400 font-semibold text-xs">
            Total removed: {pre_screening.total_removed}
          </text>
          <text x="575" y="222" className="fill-slate-300 text-xs">
            • Duplicate records removed: {pre_screening.duplicate_records_removed}
          </text>
          <text x="575" y="244" className="fill-slate-300 text-xs">
            • Marked ineligible / other removals: {pre_screening.other_records_removed}
          </text>
          <text x="575" y="266" className="fill-slate-300 text-xs">
            • Net records entering screening: {pre_screening.records_eligible_for_screening}
          </text>
        </g>

        {/* ============================================================== */}
        {/* PHASE 2: SCREENING                                             */}
        {/* ============================================================== */}

        {/* Box 3: Records Screened */}
        <g
          id="box-screening"
          onClick={() => onSelectStage("screening", "Records Screened (Title & Abstract)")}
          className="cursor-pointer group"
          role="button"
          tabIndex={0}
        >
          <rect
            x="60"
            y="280"
            width="420"
            height="110"
            rx="8"
            fill="#0f172a"
            stroke="#60a5fa"
            strokeWidth="2"
            className="transition-all duration-200 hover:fill-slate-800"
          />
          <text x="80" y="308" className="fill-slate-100 font-bold text-sm">
            Records screened (Title & Abstract)
          </text>
          <text x="80" y="332" className="fill-sky-400 font-semibold text-xs">
            Total eligible for screening: {pre_screening.records_eligible_for_screening}
          </text>
          <text x="90" y="354" className="fill-slate-300 text-xs">
            • Completed decisions: {screening.records_screened}
          </text>
          <text x="90" y="374" className="fill-slate-400 text-xs">
            • Pending: {screening.records_pending} | Maybe: {screening.records_maybe} | Conflicts: {screening.records_conflicts}
          </text>
        </g>

        {/* Connector from Box 3 to Box 4 (Exclusions) */}
        <path
          d="M 480 335 L 530 335"
          fill="none"
          stroke="#64748b"
          strokeWidth="2"
          markerEnd="url(#prisma-arrow)"
        />

        {/* Box 4: Records Excluded */}
        <g
          id="box-exclusions"
          onClick={() => onSelectStage("screening", "Records Excluded During Screening")}
          className="cursor-pointer group"
          role="button"
          tabIndex={0}
        >
          <rect
            x="540"
            y="295"
            width="390"
            height="150"
            rx="8"
            fill="#0f172a"
            stroke="#f43f5e"
            strokeWidth="2"
            className="transition-all duration-200 hover:fill-slate-800"
          />
          <text x="560" y="322" className="fill-slate-100 font-bold text-sm">
            Records excluded
          </text>
          <text x="560" y="342" className="fill-rose-400 font-semibold text-xs">
            Total excluded: {screening.records_excluded}
          </text>
          <text x="560" y="362" className="fill-slate-400 text-xs font-medium">
            Top exclusion reasons:
          </text>
          {exclusionReasons.slice(0, 3).map((r, i) => (
            <text key={r.reason} x="575" y={382 + i * 18} className="fill-slate-300 text-xs">
              • {r.reason}: {r.count} ({r.percentage.toFixed(1)}%)
            </text>
          ))}
          {exclusionReasons.length === 0 && (
            <text x="575" y="382" className="fill-slate-400 text-xs italic">
              No exclusions recorded
            </text>
          )}
          {exclusionReasons.length > 3 && (
            <text x="575" y={382 + 3 * 18} className="fill-rose-300 text-[11px] underline">
              + {exclusionReasons.length - 3} more reasons (click to view all)
            </text>
          )}
        </g>

        {/* Connector from Box 3 down to Full-Text Retrieval / Disclosure */}
        <path
          d="M 270 390 L 270 480"
          fill="none"
          stroke="#64748b"
          strokeWidth="2"
          markerEnd="url(#prisma-arrow)"
        />

        {/* ============================================================== */}
        {/* PHASE 3: FULL-TEXT RETRIEVAL & ELIGIBILITY (TRUTHFUL)          */}
        {/* ============================================================== */}

        {/* Box 5: Reports sought for retrieval */}
        <g
          id="box-retrieval"
          onClick={() => onSelectStage("retrieval", "Reports Sought for Retrieval")}
          className="cursor-pointer group"
          role="button"
          tabIndex={0}
        >
          <rect
            x="60"
            y="490"
            width="420"
            height="125"
            rx="8"
            fill="#0f172a"
            stroke="#94a3b8"
            strokeWidth="1.5"
            strokeDasharray="4 3"
            className="transition-all duration-200 hover:fill-slate-800"
          />
          <text x="80" y="518" className="fill-slate-100 font-bold text-sm">
            Reports sought for retrieval
          </text>
          <rect x="80" y="528" width="165" height="20" rx="4" fill="#334155" />
          <text x="86" y="542" className="fill-amber-300 font-semibold text-[11px]">
            Abstract-Phase Screening
          </text>
          <text x="80" y="570" className="fill-slate-300 text-xs">
            • Reports sought: {retrieval.reports_sought_for_retrieval}
          </text>
          <text x="80" y="590" className="fill-slate-400 text-xs italic">
            Note: Evidra screening occurs at title/abstract level.
          </text>
          <text x="80" y="606" className="fill-slate-400 text-xs italic">
            Full-text retrieval is not initiated in current protocol.
          </text>
        </g>

        {/* Branch Arrow to Retrieval Exclusions */}
        <path
          d="M 480 550 L 530 550"
          fill="none"
          stroke="#64748b"
          strokeWidth="2"
          strokeDasharray="4 3"
          markerEnd="url(#prisma-arrow)"
        />

        {/* Box 6: Reports not retrieved */}
        <g
          id="box-not-retrieved"
          onClick={() => onSelectStage("retrieval", "Reports Not Retrieved")}
          className="cursor-pointer group"
          role="button"
          tabIndex={0}
        >
          <rect
            x="540"
            y="510"
            width="390"
            height="80"
            rx="8"
            fill="#0f172a"
            stroke="#64748b"
            strokeWidth="1.5"
            strokeDasharray="4 3"
            className="transition-all duration-200 hover:fill-slate-800"
          />
          <text x="560" y="538" className="fill-slate-100 font-bold text-sm">
            Reports not retrieved
          </text>
          <text x="560" y="562" className="fill-slate-400 text-xs">
            Reports not retrieved: {retrieval.reports_not_retrieved}
          </text>
          <text x="560" y="578" className="fill-slate-500 text-[11px] italic">
            Stage marked not started in protocol
          </text>
        </g>

        {/* Connector from Box 5 down to Included */}
        <path
          d="M 270 615 L 270 670"
          fill="none"
          stroke="#64748b"
          strokeWidth="2"
          markerEnd="url(#prisma-arrow)"
        />

        {/* ============================================================== */}
        {/* PHASE 4: INCLUDED                                              */}
        {/* ============================================================== */}

        {/* Box 7: Studies and Reports Included */}
        <g
          id="box-included"
          onClick={() => onSelectStage("included", "Studies & Reports Included")}
          className="cursor-pointer group"
          role="button"
          tabIndex={0}
        >
          <rect
            x="60"
            y="675"
            width="420"
            height="125"
            rx="8"
            fill="#064e3b"
            stroke="#10b981"
            strokeWidth="2.5"
            className="transition-all duration-200 hover:fill-emerald-950"
          />
          <text x="80" y="705" className="fill-emerald-100 font-bold text-base">
            Studies included in review
          </text>
          <text x="80" y="735" className="fill-emerald-300 font-extrabold text-2xl">
            {included.studies_included} unique studies
          </text>
          <text x="80" y="762" className="fill-emerald-200 font-medium text-xs">
            Reports of included studies: {included.reports_included} publication records
          </text>
          <text x="80" y="782" className="fill-emerald-300/80 text-[11px]">
            Title/Abstract screening included: {included.studies_included_title_abstract}
          </text>
        </g>
      </svg>
    </div>
  );
};
