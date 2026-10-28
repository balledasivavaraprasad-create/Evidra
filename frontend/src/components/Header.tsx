import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { LogOut, Sun, Moon } from "lucide-react";
import { api } from "../api/client";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { getRememberedWorkspaceId, reconcileRememberedWorkspace, workspaceIdFromPath } from "../context/currentWorkspace";

const buildNavGroups = (ws: string): Array<Array<{ to: string; label: string; title: string }>> => [
  [
    { to: "/", label: "Overview", title: "Overview" },
    { to: "/reviews", label: "Workspaces", title: "Review workspaces" },
  ],
  [
    { to: `${ws}/setup`, label: "Query", title: "Review question, search and import" },
    { to: `${ws}/records`, label: "Screening", title: "Screening queue" },
    { to: `${ws}/ml-ranking`, label: "ML ranking", title: "ML prioritization" },
    { to: `${ws}/duplicates`, label: "Duplicates", title: "Deduplication" },
    { to: `${ws}/history`, label: "Lineage", title: "Audit lineage" },
    { to: `${ws}/radar`, label: "PICO radar", title: "Missing-evidence radar" },
    { to: `${ws}/devils-advocate`, label: "Devil's advocate", title: "Devil's advocate reviewer" },
    { to: `${ws}/search-evolution`, label: "Evolution", title: "Search evolution" },
  ],
];

export const Header: React.FC = () => {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { authRequired, signOut } = useAuth();

  // Menu links follow the review you're working in
  // (WorkspaceGuard remembers a review once the server confirms it exists.)
  const urlWorkspace = workspaceIdFromPath(location.pathname);
  // On load, drop a remembered review the server no longer has (e.g. after a restart wiped it)
  const [, setReconciled] = useState(0);
  useEffect(() => {
    let mounted = true;
    api.workspaces
      .list()
      .then((list) => {
        reconcileRememberedWorkspace(list.map((w) => w.id));
        if (mounted) setReconciled((n) => n + 1);
      })
      .catch(() => {
        /* service unreachable: keep what is remembered until it can be checked */
      });
    return () => {
      mounted = false;
    };
  }, []);
  const navGroups = buildNavGroups(`/reviews/${encodeURIComponent(urlWorkspace ?? getRememberedWorkspaceId())}`);
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

  const statusLabel = backendStatus === "ready" ? "Connected" : backendStatus === "checking" ? "Connecting" : "Offline";
  const statusDot =
    backendStatus === "ready" ? "bg-emerald-400" : backendStatus === "checking" ? "bg-amber-400 animate-pulse" : "bg-rose-400";

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border-subtle)] bg-[var(--bg-base)]/80 backdrop-blur-xl">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap lg:flex-nowrap items-center gap-x-8">
        <Link to="/" className="flex items-center gap-2.5 h-16 shrink-0" aria-label="Evidra home">
          <span className="font-serif text-[1.35rem] font-medium tracking-tight text-[var(--text-primary)]">Evidra</span>
        </Link>

        <nav
          className="order-last lg:order-none w-full lg:w-auto lg:flex-1 min-w-0 -mx-1 lg:mx-0 overflow-x-auto no-scrollbar border-t border-[var(--border-subtle)] lg:border-0"
          aria-label="Main navigation"
        >
          <ul className="flex items-center h-11 lg:h-16 whitespace-nowrap">
            {navGroups.map((group, gi) => (
              <React.Fragment key={gi}>
                {gi > 0 && <li aria-hidden="true" className="mx-2 h-4 w-px bg-[var(--border-silver)] shrink-0" />}
                {group.map((link) => {
                  const isActive =
                    location.pathname === link.to ||
                    (link.label === "Query" && /\/(search|setup)$/.test(location.pathname));
                  return (
                    <li key={link.to} className="h-full">
                      <Link
                        to={link.to}
                        title={link.title}
                        aria-current={isActive ? "page" : undefined}
                        className={`relative flex items-center h-full px-2.5 text-[13px] font-medium ${
                          isActive
                            ? "text-[var(--text-primary)]"
                            : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                        }`}
                      >
                        {link.label}
                        {isActive && (
                          <span className="absolute left-2.5 right-2.5 bottom-0 h-0.5 rounded-full bg-[var(--accent-gold)]" />
                        )}
                      </Link>
                    </li>
                  );
                })}
              </React.Fragment>
            ))}
          </ul>
        </nav>

        <div className="ml-auto lg:ml-0 flex items-center gap-4 h-16 shrink-0">
          <span
            className="hidden sm:inline-flex items-center gap-2 text-xs text-[var(--text-muted)]"
            title={`Backend service: ${backendStatus}`}
            role="status"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${statusDot}`} />
            {statusLabel}
          </span>
          {authRequired && (
            <button
              type="button"
              onClick={() => void signOut()}
              aria-label="Sign out"
              title="Sign out"
              className="grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-silver)] text-[var(--text-secondary)] hover:text-[var(--accent-gold)] hover:border-[var(--border-gold)]"
            >
              <LogOut className="w-4 h-4" strokeWidth={1.75} />
            </button>
          )}
          <button
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className="grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-silver)] text-[var(--text-secondary)] hover:text-[var(--accent-gold)] hover:border-[var(--border-gold)]"
          >
            {theme === "dark" ? <Sun className="w-4 h-4" strokeWidth={1.75} /> : <Moon className="w-4 h-4" strokeWidth={1.75} />}
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
