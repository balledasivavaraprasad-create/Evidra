import React from "react";
import { GitBranch, ShieldCheck, Terminal, Cpu } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-900 bg-slate-950 py-8 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <span className="flex items-center gap-1.5 font-mono text-slate-400">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            Evidra Core v1.0.0
          </span>
          <span className="flex items-center gap-1.5 font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Deterministic Level 1
          </span>
          <span className="flex items-center gap-1.5 font-mono">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            FastAPI + SQLite WAL + LangGraph
          </span>
        </div>

        <div className="flex items-center gap-4 text-slate-400">
          <span className="flex items-center gap-1 font-mono">
            <GitBranch className="w-3.5 h-3.5 text-slate-500" />
            Track 1: Epoch Hackathon
          </span>
        </div>
      </div>
    </footer>
  );
};
