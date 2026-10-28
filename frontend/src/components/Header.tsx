import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Layers,
  Search,
  Filter,
  Copy,
  History,
  Activity,
  CheckCircle2,
  AlertCircle,
  Brain,
  Sparkles,
  Sun,
  Moon,
  Clock,
  HelpCircle,
} from "lucide-react";
import { api } from "../api/client";
import { useTheme } from "../context/ThemeContext";

export const Header: React.FC = () => {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const [backendStatus, setBackendStatus] = useState<"checking" | "ready" | "offline">("checking");

  useEffect(() => {
    let mounted = true;
    api.health
      .ready()
      .then(() => {
        if (mounted) setBackendStatus("ready");
      })
      .catch(() => {
        api.health
          .live()
          .then(() => {
            if (mounted) setBackendStatus("ready");
          })
          .catch(() => {
            if (mounted) setBackendStatus("offline");
          });
      });
    return () => {
      mounted = false;
    };
  }, []);

  const navLinks = [
    { to: "/", label: "Overview", icon: Sparkles },
    { to: "/reviews", label: "Workspaces", icon: Layers },
    { to: "/reviews/ws-synth-001/search", label: "Query Builder", icon: Search },
    { to: "/reviews/ws-synth-001/records", label: "Screening Queue", icon: Filter },
    { to: "/reviews/ws-synth-001/ml-ranking", label: "ML Prioritization", icon: Brain },
    { to: "/reviews/ws-synth-001/duplicates", label: "Deduplication", icon: Copy },
    { to: "/reviews/ws-synth-001/history", label: "Audit Lineage", icon: History },
    { to: "/reviews/ws-synth-001/radar", label: "PICO Radar", icon: HelpCircle },
    { to: "/reviews/ws-synth-001/search-evolution", label: "Search Evolution", icon: Clock },
  ];

  return (
    <header className="border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 bg-slate-950/80 dark:bg-slate-950/80 light:bg-white/80 backdrop-blur-md sticky top-0 z-50">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 via-amber-400 to-yellow-500 p-0.5 flex items-center justify-center shadow-lg shadow-amber-500/20 group-hover:shadow-amber-500/40 transition">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-amber-400" />
              </div>
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight flex items-center gap-1.5 text-slate-100 dark:text-slate-100 light:text-slate-900">
                Evidra
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  SLR v1
                </span>
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1" aria-label="Main Navigation">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    isActive
                      ? "bg-slate-800/90 dark:bg-slate-800/90 light:bg-slate-100 text-amber-400 dark:text-amber-400 light:text-amber-600 border border-slate-700 dark:border-slate-700 light:border-slate-300 shadow-sm"
                      : "text-slate-400 hover:text-slate-100 dark:hover:text-slate-100 light:hover:text-slate-900 hover:bg-slate-900/60 dark:hover:bg-slate-900/60 light:hover:bg-slate-100/60"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className="p-2 rounded-xl glass-panel hover:border-amber-400 text-slate-300 hover:text-amber-400 transition"
          >
            {theme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
          </button>

          {/* Backend Health Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border ${
              backendStatus === "ready"
                ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/60 shadow-sm shadow-emerald-950/50"
                : backendStatus === "checking"
                ? "bg-amber-950/60 text-amber-300 border-amber-800/60"
                : "bg-rose-950/60 text-rose-300 border-rose-800/60"
            }`}
            title={`Backend Service: ${backendStatus}`}
          >
            {backendStatus === "ready" ? (
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            ) : backendStatus === "checking" ? (
              <Activity className="w-3 h-3 text-amber-400 animate-spin" />
            ) : (
              <AlertCircle className="w-3 h-3 text-rose-400" />
            )}
            <span className="capitalize">{backendStatus}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
