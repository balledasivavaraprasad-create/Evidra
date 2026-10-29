import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { LogOut, Sun, Moon } from "lucide-react";
import { api } from "../api/client";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import { getRememberedWorkspaceId, reconcileRememberedWorkspace, workspaceIdFromPath } from "../context/currentWorkspace";

type NavLink = { to: string; label: string; title: string };

const reviewLinks = (ws: string): NavLink[] => [
  { to: `${ws}/setup`, label: "Query", title: "Review question, search and import" },
  { to: `${ws}/records`, label: "Screening", title: "Screening queue" },
  { to: `${ws}/ml-ranking`, label: "ML ranking", title: "ML prioritization" },
  { to: `${ws}/duplicates`, label: "Duplicates", title: "Deduplication" },
  { to: `${ws}/history`, label: "Lineage", title: "Audit lineage" },
  { to: `${ws}/radar`, label: "PICO radar", title: "Missing-evidence radar" },
  { to: `${ws}/devils-advocate`, label: "Devil's advocate", title: "Devil's advocate reviewer" },
  { to: `${ws}/prisma`, label: "PRISMA", title: "PRISMA 2020 flow & reporting" },
  { to: `${ws}/search-evolution`, label: "Evolution", title: "Search evolution" },
];

const iconButton =
  "grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-silver)] text-[var(--text-secondary)] hover:text-[var(--accent-gold)] hover:border-[var(--border-gold)]";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase() || "?";
}

export const Header: React.FC = () => {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { status, user, authRequired, signOut } = useAuth();
  const signedIn = status === "signed-in";

  // Menu links follow the review in the URL, else the last one opened (if it's still yours)
  const urlWorkspace = workspaceIdFromPath(location.pathname);
  const [remembered, setRemembered] = useState<string | null>(() => getRememberedWorkspaceId());
  useEffect(() => {
    if (!signedIn) return;
    let mounted = true;
    api.workspaces
      .list()
      .then((list) => {
        if (mounted) setRemembered(reconcileRememberedWorkspace(list.map((w) => w.id)));
      })
      .catch(() => {
        /* service unreachable: keep what is remembered until it can be checked */
      });
    return () => {
      mounted = false;
    };
  }, [signedIn, user?.id]);
  useEffect(() => {
    if (urlWorkspace) setRemembered(urlWorkspace);
  }, [urlWorkspace]);

  const currentReview = urlWorkspace ?? remembered;
  const navGroups: NavLink[][] = signedIn
    ? [
        [{ to: "/dashboard", label: "Dashboard", title: "Your reviews" }],
        ...(currentReview ? [reviewLinks(`/reviews/${encodeURIComponent(currentReview)}`)] : []),
      ]
    : [];

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border-subtle)] bg-[var(--bg-base)]/80 backdrop-blur-xl">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap lg:flex-nowrap items-center gap-x-8">
        <Link to={signedIn ? "/dashboard" : "/"} className="flex items-center gap-2.5 h-16 shrink-0" aria-label="Evidra home">
          <span className="font-serif text-[1.35rem] font-medium tracking-tight text-[var(--text-primary)]">Evidra</span>
        </Link>

        {navGroups.length > 0 && (
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
                      (link.label === "Query" && /\/(search|setup)$/.test(location.pathname) && location.pathname.startsWith(link.to.replace(/\/setup$/, "")));
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
        )}

        <div className="ml-auto lg:ml-0 flex items-center gap-3 h-16 shrink-0">
          {signedIn && user && (
            <span className="hidden sm:flex items-center gap-2 text-xs text-[var(--text-secondary)]" title={user.email}>
              <span
                aria-hidden="true"
                className="grid place-items-center w-8 h-8 rounded-full border border-[var(--border-gold)] bg-[var(--gold-glow)] text-[11px] font-semibold text-[var(--accent-gold)]"
              >
                {initials(user.name)}
              </span>
              <span className="max-w-[9rem] truncate">{user.name}</span>
            </span>
          )}
          {signedIn && authRequired && (
            <button type="button" onClick={() => void signOut()} aria-label="Sign out" title="Sign out" className={iconButton}>
              <LogOut className="w-4 h-4" strokeWidth={1.75} />
            </button>
          )}
          {!signedIn && (
            <>
              <Link to="/signin" className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
                Sign in
              </Link>
              <Link to="/signup" className="btn-ink !py-2 !px-3.5 text-sm">
                Create account
              </Link>
            </>
          )}
          <button
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className={iconButton}
          >
            {theme === "dark" ? <Sun className="w-4 h-4" strokeWidth={1.75} /> : <Moon className="w-4 h-4" strokeWidth={1.75} />}
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
