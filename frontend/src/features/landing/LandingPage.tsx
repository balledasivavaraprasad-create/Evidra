import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Shield,
  Layers,
  Sparkles,
  GitCompare,
  FileCheck2,
  Database,
  History,
  CheckCircle,
} from "lucide-react";
import { HeroStatic } from "./HeroStatic";

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-16 pb-16">
      {/* Hero Section */}
      <section className="relative pt-12 pb-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/60">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Track 1 • Evidence Observatory</span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.15]">
              Accelerate Systematic Reviews with{" "}
              <span className="bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
                Clinical Rigor & Provenance
              </span>
            </h1>

            <p className="text-slate-300 text-base sm:text-lg max-w-2xl leading-relaxed">
              Evidra combines a <strong>100% deterministic baseline</strong> with <strong>LangGraph human-in-the-loop workflows</strong> to automate search ingestion, exact deduplication, screening, and PICO annotation without losing reviewer history.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                to="/reviews"
                className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-slate-950 font-semibold text-sm transition shadow-lg shadow-cyan-500/20"
              >
                <span>Enter Workspaces</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/reviews/ws-demo-01/records"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700/80 font-medium text-sm transition"
              >
                <span>Live Workbench Preview</span>
              </Link>
            </div>

            <div className="pt-4 grid grid-cols-3 gap-4 border-t border-slate-800/80 text-xs text-slate-400">
              <div>
                <span className="font-bold text-white block text-sm">Level 1 Baseline</span>
                <span>Zero-LLM required</span>
              </div>
              <div>
                <span className="font-bold text-white block text-sm">Exact Offsets</span>
                <span>Unicode half-open spans</span>
              </div>
              <div>
                <span className="font-bold text-white block text-sm">Level 2 Loop</span>
                <span>Immutable snapshots</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5">
            <HeroStatic />
          </div>
        </div>
      </section>

      {/* Core Architectural Pillars */}
      <section className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl font-bold text-white">Engineered for Precision & Trust</h2>
          <p className="text-slate-400 text-sm">
            Every machine suggestion is strictly separated from human decisions, keeping your evidence synthesis fully auditable.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-panel p-6 space-y-3 glass-panel-hover">
            <div className="w-10 h-10 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Multi-Database Ingestion & Dedup</h3>
            <p className="text-slate-400 text-xs leading-relaxed">
              Connects to PubMed E-Utilities and Europe PMC REST with rate limits. Deduplicates across DOI, normalized title, and authors while preserving study vs. paper separation.
            </p>
          </div>

          <div className="glass-panel p-6 space-y-3 glass-panel-hover">
            <div className="w-10 h-10 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Screening & Exact PICO Extraction</h3>
            <p className="text-slate-400 text-xs leading-relaxed">
              Transparent inclusion/exclusion heuristics with logged reasons. PICO entities are verified against Unicode half-open code-point offsets into canonical abstract text.
            </p>
          </div>

          <div className="glass-panel p-6 space-y-3 glass-panel-hover">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <History className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Snapshot Loops & Exact Revert</h3>
            <p className="text-slate-400 text-xs leading-relaxed">
              Iterating on a search query preserves past human decisions. Reverting restores the historical corpus directly from SQLite without re-fetching live APIs.
            </p>
          </div>
        </div>
      </section>

      {/* Review Pipeline Steps */}
      <section className="glass-panel p-8 border-slate-800">
        <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <Database className="w-5 h-5 text-cyan-400" />
          <span>7-Step Deterministic Review Protocol</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-cyan-400 font-mono font-bold block mb-1">01 • Question</span>
            <p className="text-slate-300">Formulate PICO question and versioned eligibility criteria.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-cyan-400 font-mono font-bold block mb-1">02 • Search</span>
            <p className="text-slate-300">Execute count-only queries and preview results before importing.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-teal-400 font-mono font-bold block mb-1">03 • Deduplicate</span>
            <p className="text-slate-300">Cluster identical papers while differentiating study arms.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-teal-400 font-mono font-bold block mb-1">04 • Screen</span>
            <p className="text-slate-300">Evaluate population, study design, and species with audit trails.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-indigo-400 font-mono font-bold block mb-1">05 • Annotate</span>
            <p className="text-slate-300">Extract exact Population, Intervention, Comparator, and Outcome.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-indigo-400 font-mono font-bold block mb-1">06 • Review</span>
            <p className="text-slate-300">Resolve edge cases, override decisions, and handle conflicts.</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 sm:col-span-2">
            <span className="text-emerald-400 font-mono font-bold block mb-1">07 • Export & Loop</span>
            <p className="text-slate-300">Download sanitized PRISMA-compatible CSV/RIS or iterate queries with preserved history.</p>
          </div>
        </div>
      </section>
    </div>
  );
};
