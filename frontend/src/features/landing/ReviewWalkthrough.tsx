import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  FileCheck2,
  GitCompare,
  Info,
  ListChecks,
  Lock,
  Pause,
  Play,
  RotateCcw,
  Search,
} from "lucide-react";

/**
 * Interactive walkthrough of one review moving through Evidra.
 * Left: a live flow graph of five records from query to locked snapshot.
 * Right: what happens at the current stage, with the real values involved.
 * Uses the synthetic benchmark review (metformin vs placebo, type 2 diabetes).
 */

const WS = "/reviews/ws-synth-001";
const STEP_MS = 7000;

type StepId = "search" | "dedup" | "screen" | "pico" | "audit";

type Step = {
  id: StepId;
  label: string;
  icon: React.ElementType;
  title: string;
  fieldLabel: string;
  field: string;
  body: string;
  stats: Array<{ value: string; label: string }>;
  why: string;
  link: { to: string; label: string };
};

const STEPS: Step[] = [
  {
    id: "search",
    label: "Search",
    icon: Search,
    title: "One query, two sources, five records",
    fieldLabel: "Query version 1",
    field: 'metformin[Title] AND "type 2 diabetes"',
    body:
      "The Boolean query is translated for PubMed and Europe PMC. Evidra shows each provider's count first and imports only what you approve, keeping every raw source record.",
    stats: [
      { value: "2", label: "sources" },
      { value: "5", label: "records imported" },
    ],
    why: "Query versions are immutable, so you can always show exactly what was searched and when.",
    link: { to: `${WS}/search`, label: "Open the query builder" },
  },
  {
    id: "dedup",
    label: "Deduplicate",
    icon: GitCompare,
    title: "Same paper merged, same study kept apart",
    fieldLabel: "Matched on DOI",
    field: "10.1001/dc.2023.01 · PubMed 38100001 ~ Europe PMC",
    body:
      "The PubMed record and its Europe PMC copy are the same publication, so they become one paper. The trial protocol belongs to the same study but is a different paper, so a cannot-link rule keeps it separate.",
    stats: [
      { value: "5 → 4", label: "papers" },
      { value: "1", label: "cannot-link kept" },
    ],
    why: "Merging a protocol into its results paper would silently hide evidence. Evidra never deletes a duplicate; it groups it.",
    link: { to: `${WS}/duplicates`, label: "Inspect duplicate pairs" },
  },
  {
    id: "screen",
    label: "Screen",
    icon: ListChecks,
    title: "Rules suggest, a reviewer decides",
    fieldLabel: "Exclusion recorded",
    field: "Rat study · reason: animal-only preclinical study",
    body:
      "Screening rules from the protocol propose a decision for each paper. The reviewer confirms it. An exclusion cannot be saved without a reason, and uncertain evidence becomes Maybe rather than a guess.",
    stats: [
      { value: "1", label: "include" },
      { value: "1", label: "maybe" },
      { value: "2", label: "exclude" },
    ],
    why: "Machine output stays a suggestion. Every human decision is attributed and appended, never overwritten.",
    link: { to: `${WS}/records`, label: "Open the screening queue" },
  },
  {
    id: "pico",
    label: "Extract PICO",
    icon: FileCheck2,
    title: "Evidence tagged to the exact characters",
    fieldLabel: "Population span, code points [53, 80)",
    field: '"adults with type 2 diabetes"',
    body:
      "Population, intervention, comparator and outcome are highlighted in the saved abstract of the included trial. Each span is stored as half-open Unicode offsets and checked against a hash of that text.",
    stats: [
      { value: "4 / 4", label: "PICO elements found" },
      { value: "0", label: "stale spans" },
    ],
    why: "If the abstract text ever changes, the hash no longer matches and the span is flagged instead of drifting.",
    link: { to: `${WS}/radar`, label: "Open the PICO radar" },
  },
  {
    id: "audit",
    label: "Audit",
    icon: Lock,
    title: "Everything locked into a snapshot",
    fieldLabel: "Active revision",
    field: "b0398022 · fingerprint 2d6c8748…acd27",
    body:
      "The query, groupings, decisions and spans are written into an append-only snapshot. Restoring an older revision reads that saved snapshot exactly; nothing is re-fetched or re-run with today's methods.",
    stats: [
      { value: "1", label: "snapshot" },
      { value: "100%", label: "reproducible" },
    ],
    why: "Reviewers and auditors can see what the review looked like on any date, and why each record ended up where it did.",
    link: { to: `${WS}/history`, label: "Open audit lineage" },
  },
];

/* ---------- Flow graph ---------- */

type Tone = "gold" | "steel" | "sage" | "garnet" | "amber" | "muted";

const toneStroke: Record<Tone, string> = {
  gold: "var(--accent-gold)",
  steel: "var(--accent-steel)",
  sage: "var(--status-include)",
  garnet: "var(--status-exclude)",
  amber: "var(--status-maybe)",
  muted: "var(--border-silver)",
};

const X = { query: 62, source: 182, record: 330, state: 492, pico: 620 };
const ROW = { r1: 62, r2: 146, r4: 230, r3: 314, r5: 398 };
const MERGED_Y = (ROW.r1 + ROW.r2) / 2;

const records = [
  { id: "r1", y: ROW.r1, label: "PubMed 38100001", sub: "RCT, 2023", from: "pm" },
  { id: "r2", y: ROW.r2, label: "Europe PMC copy", sub: "same DOI", from: "ep" },
  { id: "r4", y: ROW.r4, label: "Trial protocol", sub: "same trial, 2021", from: "pm" },
  { id: "r3", y: ROW.r3, label: "Rat study", sub: "PubMed 38100003", from: "pm" },
  { id: "r5", y: ROW.r5, label: "Prediabetes cohort", sub: "PubMed 38100010", from: "ep" },
] as const;

const sources = { pm: { y: 150, label: "PubMed" }, ep: { y: 310, label: "Europe PMC" } };

const curve = (x1: number, y1: number, x2: number, y2: number) => {
  const mx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
};

type StateNode = { key: string; y: number; label: string; sub?: string; tone: Tone; dashed?: boolean };

const stateNodesFor = (step: number): StateNode[] => {
  if (step === 1)
    return [
      { key: "a", y: MERGED_Y, label: "Paper A", sub: "2 records merged", tone: "gold" },
      { key: "b", y: ROW.r4, label: "Paper B", sub: "same study as A", tone: "steel", dashed: true },
      { key: "c", y: ROW.r3, label: "Paper C", sub: "distinct", tone: "muted" },
      { key: "d", y: ROW.r5, label: "Paper D", sub: "distinct", tone: "muted" },
    ];
  if (step >= 2)
    return [
      { key: "a", y: MERGED_Y, label: "Include", sub: "meets all criteria", tone: "sage" },
      { key: "b", y: ROW.r4, label: "Maybe", sub: "no results yet", tone: "amber" },
      { key: "c", y: ROW.r3, label: "Exclude", sub: "animal-only", tone: "garnet" },
      { key: "d", y: ROW.r5, label: "Exclude", sub: "prediabetes", tone: "garnet" },
    ];
  return [];
};

const picoChips = [
  { k: "P", text: "adults, T2D", y: 26, color: "var(--pico-p)" },
  { k: "I", text: "oral metformin", y: 70, color: "var(--pico-i)" },
  { k: "C", text: "placebo", y: 114, color: "var(--pico-c)" },
  { k: "O", text: "HbA1c", y: 158, color: "var(--pico-o)" },
];

const FlowDot: React.FC<{ path: string; delay: number; color: string; dur?: number }> = ({ path, delay, color, dur = 2.4 }) => (
  <circle r={3} fill={color} className="walkthrough-dot">
    <animateMotion dur={`${dur}s`} begin={`${delay}s`} repeatCount="indefinite" path={path} />
  </circle>
);

const FlowGraph: React.FC<{ step: number; motion: boolean }> = ({ step, motion }) => {
  const showRecords = true;
  const stateNodes = stateNodesFor(step);
  const dimNonIncluded = step === 3;

  const queryEdges = (["pm", "ep"] as const).map((s) => curve(X.query + 26, 220, X.source - 44, sources[s].y));
  const sourceEdges = records.map((r) => ({
    id: r.id,
    d: curve(X.source + 44, sources[r.from].y, X.record - 66, r.y),
  }));
  const stateEdges = records.map((r) => {
    const target = r.id === "r1" || r.id === "r2" ? MERGED_Y : r.y;
    return { id: r.id, d: curve(X.record + 66, r.y, X.state - 58, target) };
  });

  const edgeActive = (layer: "query" | "source" | "state") =>
    (layer === "query" || layer === "source") ? step === 0 : step === 1 || step === 2;

  return (
    <svg viewBox="0 0 680 440" className="w-full h-auto" role="img" aria-label={`Flow graph, stage ${step + 1}: ${STEPS[step].title}`}>
      <defs>
        <filter id="wt-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Snapshot frame (audit) */}
      <g className="transition-opacity duration-700" style={{ opacity: step === 4 ? 1 : 0 }}>
        <rect x="8" y="8" width="664" height="424" rx="18" fill="var(--gold-glow)" stroke="var(--accent-gold)" strokeDasharray="6 6" strokeWidth="1.5" />
        <g transform="translate(508 18)">
          <rect width="150" height="26" rx="13" fill="var(--bg-surface)" stroke="var(--border-gold)" />
          <text x="75" y="17" textAnchor="middle" className="wt-label" fill="var(--accent-gold)">
            Snapshot b0398022 · locked
          </text>
        </g>
      </g>

      {/* Edges: query -> sources */}
      {queryEdges.map((d, i) => (
        <g key={`q${i}`}>
          <path d={d} fill="none" stroke={edgeActive("query") ? "var(--accent-gold)" : "var(--border-silver)"} strokeWidth={1.5} className="transition-[stroke] duration-500" />
          {motion && edgeActive("query") && <FlowDot path={d} delay={i * 0.4} color="var(--accent-gold)" dur={1.6} />}
        </g>
      ))}

      {/* Edges: sources -> records */}
      {sourceEdges.map((e, i) => (
        <g key={e.id}>
          <path d={e.d} fill="none" stroke={edgeActive("source") ? "var(--accent-gold)" : "var(--border-silver)"} strokeWidth={1.5} className="transition-[stroke] duration-500" />
          {motion && edgeActive("source") && <FlowDot path={e.d} delay={0.8 + i * 0.3} color="var(--accent-gold)" />}
        </g>
      ))}

      {/* Edges: records -> state column */}
      {stateEdges.map((e, i) => {
        const visible = step >= 1;
        const node = stateNodes.find((n) =>
          e.id === "r1" || e.id === "r2" ? n.key === "a" : n.key === { r4: "b", r3: "c", r5: "d" }[e.id as "r4" | "r3" | "r5"],
        );
        const tone = node?.tone ?? "muted";
        const dim = dimNonIncluded && !(e.id === "r1" || e.id === "r2");
        return (
          <g key={`s${e.id}`} className="transition-opacity duration-500" style={{ opacity: visible ? (dim ? 0.25 : 1) : 0 }}>
            <path d={e.d} fill="none" stroke={edgeActive("state") ? toneStroke[tone] : "var(--border-silver)"} strokeWidth={1.5} className="transition-[stroke] duration-500" />
            {motion && visible && edgeActive("state") && <FlowDot path={e.d} delay={i * 0.35} color={toneStroke[tone]} />}
          </g>
        );
      })}

      {/* Same-study link (cannot-link) */}
      <g className="transition-opacity duration-500" style={{ opacity: step === 1 ? 1 : 0 }}>
        <path
          d={`M ${X.state + 60} ${MERGED_Y + 12} C ${X.state + 96} ${MERGED_Y + 50}, ${X.state + 96} ${ROW.r4 - 50}, ${X.state + 60} ${ROW.r4 - 12}`}
          fill="none"
          stroke="var(--accent-steel)"
          strokeDasharray="4 4"
          strokeWidth={1.5}
        />
        <text x={X.state + 98} y={(MERGED_Y + ROW.r4) / 2 + 4} className="wt-small" fill="var(--accent-steel)">
          study S1
        </text>
      </g>

      {/* PICO chips */}
      {picoChips.map((c, i) => {
        const d = curve(X.state + 58, MERGED_Y, X.pico - 50, c.y);
        return (
          <g key={c.k} className="transition-opacity duration-500" style={{ opacity: step === 3 ? 1 : 0, transitionDelay: step === 3 ? `${i * 120}ms` : "0ms" }}>
            <path d={d} fill="none" stroke={c.color} strokeWidth={1.25} strokeOpacity={0.7} />
            {motion && step === 3 && <FlowDot path={d} delay={i * 0.25} color={c.color} dur={1.8} />}
            <g transform={`translate(${X.pico - 50} ${c.y - 15})`}>
              <rect width="104" height="30" rx="8" fill="var(--bg-surface)" stroke={c.color} />
              <text x="10" y="19" className="wt-label" fill={c.color} fontWeight={600}>
                {c.k}
              </text>
              <text x="22" y="19" className="wt-small" fill="var(--text-secondary)">
                {c.text}
              </text>
            </g>
          </g>
        );
      })}

      {/* Query node */}
      <g>
        <circle cx={X.query} cy={220} r={26} fill="var(--bg-surface)" stroke={step === 0 ? "var(--accent-gold)" : "var(--border-silver)"} strokeWidth={1.5} filter={step === 0 ? "url(#wt-glow)" : undefined} />
        <Search x={X.query - 9} y={220 - 9} width={18} height={18} color="var(--accent-gold)" strokeWidth={1.75} />
        <text x={X.query} y={268} textAnchor="middle" className="wt-label" fill="var(--text-primary)">
          Query v1
        </text>
      </g>

      {/* Source nodes */}
      {(Object.keys(sources) as Array<keyof typeof sources>).map((k) => (
        <g key={k}>
          <rect x={X.source - 44} y={sources[k].y - 17} width={88} height={34} rx={17} fill="var(--bg-surface)" stroke={step === 0 ? "var(--accent-gold)" : "var(--border-silver)"} strokeWidth={1.25} />
          <text x={X.source} y={sources[k].y + 4} textAnchor="middle" className="wt-label" fill="var(--text-primary)">
            {sources[k].label}
          </text>
        </g>
      ))}

      {/* Record nodes */}
      {showRecords &&
        records.map((r, i) => {
          const merged = step >= 1 && (r.id === "r1" || r.id === "r2");
          const dim = dimNonIncluded && !(r.id === "r1" || r.id === "r2");
          return (
            <g
              key={r.id}
              className="transition-opacity duration-500"
              style={{ opacity: dim ? 0.3 : 1, transitionDelay: step === 0 ? `${300 + i * 120}ms` : "0ms" }}
            >
              <rect
                x={X.record - 66}
                y={r.y - 21}
                width={132}
                height={42}
                rx={10}
                fill="var(--bg-surface)"
                stroke={merged ? "var(--accent-gold)" : "var(--border-silver)"}
                strokeWidth={1.25}
              />
              <text x={X.record - 54} y={r.y - 3} className="wt-label" fill="var(--text-primary)">
                {r.label}
              </text>
              <text x={X.record - 54} y={r.y + 12} className="wt-small" fill="var(--text-muted)">
                {r.sub}
              </text>
            </g>
          );
        })}

      {/* Bracket for merged pair */}
      <path
        d={`M ${X.record + 72} ${ROW.r1 - 14} h 8 V ${ROW.r2 + 14} h -8`}
        fill="none"
        stroke="var(--accent-gold)"
        strokeWidth={1.5}
        className="transition-opacity duration-500"
        style={{ opacity: step === 1 ? 1 : 0 }}
      />

      {/* State column */}
      {stateNodes.map((n) => {
        const dim = dimNonIncluded && n.key !== "a";
        return (
          <g key={`${n.key}-${n.label}`} className="wt-pop" style={{ opacity: dim ? 0.3 : 1 }}>
            <rect
              x={X.state - 58}
              y={n.y - 21}
              width={116}
              height={42}
              rx={10}
              fill="var(--bg-surface)"
              stroke={toneStroke[n.tone]}
              strokeDasharray={n.dashed ? "4 3" : undefined}
              strokeWidth={1.5}
              filter={n.key === "a" && (step === 2 || step === 3) ? "url(#wt-glow)" : undefined}
            />
            <text x={X.state - 46} y={n.y - 3} className="wt-label" fill={n.tone === "muted" ? "var(--text-secondary)" : toneStroke[n.tone]} fontWeight={600}>
              {n.label}
            </text>
            {n.sub && (
              <text x={X.state - 46} y={n.y + 12} className="wt-small" fill="var(--text-muted)">
                {n.sub}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};

/* ---------- Walkthrough ---------- */

export const ReviewWalkthrough: React.FC = () => {
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [cycle, setCycle] = useState(0); // restarts the progress bar animation
  const rootRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const startedRef = useRef(false);
  const tablistRef = useRef<HTMLDivElement>(null);

  // Keep the active stage visible in the horizontally scrolling stepper (mobile)
  useEffect(() => {
    const list = tablistRef.current;
    const tab = tabRefs.current[step];
    if (!list || !tab || list.scrollWidth <= list.clientWidth) return;
    list.scrollTo({ left: tab.offsetLeft - 8, behavior: "smooth" });
  }, [step]);

  const reduceMotion = useMemo(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    [],
  );

  // Start playing the first time the walkthrough scrolls into view
  useEffect(() => {
    if (reduceMotion || !rootRef.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !startedRef.current) {
          startedRef.current = true;
          setPlaying(true);
        }
      },
      { threshold: 0.35 },
    );
    obs.observe(rootRef.current);
    return () => obs.disconnect();
  }, [reduceMotion]);

  // Auto-advance
  useEffect(() => {
    if (!playing) return;
    const t = window.setTimeout(() => {
      if (step >= STEPS.length - 1) {
        setPlaying(false);
      } else {
        setStep((s) => s + 1);
        setCycle((c) => c + 1);
      }
    }, STEP_MS);
    return () => window.clearTimeout(t);
  }, [playing, step, cycle]);

  const goTo = useCallback((i: number, stopPlaying = true) => {
    setStep(Math.max(0, Math.min(STEPS.length - 1, i)));
    setCycle((c) => c + 1);
    if (stopPlaying) setPlaying(false);
  }, []);

  const togglePlay = () => {
    if (!playing && step === STEPS.length - 1) {
      setStep(0);
    }
    setCycle((c) => c + 1);
    setPlaying((p) => !p);
  };

  const reset = () => {
    setStep(0);
    setCycle((c) => c + 1);
    setPlaying(false);
  };

  const onTabKey = (e: React.KeyboardEvent, i: number) => {
    let next = -1;
    if (e.key === "ArrowRight") next = (i + 1) % STEPS.length;
    if (e.key === "ArrowLeft") next = (i - 1 + STEPS.length) % STEPS.length;
    if (e.key === "Home") next = 0;
    if (e.key === "End") next = STEPS.length - 1;
    if (next >= 0) {
      e.preventDefault();
      goTo(next);
      tabRefs.current[next]?.focus();
    }
  };

  const current = STEPS[step];

  return (
    <div ref={rootRef} className="space-y-5">
      {/* Stepper */}
      <div className="glass-panel flex items-stretch gap-2 p-2">
        <div ref={tablistRef} role="tablist" aria-label="Review stages" className="relative flex-1 min-w-0 grid grid-flow-col auto-cols-[minmax(150px,1fr)] gap-1 overflow-x-auto no-scrollbar">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            const active = i === step;
            const done = i < step;
            return (
              <button
                key={s.id}
                ref={(el) => {
                  tabRefs.current[i] = el;
                }}
                role="tab"
                id={`wt-tab-${s.id}`}
                aria-selected={active}
                aria-controls="wt-panel"
                tabIndex={active ? 0 : -1}
                onClick={() => goTo(i)}
                onKeyDown={(e) => onTabKey(e, i)}
                className={`relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-left overflow-hidden ${
                  active
                    ? "bg-[var(--gold-glow)] ring-1 ring-[var(--border-gold)]"
                    : "hover:bg-[var(--bg-raised)]"
                }`}
              >
                <span
                  className={`grid place-items-center w-9 h-9 shrink-0 rounded-lg border ${
                    active || done
                      ? "border-[var(--border-gold)] text-[var(--accent-gold)]"
                      : "border-[var(--border-silver)] text-[var(--text-muted)]"
                  }`}
                >
                  <Icon className="w-4 h-4" strokeWidth={1.75} />
                </span>
                <span className="min-w-0">
                  <span className="block text-[11px] text-[var(--text-muted)]">Stage {i + 1}</span>
                  <span className={`block text-sm font-semibold truncate ${active ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}>
                    {s.label}
                  </span>
                </span>
                {active && (
                  <span className="absolute left-0 bottom-0 h-0.5 w-full bg-[var(--border-subtle)]">
                    <span
                      key={cycle}
                      className="block h-full bg-[var(--accent-gold)] origin-left"
                      style={{
                        animation: `wt-progress ${STEP_MS}ms linear forwards`,
                        animationPlayState: playing ? "running" : "paused",
                      }}
                    />
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-1.5 pl-1 shrink-0">
          <button
            type="button"
            onClick={togglePlay}
            aria-label={playing ? "Pause walkthrough" : "Play walkthrough"}
            className="grid place-items-center w-10 h-10 rounded-lg border border-[var(--border-silver)] text-[var(--text-secondary)] hover:text-[var(--accent-gold)] hover:border-[var(--border-gold)]"
          >
            {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            type="button"
            onClick={reset}
            aria-label="Restart walkthrough"
            className="grid place-items-center w-10 h-10 rounded-lg border border-[var(--border-silver)] text-[var(--text-secondary)] hover:text-[var(--accent-gold)] hover:border-[var(--border-gold)]"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Graph + detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="glass-panel lg:col-span-7 p-5 sm:p-6 flex flex-col">
          <div className="flex items-center justify-between gap-3 pb-3">
            <span className="inline-flex items-center gap-2 text-sm whitespace-nowrap text-[var(--text-secondary)]">
              <span className={`w-2 h-2 rounded-full bg-[var(--accent-gold)] ${playing ? "animate-pulse" : ""}`} />
              Review flow
            </span>
            <span className="hidden sm:inline text-xs text-[var(--text-muted)] rounded-md border border-[var(--border-subtle)] px-2 py-1">
              Synthetic benchmark · metformin vs placebo
            </span>
          </div>
          <div className="flex-1 grid place-items-center">
            <FlowGraph step={step} motion={!reduceMotion} />
          </div>
        </div>

        <div
          id="wt-panel"
          role="tabpanel"
          aria-labelledby={`wt-tab-${current.id}`}
          aria-live="polite"
          className="glass-panel-luxury lg:col-span-5 p-6 sm:p-7 flex flex-col gap-5 lg:min-h-[600px]"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium rounded-md border border-[var(--border-gold)] text-[var(--accent-gold)] px-2 py-1">
              {current.label}
            </span>
            <span className="text-xs text-[var(--text-muted)]">
              {step + 1} of {STEPS.length}
            </span>
          </div>

          <div key={current.id} className="wt-fade space-y-5">
            <h3 className="font-serif text-2xl leading-tight text-[var(--text-primary)]">{current.title}</h3>

            <div className="space-y-1.5">
              <p className="text-xs text-[var(--text-muted)]">{current.fieldLabel}</p>
              <p className="font-mono text-[13px] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)]/60 px-3.5 py-2.5 text-[var(--accent-steel)] break-words">
                {current.field}
              </p>
            </div>

            <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{current.body}</p>

            <dl className="flex flex-wrap gap-x-8 gap-y-3">
              {current.stats.map((s) => (
                <div key={s.label}>
                  <dt className="sr-only">{s.label}</dt>
                  <dd className="font-serif text-2xl text-[var(--text-primary)] leading-none">{s.value}</dd>
                  <dd className="text-xs text-[var(--text-muted)] mt-1">{s.label}</dd>
                </div>
              ))}
            </dl>

            <div className="flex gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)]/50 p-4">
              <Info className="w-4 h-4 mt-0.5 shrink-0 text-[var(--accent-gold)]" strokeWidth={1.75} />
              <p className="text-sm text-[var(--text-secondary)]">
                <span className="font-semibold text-[var(--text-primary)]">Why it matters. </span>
                {current.why}
              </p>
            </div>
          </div>

          <div className="mt-auto flex items-center justify-between gap-3 pt-2 border-t border-[var(--border-subtle)]">
            <Link to={current.link.to} className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--accent-gold)] pt-3">
              {current.link.label}
              <ArrowRight className="w-4 h-4" />
            </Link>
            <div className="flex gap-1.5 pt-3">
              <button
                type="button"
                onClick={() => goTo(step - 1)}
                disabled={step === 0}
                aria-label="Previous stage"
                className="grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-silver)] text-[var(--text-secondary)] hover:border-[var(--border-gold)] disabled:opacity-40"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => goTo(step + 1)}
                disabled={step === STEPS.length - 1}
                aria-label="Next stage"
                className="grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-silver)] text-[var(--text-secondary)] hover:border-[var(--border-gold)] disabled:opacity-40"
              >
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewWalkthrough;
