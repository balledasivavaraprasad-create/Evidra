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
  Sparkles,
} from "lucide-react";
import { api } from "../api/client";

export const Header: React.FC = () => {
  const location = useLocation();
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
    { to: "/reviews/ws-demo-01/search", label: "Query Builder", icon: Search },
    { to: "/reviews/ws-demo-01/records", label: "Screening Queue", icon: Filter },
    { to: "/reviews/ws-demo-01/duplicates", label: "Deduplication", icon: Copy },
    { to: "/reviews/ws-demo-01/history", label: "Version History", icon: History },
  ];

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-teal-400 p-0.5 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/40 transition">
              <div className="w-full h-full bg-slate-950 rounded-[7px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <span className="font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
                Evidra
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60">
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
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    isActive
                      ? "bg-slate-800 text-cyan-300 border border-slate-700"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
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
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono border ${
              backendStatus === "ready"
                ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/60"
                : backendStatus === "checking"
                ? "bg-amber-950/60 text-amber-300 border-amber-800/60"
                : "bg-red-950/60 text-red-300 border-red-800/60"
            }`}
            title={`Backend Status: ${backendStatus}`}
          >
            {backendStatus === "ready" ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : backendStatus === "checking" ? (
              <Activity className="w-3.5 h-3.5 animate-pulse text-amber-400" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 text-red-400" />
            )}
            <span className="hidden sm:inline">
              API: {backendStatus === "ready" ? "Connected" : backendStatus}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
