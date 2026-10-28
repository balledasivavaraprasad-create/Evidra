import React from "react";

export const Footer: React.FC = () => {
  return (
    <footer className="relative z-10 mt-24 border-t border-[var(--border-subtle)] bg-[var(--bg-base)]/85 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs text-[var(--text-muted)]">
        <div className="flex items-center gap-3">
          <span className="font-serif text-base text-[var(--text-secondary)]">Evidra</span>
          <span>Systematic literature review with traceable evidence.</span>
        </div>
        <ul className="flex flex-wrap items-center gap-x-5 gap-y-1">
          <li>Core v1.0.0</li>
          <li>Deterministic level 1</li>
          <li>FastAPI, SQLite and LangGraph</li>
          <li>Epoch Hackathon, track 1</li>
        </ul>
      </div>
    </footer>
  );
};
