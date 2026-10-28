import React, { Suspense, lazy } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Database, GitCompare, FileCheck2 } from "lucide-react";
import { HeroStatic } from "./HeroStatic";
import { ReviewWalkthrough } from "./ReviewWalkthrough";

// Lazy-load the heavy 3D scene to keep initial bundle load instantaneous
const EvidenceScene3D = lazy(() => import("./EvidenceScene3D"));

const WS = "/reviews/ws-synth-001";

const facts = [
  { title: "Runs fully offline", detail: "Level 1 needs no LLM or GPU" },
  { title: "Exact evidence spans", detail: "Half-open Unicode code points" },
  { title: "Nothing is overwritten", detail: "Append-only snapshot history" },
];


const pillars = [
  {
    icon: Database,
    title: "Multi-source ingestion",
    text: "Queries are translated for each source with synonym control, pagination limits and a visible count before anything is imported.",
    sampleLabel: "Query",
    sample: 'metformin[Title] AND "type 2 diabetes"',
  },
  {
    icon: GitCompare,
    title: "Same study is not the same paper",
    text: "Grouping obeys cannot-link rules, so a trial protocol and its primary results stay separate records under one study.",
    sampleLabel: "Candidate pair",
    sample: "10.1056/nejmoa2024001 · PubMed ~ PMC",
  },
  {
    icon: FileCheck2,
    title: "Exact-span PICO tagging",
    text: "Every highlighted span is stored as code-point offsets and checked against a hash of the abstract it came from.",
    sampleLabel: "Population span [12, 45)",
    sample: '"adults with type 2 diabetes"',
  },
];

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-28 pb-8">
      {/* Hero */}
      <section className="relative pt-6 sm:pt-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-10 items-center">
          <div className="lg:col-span-7 space-y-8">
            <h1 className="text-[2.6rem] sm:text-6xl lg:text-[4.1rem] text-[var(--text-primary)] max-w-[15ch]">
              Every inclusion, traced to the sentence that justified it.
            </h1>

            <p className="text-[var(--text-secondary)] text-base sm:text-lg max-w-[58ch] leading-relaxed">
              Evidra pulls records from PubMed and Europe PMC, separates true duplicates from related reports and screens
              them with deterministic rules. Each decision stays tied to the exact abstract span and the reviewer who made it.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <Link to="/reviews" className="btn-gold">
                Open workspaces
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to={`${WS}/records`} className="btn-ghost">
                Go to screening queue
              </Link>
            </div>

            <dl className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-8 border-t border-[var(--border-subtle)]">
              {facts.map((f) => (
                <div key={f.title} className="space-y-1">
                  <dt className="text-sm font-semibold text-[var(--text-primary)]">{f.title}</dt>
                  <dd className="text-sm text-[var(--text-muted)]">{f.detail}</dd>
                </div>
              ))}
            </dl>
          </div>

          <figure className="lg:col-span-5 space-y-3">
            <div className="glass-panel-luxury p-1.5 overflow-hidden">
              <Suspense fallback={<HeroStatic />}>
                <EvidenceScene3D />
              </Suspense>
            </div>
            <figcaption className="flex items-center justify-between px-1 text-xs text-[var(--text-muted)]">
              <span className="inline-flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-gold)]" />
                Evidence lens with live PICO beacons
              </span>
              <span>Scroll to orbit</span>
            </figcaption>
          </figure>
        </div>
      </section>

      {/* Workflow sequence */}
      <section aria-labelledby="workflow-heading" className="space-y-10">
        <div className="max-w-2xl space-y-3">
          <h2 id="workflow-heading" className="text-3xl sm:text-4xl text-[var(--text-primary)]">
            How a review moves through Evidra
          </h2>
          <p className="text-[var(--text-secondary)]">
            Follow five records from a single query to a locked snapshot. Press play, or pick a stage to see what Evidra does
            and why.
          </p>
        </div>

        <ReviewWalkthrough />
      </section>

      {/* Pillars */}
      <section aria-labelledby="pillars-heading" className="space-y-10">
        <div className="max-w-2xl space-y-3">
          <h2 id="pillars-heading" className="text-3xl sm:text-4xl text-[var(--text-primary)]">
            Built for reviews that have to stand up to scrutiny
          </h2>
          <p className="text-[var(--text-secondary)]">
            Decisions, extracted spans and duplicate resolutions are written once and never silently changed.
          </p>
        </div>

        <div className="glass-panel grid grid-cols-1 md:grid-cols-3 md:divide-x divide-y md:divide-y-0 divide-[var(--border-subtle)] overflow-hidden">
          {pillars.map(({ icon: Icon, title, text, sampleLabel, sample }) => (
            <article key={title} className="flex flex-col justify-between gap-8 p-7 sm:p-8">
              <div className="space-y-4">
                <Icon className="w-6 h-6 text-[var(--accent-gold)]" strokeWidth={1.5} />
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h3>
                <p className="text-sm leading-relaxed text-[var(--text-muted)]">{text}</p>
              </div>
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)]/60 px-4 py-3 space-y-1">
                <p className="text-xs text-[var(--text-muted)]">{sampleLabel}</p>
                <p className="font-mono text-[13px] text-[var(--accent-steel)] truncate">{sample}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Call to action */}
      <section className="glass-panel-luxury px-8 py-10 sm:px-12 sm:py-12">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
          <div className="space-y-3 max-w-2xl">
            <h2 className="text-3xl text-[var(--text-primary)]">Try it on the synthetic benchmark review</h2>
            <p className="text-[var(--text-secondary)]">
              Override a duplicate, exclude a record with a reason, resolve a conflict and export the included studies as CSV.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 shrink-0">
            <Link to={`${WS}/records`} className="btn-gold">
              Open the review queue
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to={`${WS}/duplicates`} className="btn-ghost">
              Inspect duplicate pairs
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
