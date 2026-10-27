import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { Search, Play, Database, Calendar, Filter, Sparkles } from "lucide-react";
import { NotImplementedNotice } from "../../components/NotImplementedNotice";

export const QueryBuilderPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [queryTerm, setQueryTerm] = useState("(metformin[Title/Abstract]) AND (type 2 diabetes[Title/Abstract])");
  const [source, setSource] = useState<"pubmed" | "europepmc">("pubmed");
  const [yearStart, setYearStart] = useState("2020");
  const [yearEnd, setYearEnd] = useState("2026");

  return (
    <div className="space-y-6 pb-12">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Search className="w-5 h-5 text-cyan-400" />
          <span>Structured Query Builder & Ingestion</span>
        </h1>
        <p className="text-slate-400 text-xs">
          Workspace: <code className="text-cyan-300 font-mono">{id || "ws-demo-01"}</code> • Define search strategy, check counts, and import records.
        </p>
      </div>

      <NotImplementedNotice
        featureName="Live PubMed & Europe PMC Ingestion"
        targetTask="D02"
        taskOwner="dev-D"
        description="Literature adapters, NCBI E-Utilities counts, and durable import jobs are being implemented in D02. This preview demonstrates the query builder UI and parameter bindings."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Query Builder Form */}
        <div className="lg:col-span-8 space-y-4">
          <div className="glass-panel p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              <span>Search Parameters</span>
            </h3>

            <div>
              <label htmlFor="query-string" className="block text-xs font-medium text-slate-300 mb-1">
                Boolean Query String
              </label>
              <textarea
                id="query-string"
                rows={3}
                value={queryTerm}
                onChange={(e) => setQueryTerm(e.target.value)}
                className="w-full p-3 rounded-lg bg-slate-900 border border-slate-700 text-white font-mono text-xs focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="source-select" className="block text-xs font-medium text-slate-300 mb-1">
                  Target Database
                </label>
                <select
                  id="source-select"
                  value={source}
                  onChange={(e) => setSource(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:border-cyan-500"
                >
                  <option value="pubmed">PubMed (NCBI E-Utilities)</option>
                  <option value="europepmc">Europe PMC (REST API)</option>
                </select>
              </div>

              <div>
                <label htmlFor="year-start" className="block text-xs font-medium text-slate-300 mb-1">
                  Start Year
                </label>
                <input
                  id="year-start"
                  type="number"
                  value={yearStart}
                  onChange={(e) => setYearStart(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:border-cyan-500"
                />
              </div>

              <div>
                <label htmlFor="year-end" className="block text-xs font-medium text-slate-300 mb-1">
                  End Year
                </label>
                <input
                  id="year-end"
                  type="number"
                  value={yearEnd}
                  onChange={(e) => setYearEnd(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Execute Count Probe</span>
              </button>
              <button
                type="button"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
              >
                <span>Save Query Version</span>
              </button>
            </div>
          </div>
        </div>

        {/* Count Preview & History Panel */}
        <div className="lg:col-span-4 space-y-4">
          <div className="glass-panel p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-teal-400" />
              <span>Acquisition Preview</span>
            </h3>

            <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Database Hits</span>
                <span className="text-emerald-400 font-bold font-mono text-base">348 papers</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Import Cap</span>
                <span className="text-slate-300 font-mono">200 max</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Source Namespace</span>
                <span className="text-cyan-300 font-mono">{source}</span>
              </div>
            </div>

            <button
              type="button"
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
            >
              Approve & Ingest to Corpus
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
