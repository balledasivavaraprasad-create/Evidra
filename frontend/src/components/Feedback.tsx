import React, { useState } from "react";
import { AlertTriangle, Check, Copy, PlugZap, RotateCcw, SearchX, ServerCrash } from "lucide-react";
import { ApiError, FRIENDLY_ERRORS, isServiceUnreachable } from "../api/client";

/* ------------------------------------------------------------------ */
/* Error classification                                               */
/* ------------------------------------------------------------------ */

export type ErrorKind = "unreachable" | "server" | "notFound" | "other";

export function errorKind(err: unknown): ErrorKind {
  if (isServiceUnreachable(err)) return "unreachable";
  if (err instanceof ApiError) {
    if (err.status === 404) return "notFound";
    if (err.status >= 500) return "server";
  }
  // Strings handed down from older components: recognise the old raw texts too
  if (typeof err === "string") {
    if (err === FRIENDLY_ERRORS.unreachable || /bad gateway|failed to fetch|network/i.test(err)) return "unreachable";
    if (err === FRIENDLY_ERRORS.server || /internal server error/i.test(err)) return "server";
  }
  return "other";
}

function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") {
    const kind = errorKind(err);
    if (kind === "unreachable") return FRIENDLY_ERRORS.unreachable;
    if (kind === "server") return FRIENDLY_ERRORS.server;
    return err;
  }
  return "Something went wrong while loading this.";
}

const TITLES: Record<ErrorKind, string> = {
  unreachable: "The review service isn't running",
  server: "This section couldn't load",
  notFound: "Nothing found here",
  other: "This section couldn't load",
};

const ICONS: Record<ErrorKind, React.ElementType> = {
  unreachable: PlugZap,
  server: ServerCrash,
  notFound: SearchX,
  other: AlertTriangle,
};

export const BACKEND_START_COMMANDS = [
  "cd backend",
  "uv run --locked alembic upgrade head",
  "uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8800",
];

/* ------------------------------------------------------------------ */
/* Start-the-backend instructions                                     */
/* ------------------------------------------------------------------ */

export const StartBackendSteps: React.FC<{ className?: string }> = ({ className = "" }) => {
  const [copied, setCopied] = useState(false);
  const text = BACKEND_START_COMMANDS.join("\n");
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard unavailable: the commands stay visible to copy by hand */
    }
  };
  return (
    <div className={`text-left ${className}`}>
      <div className="flex items-center justify-between gap-3 mb-1.5">
        <p className="text-xs text-[var(--text-muted)]">In a terminal at the project folder, run:</p>
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-1 text-xs text-[var(--text-secondary)] hover:text-[var(--accent-gold)]"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="font-mono text-[12.5px] leading-relaxed rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)]/70 px-3.5 py-2.5 overflow-x-auto text-[var(--accent-steel)]">
        {text}
      </pre>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* ErrorState: replaces bare "Bad Gateway" / "Internal Server Error"  */
/* ------------------------------------------------------------------ */

type ErrorStateProps = {
  error: unknown;
  onRetry?: () => void;
  /** Overrides the default title, e.g. "Duplicate history couldn't load" */
  title?: string;
  /** What this section would show, used in the default message for clarity */
  what?: string;
  compact?: boolean;
  className?: string;
};

export const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry, title, what, compact = false, className = "" }) => {
  const kind = errorKind(error);
  const Icon = ICONS[kind];
  const heading = title ?? (kind === "server" && what ? `${what} couldn't load` : TITLES[kind]);
  const message = errorMessage(error);
  const tone =
    kind === "unreachable"
      ? "border-amber-500/30 bg-amber-500/5"
      : kind === "notFound"
        ? "border-[var(--border-silver)] bg-[var(--bg-card)]"
        : "border-rose-500/30 bg-rose-500/5";
  const iconTone = kind === "unreachable" ? "text-amber-400" : kind === "notFound" ? "text-slate-400" : "text-rose-400";

  if (compact) {
    return (
      <div role="alert" className={`flex items-start gap-3 rounded-xl border p-4 ${tone} ${className}`}>
        <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${iconTone}`} strokeWidth={1.75} />
        <div className="flex-1 min-w-0 space-y-1">
          <p className="text-sm font-semibold text-[var(--text-primary)]">{heading}</p>
          <p className="text-sm text-[var(--text-secondary)]">{message}</p>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 shrink-0 rounded-lg border border-[var(--border-silver)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:border-[var(--border-gold)]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Try again
          </button>
        )}
      </div>
    );
  }

  return (
    <div role="alert" className={`rounded-2xl border px-6 py-10 sm:px-10 ${tone} ${className}`}>
      <div className="mx-auto max-w-xl text-center space-y-4">
        <span className="mx-auto grid place-items-center w-12 h-12 rounded-xl border border-[var(--border-silver)] bg-[var(--bg-surface)]">
          <Icon className={`w-5 h-5 ${iconTone}`} strokeWidth={1.75} />
        </span>
        <div className="space-y-1.5">
          <h2 className="font-serif text-2xl text-[var(--text-primary)]">{heading}</h2>
          <p className="text-sm text-[var(--text-secondary)]">{message}</p>
        </div>
        {kind === "unreachable" && <StartBackendSteps className="pt-1" />}
        {onRetry && (
          <button type="button" onClick={onRetry} className="btn-ghost mx-auto">
            <RotateCcw className="w-4 h-4" />
            Try again
          </button>
        )}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* SampleDataNotice: honest banner when a page falls back to demo data */
/* ------------------------------------------------------------------ */

export const SampleDataNotice: React.FC<{ onRetry?: () => void; className?: string }> = ({ onRetry, className = "" }) => {
  const [open, setOpen] = useState(false);
  return (
    <div role="status" className={`rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 ${className}`}>
      <div className="flex flex-wrap items-start gap-3">
        <PlugZap className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" strokeWidth={1.75} />
        <div className="flex-1 min-w-[16rem] space-y-1">
          <p className="text-sm font-semibold text-[var(--text-primary)]">You're looking at sample records</p>
          <p className="text-sm text-[var(--text-secondary)]">
            The review service isn't running, so this page shows built-in examples. Decisions you make here won't be saved.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--accent-gold)]"
          >
            {open ? "Hide steps" : "How to start it"}
          </button>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-silver)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:border-[var(--border-gold)]"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reconnect
            </button>
          )}
        </div>
      </div>
      {open && <StartBackendSteps className="mt-3 sm:ml-7" />}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Skeletons                                                          */
/* ------------------------------------------------------------------ */

export const Skeleton: React.FC<{ className?: string; style?: React.CSSProperties }> = ({ className = "", style }) => (
  <span aria-hidden="true" style={style} className={`skeleton block rounded-md ${className}`} />
);

export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({ lines = 3, className = "" }) => (
  <span aria-hidden="true" className={`block space-y-2 ${className}`}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} className="h-3" style={{ width: i === lines - 1 ? "62%" : `${92 - i * 6}%` }} />
    ))}
  </span>
);

/** Wrapper that announces loading to screen readers once, while skeleton shapes stay silent. */
export const LoadingRegion: React.FC<{ label: string; children: React.ReactNode; className?: string }> = ({
  label,
  children,
  className = "",
}) => (
  <div role="status" aria-live="polite" aria-busy="true" className={className}>
    <span className="sr-only">{label}</span>
    {children}
  </div>
);

export const SkeletonCard: React.FC<{ className?: string; lines?: number }> = ({ className = "", lines = 2 }) => (
  <div className={`glass-panel p-5 space-y-4 ${className}`}>
    <div className="flex items-center justify-between gap-4">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-4 w-14" />
    </div>
    <SkeletonText lines={lines} />
  </div>
);

export const SkeletonStatRow: React.FC<{ count?: number }> = ({ count = 4 }) => (
  <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(auto-fit, minmax(160px, 1fr))` }}>
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="glass-panel p-4 space-y-3">
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-6 w-1/3" />
      </div>
    ))}
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number; cols?: number }> = ({ rows = 4, cols = 5 }) => (
  <div className="glass-panel overflow-hidden">
    <div className="grid gap-4 px-5 py-3 border-b border-[var(--border-subtle)]" style={{ gridTemplateColumns: `2fr repeat(${cols - 1}, 1fr)` }}>
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className="h-3 w-2/3" />
      ))}
    </div>
    {Array.from({ length: rows }).map((_, r) => (
      <div key={r} className="grid gap-4 px-5 py-4 border-b last:border-0 border-[var(--border-subtle)]" style={{ gridTemplateColumns: `2fr repeat(${cols - 1}, 1fr)` }}>
        <SkeletonText lines={2} />
        {Array.from({ length: cols - 1 }).map((_, c) => (
          <Skeleton key={c} className="h-3 w-3/4 self-center" />
        ))}
      </div>
    ))}
  </div>
);

/** List on the left, reader on the right: screening and ML ranking pages */
export const SkeletonListDetail: React.FC = () => (
  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
    <div className="lg:col-span-4 space-y-3">
      <Skeleton className="h-3 w-32" />
      {[0, 1, 2].map((i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
    <div className="lg:col-span-8 glass-panel p-6 space-y-6">
      <div className="flex gap-2">
        {[0, 1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-8 w-20 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-6 w-4/5" />
      <Skeleton className="h-3 w-1/3" />
      <div className="rounded-xl border border-[var(--border-subtle)] p-5">
        <SkeletonText lines={4} />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-9 w-28 rounded-lg" />
        <Skeleton className="h-9 w-36 rounded-lg" />
        <Skeleton className="h-9 w-20 rounded-lg" />
      </div>
    </div>
  </div>
);

/** Vertical timeline: lineage / snapshot history */
export const SkeletonTimeline: React.FC<{ items?: number }> = ({ items = 2 }) => (
  <div className="space-y-4">
    {Array.from({ length: items }).map((_, i) => (
      <div key={i} className="glass-panel p-6 space-y-5">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-xl" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="h-3 w-28" />
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((c) => (
            <div key={c} className="rounded-xl border border-[var(--border-subtle)] p-4 space-y-2">
              <Skeleton className="h-3 w-2/3" />
              <Skeleton className="h-5 w-1/4" />
            </div>
          ))}
        </div>
      </div>
    ))}
  </div>
);
