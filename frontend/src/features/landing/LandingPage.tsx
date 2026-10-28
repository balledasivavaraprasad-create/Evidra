import React, { Suspense, lazy } from "react";
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
  Eye,
  Cpu,
  Lock,
} from "lucide-react";
import { HeroStatic } from "./HeroStatic";

// Lazy-load the heavy 3D scene to keep initial bundle load instantaneous
const EvidenceScene3D = lazy(() => import("./EvidenceScene3D"));

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-24 pb-24">
      {/* 1. Hero Section with Scroll-Driven 3D Evidence Observatory */}
      <section className="relative pt-8 sm:pt-14 pb-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full text-xs font-mono bg-cyan-950/60 dark:bg-cyan-950/60 light:bg-cyan-50 text-cyan-300 dark:text-cyan-300 light:text-cyan-700 border border-cyan-800/60 dark:border-cyan-800/60 light:border-cyan-200 shadow-sm backdrop-blur">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Evidra Observatory • Systematic Literature Review</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.12]">
              Clinical Synthesis with{" "}
              <span className="text-metallic-silver block sm:inline">Absolute Provenance</span>{" "}
              and <span className="text-metallic-gold">Zero Guesswork</span>
            </h1>

            <p className="text-slate-300 dark:text-slate-300 light:text-slate-600 text-base sm:text-lg max-w-2xl leading-relaxed">
              Evidra unifies <strong>100% deterministic baseline algorithms</strong> with <strong>LangGraph human review checkpoints</strong> to ingest PubMed & Europe PMC records, enforce exact cannot-link deduplication, and extract Unicode-exact PICO evidence spans.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                to="/reviews"
                className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-slate-950 font-bold text-sm transition shadow-lg shadow-amber-500/20 active:scale-95"
              >
                <span>Enter Workspaces</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/reviews/ws-synth-001/records"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl glass-panel-luxury text-slate-100 dark:text-slate-100 light:text-slate-800 font-semibold text-sm transition hover:border-cyan-400"
              >
                <Eye className="w-4 h-4 text-cyan-400" />
                <span>Live Review Workbench</span>
              </Link>
            </div>

            <div className="pt-6 grid grid-cols-3 gap-4 border-t border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 text-xs">
              <div className="space-y-1">
                <span className="font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 block text-sm">Level 1 Baseline</span>
                <span className="text-slate-400">100% LLM-off offline</span>
              </div>
              <div className="space-y-1">
                <span className="font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 block text-sm">Exact Offsets</span>
                <span className="text-slate-400">Half-open code points</span>
              </div>
              <div className="space-y-1">
                <span className="font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 block text-sm">Snapshot Lineage</span>
                <span className="text-slate-400">Append-only audit trail</span>
              </div>
            </div>
          </div>

          {/* 3D Scene Container with Fallback to Static Evidence Lens */}
          <div className="lg:col-span-5 relative">
            <div className="relative glass-panel-luxury p-2">
              <Suspense fallback={<HeroStatic />}>
                <EvidenceScene3D />
              </Suspense>
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between pointer-events-none px-3 py-1.5 rounded-lg bg-slate-950/70 backdrop-blur border border-slate-800/70 text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  3D Knowledge Lattice Active
                </span>
                <span>Scroll to orbit & track</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Interactive Feature Showcases (Apple-Style Pillar Cards) */}
      <section className="space-y-12">
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <span>Rigorous Evidence Architecture</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Engineered for Precision, Provenance, & Performance
          </h2>
          <p className="text-slate-400 text-sm sm:text-base">
            Every decision, span extraction, and duplicate resolution is persisted immutably with cryptographic text hashes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Multi-Source Literature Ingestion */}
          <div className="glass-panel-luxury p-6 sm:p-8 space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                <Database className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold">Multi-Source Ingestion</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Connect directly to PubMed and Europe PMC APIs with automatic Boolean AST query translation, synonym controls, and pagination quotas.
              </p>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs font-mono space-y-1.5">
              <div className="text-cyan-400 font-semibold flex items-center justify-between">
                <span>AST Query Engine</span>
                <span className="text-[10px] text-emerald-400">OPTIMIZED</span>
              </div>
              <p className="text-slate-400 truncate">metformin[Title] AND &quot;type 2 diabetes&quot;</p>
            </div>
          </div>

          {/* Card 2: Deterministic Deduplication Engine */}
          <div className="glass-panel-luxury p-6 sm:p-8 space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <GitCompare className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold">Same Study ≠ Same Paper</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Separates trial protocols from primary results and follow-up reports. Graph partitioning strictly obeys cannot-link assertions without false merges.
              </p>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs font-mono space-y-1.5">
              <div className="text-amber-400 font-semibold flex items-center justify-between">
                <span>Candidate Pair</span>
                <span className="text-[10px] text-amber-300">100% DOI MATCH</span>
              </div>
              <p className="text-slate-400 truncate">10.1056/nejmoa2024001 • PubMed ~ PMC</p>
            </div>
          </div>

          {/* Card 3: Exact Unicode PICO Spans */}
          <div className="glass-panel-luxury p-6 sm:p-8 space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <FileCheck2 className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold">Exact-Span PICO Tagging</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Highlights Population, Intervention, Comparison, and Outcome spans using Unicode half-open code point indices verified against immutable text hashes.
              </p>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs font-mono space-y-1.5">
              <div className="text-purple-400 font-semibold flex items-center justify-between">
                <span>Verified Evidence Span</span>
                <span className="text-[10px] text-cyan-300">[12, 45) CP</span>
              </div>
              <p className="text-slate-400 truncate">&quot;adults with type 2 diabetes&quot;</p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Deep-Dive Interactive Live Preview Banner */}
      <section className="glass-panel-luxury p-8 sm:p-12 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-amber-500/10 to-transparent blur-3xl pointer-events-none" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10">
          <div className="lg:col-span-8 space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              <span>Level 1 Integration Verified</span>
            </div>
            <h3 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Ready to Experience Systematic Review Acceleration?
            </h3>
            <p className="text-slate-300 text-sm sm:text-base max-w-2xl">
              Launch into the synthetic benchmark workspace to test live duplicate overrides, mandatory exclusion reason modals, real-time conflict banners, and CSV export.
            </p>
          </div>
          <div className="lg:col-span-4 flex flex-col sm:flex-row lg:flex-col gap-3 justify-center">
            <Link
              to="/reviews/ws-synth-001/records"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-slate-950 font-bold text-sm shadow-lg shadow-amber-500/20 transition active:scale-95"
            >
              <span>Launch Review Queue</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/reviews/ws-synth-001/duplicates"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 font-medium text-sm transition"
            >
              <span>Inspect Deduplication Pairs</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
