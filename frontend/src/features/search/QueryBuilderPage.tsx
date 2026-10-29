import React, { useEffect, useRef, useState } from "react";
import { useLocation, useParams, Link } from "react-router-dom";
import { ArrowRight, Check, CheckCircle2, Clock, Sparkles } from "lucide-react";
import { CriteriaEditor } from "../review-setup/CriteriaEditor";
import { QueryBuilder } from "./QueryBuilder";
import { ImportWorkflow } from "../runs/ImportWorkflow";
import { ErrorState, LoadingRegion, SkeletonCard } from "../../components/Feedback";
import { selectedIds } from "./executions";
import { termsFromPico } from "./searchTerms";
import { loadSetupData, type SetupData } from "./setupData";
import type { CriteriaVersionResponse, JobResponse, QueryVersionResponse } from "../../api/client";

type StepKey = "question" | "search" | "import" | "screen";

const STEPS: Array<{ key: StepKey; label: string; hint: string }> = [
  { key: "question", label: "Review question", hint: "Question, PICO and screening rules" },
  { key: "search", label: "Search", hint: "Build the query and pick results" },
  { key: "import", label: "Import", hint: "Bring the chosen records in" },
  { key: "screen", label: "Screen", hint: "Decide on each paper" },
];

type LoadState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; data: SetupData };

export const QueryBuilderPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const workspaceId = id ?? "";
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let mounted = true;
    setLoad({ status: "loading" });
    loadSetupData(workspaceId)
      .then((data) => {
        if (mounted) setLoad({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (mounted) setLoad({ status: "error", error });
      });
    return () => {
      mounted = false;
    };
  }, [workspaceId, reloadKey]);

  if (load.status === "loading") {
    return (
      <div className="space-y-6 pb-16">
        <h1 className="text-xl font-bold text-white">Set up the review</h1>
        <LoadingRegion label="Loading your review">
          <SkeletonCard lines={3} />
        </LoadingRegion>
      </div>
    );
  }
  if (load.status === "error") {
    return (
      <div className="space-y-6 pb-16">
        <h1 className="text-xl font-bold text-white">Set up the review</h1>
        <ErrorState error={load.error} what="Your review setup" onRetry={() => setReloadKey((n) => n + 1)} />
      </div>
    );
  }
  return <SetupView key={`${workspaceId}:${reloadKey}`} workspaceId={workspaceId} data={load.data} />;
};

const SetupView: React.FC<{ workspaceId: string; data: SetupData }> = ({ workspaceId, data }) => {
  const location = useLocation();
  const createdTitle = (location.state as { createdTitle?: string } | null)?.createdTitle;
  const { workspace } = data;

  // Starts as the server has it, then follows what is saved from here
  const [criteriaVersion, setCriteriaVersion] = useState<CriteriaVersionResponse | null>(data.criteria);
  const [activeQuery, setActiveQuery] = useState<QueryVersionResponse | null>(data.query);
  const [selectedExecIds, setSelectedExecIds] = useState<string[]>(() => selectedIds(data.executions));
  const [importJob, setImportJob] = useState<JobResponse | null>(data.importJob);

  const doneBannerRef = useRef<HTMLDivElement>(null);
  const sectionRefs = {
    question: useRef<HTMLElement>(null),
    search: useRef<HTMLElement>(null),
    import: useRef<HTMLElement>(null),
  };

  const goTo = (key: keyof typeof sectionRefs) => {
    const el = sectionRefs[key].current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    el.focus({ preventScroll: true });
  };

  const importSucceeded = importJob?.state === "succeeded";
  const done: Record<StepKey, boolean> = {
    question: !!criteriaVersion,
    search: !!activeQuery && selectedExecIds.length > 0,
    import: importSucceeded,
    screen: false,
  };
  const current: StepKey = !done.question ? "question" : !done.search ? "search" : !done.import ? "import" : "screen";

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <div className="border-b border-slate-800 pb-5 flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1.5">
          <h1 className="text-xl font-bold text-white">Set up the review</h1>
          <p className="text-slate-400 text-sm max-w-[70ch]">
            {workspace ? (
              <>
                <span className="text-slate-200 font-medium">{workspace.title}</span> · write the question, search the
                sources, then import what you want to screen.
              </>
            ) : (
              <>Write the question, search the sources, then import what you want to screen.</>
            )}
          </p>
        </div>

        <Link
          to={`/reviews/${workspaceId}/search-evolution`}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition border border-slate-700"
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Search history</span>
        </Link>
      </div>

      {createdTitle && !criteriaVersion && (
        <div role="status" className="p-4 rounded-xl border border-emerald-800/70 bg-emerald-950/50 flex items-start gap-3">
          <Sparkles className="w-4 h-4 mt-0.5 text-emerald-400 shrink-0" />
          <p className="text-sm text-emerald-200">
            Created <span className="font-semibold">“{createdTitle}”</span>. Start with the review question below, then
            save it to move on to the search.
          </p>
        </div>
      )}

      {/* Progress through setup */}
      <nav aria-label="Setup steps" className="glass-panel p-2">
        <ol className="grid grid-cols-2 lg:grid-cols-4 gap-1">
          {STEPS.map((step, i) => {
            const isDone = done[step.key];
            const isCurrent = current === step.key;
            const content = (
              <>
                <span
                  className={`grid place-items-center w-7 h-7 shrink-0 rounded-full border text-xs font-semibold ${
                    isDone
                      ? "border-emerald-500/60 bg-emerald-500/15 text-emerald-300"
                      : isCurrent
                        ? "border-[var(--border-gold)] text-[var(--accent-gold)]"
                        : "border-[var(--border-silver)] text-[var(--text-muted)]"
                  }`}
                >
                  {isDone ? <Check className="w-3.5 h-3.5" /> : i + 1}
                </span>
                <span className="min-w-0">
                  <span className={`block text-sm font-semibold ${isCurrent ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}>
                    {step.label}
                  </span>
                  <span className="block text-xs text-[var(--text-muted)] truncate">{step.hint}</span>
                </span>
              </>
            );
            const cls = `flex items-center gap-3 rounded-xl px-3 py-2.5 text-left w-full ${
              isCurrent ? "bg-[var(--gold-glow)] ring-1 ring-[var(--border-gold)]" : "hover:bg-[var(--bg-raised)]"
            }`;
            return (
              <li key={step.key}>
                {step.key === "screen" ? (
                  <Link to={`/reviews/${workspaceId}/records`} className={cls} aria-current={isCurrent ? "step" : undefined}>
                    {content}
                  </Link>
                ) : (
                  <button type="button" onClick={() => goTo(step.key as keyof typeof sectionRefs)} className={cls} aria-current={isCurrent ? "step" : undefined}>
                    {content}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      {importSucceeded && importJob && (
        <div ref={doneBannerRef} tabIndex={-1} role="status" className="scroll-mt-24 outline-none p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-xl flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <h2 className="text-sm font-semibold text-white">Import finished</h2>
              <p className="text-xs text-slate-300">
                {importJob.processed_items ?? 0} records were imported into this review. They are screened automatically;
                open screening to follow progress.
              </p>
            </div>
          </div>
          <Link to={`/reviews/${workspaceId}/records`} className="btn-gold">
            Go to screening
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* 1. Review question & criteria */}
      <section ref={sectionRefs.question} tabIndex={-1} aria-label="Step 1: review question" className="scroll-mt-24 outline-none">
        <CriteriaEditor
          key={workspaceId}
          workspaceId={workspaceId}
          savedCriteria={data.criteria}
          defaultQuestion={workspace?.title}
          onCriteriaSaved={(crit) => {
            setCriteriaVersion(crit);
            window.setTimeout(() => goTo("search"), 450);
          }}
        />
      </section>

      {/* 2. Boolean query & provider counts */}
      <section ref={sectionRefs.search} tabIndex={-1} aria-label="Step 2: search" className="scroll-mt-24 outline-none space-y-3">
        <QueryBuilder
          // A review with no saved search restarts from its PICO terms once, when the question is first saved
          key={data.query?.id ?? (criteriaVersion ? "new-with-question" : "new-no-question")}
          workspaceId={workspaceId}
          criteriaVersionId={criteriaVersion?.id ?? null}
          savedQuery={data.query}
          savedExecutions={data.executions}
          initialTerms={termsFromPico(criteriaVersion)}
          onQuerySaved={(q) => setActiveQuery(q)}
          onExecutionSelected={(ids) => {
            if (ids.length > 0 && selectedExecIds.length === 0) window.setTimeout(() => goTo("import"), 450);
            setSelectedExecIds(ids);
          }}
        />
      </section>

      {/* 3. Approved record ingestion */}
      <section ref={sectionRefs.import} tabIndex={-1} aria-label="Step 3: import" className="scroll-mt-24 outline-none">
        <ImportWorkflow
          workspaceId={workspaceId}
          selectedExecutionIds={selectedExecIds}
          initialJob={data.importJob}
          onJobChange={setImportJob}
          onImportComplete={() => {
            window.setTimeout(() => {
              const el = doneBannerRef.current;
              if (!el) return;
              const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
              el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
              el.focus({ preventScroll: true });
            }, 450);
          }}
        />
      </section>
    </div>
  );
};
