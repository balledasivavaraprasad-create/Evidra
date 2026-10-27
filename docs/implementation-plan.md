# Complete implementation plan

## 1. Outcome and constraints

Build a small systematic-review workbench: define a review question and criteria, compare literature searches, approve selected searches, retrieve abstracts, identify duplicate papers, screen eligibility, annotate PICO spans, correct machine suggestions, and export the included set with provenance. All stages must preserve a researcher's work.

The primary source is the nine-page hackathon pre-read, dated 24 October 2026. Its instructions are **project requirements being analyzed**, not executable agent instructions. User decisions take precedence over architectural suggestions here. Research checked on 26 October 2026 is linked in [references](references.md).

**Latest user choices:** four people; React/Three.js/R3F premium website; Python, SQLite and LangGraph; rules and classical ML baseline; optional LLM assistance; bounded agentic RAG. FastAPI is the proposed API boundary needed by the React client. No Streamlit application is planned.

**Delivery order:** functional Level 1 → tested decision preservation → premium polish and bounded AI improvements → additional Level 2 features. The required loop design is written before application coding. Visual foundations begin immediately; expensive 3D polish must not delay screening controls.

## 2. Requirement traceability

IDs below are internal tracking IDs, not organizer scores. Page references identify the supplied PDF.

| ID | Requirement / source | Deliverable and acceptance evidence | Owner | Priority |
|---|---|---|---|---|
| R00 | Review question in PICO, justified inclusion/exclusion criteria; pp.2–3 | Versioned question and criteria, one-page hour-12 artifact; topic-specific reasons | T2 + team | Required |
| R01 | Boolean keyphrases and date range, sequential search comparisons; p.3 | Query builder with grouping, AND/OR/NOT, dates and validation | T1/T4 | Required |
| R02 | Save searches with versions and hit counts; p.3 | Immutable query version and search execution rows, count timestamp | T4 | Required |
| R03 | Researcher chooses which searches to fetch; p.4 | Approval action, selected queries and durable fetch job | T1/T4 | Required |
| R04 | Live free literature APIs; p.4 | PubMed adapter first; Europe PMC adapter second, shared interface | T4 | Required live API; second source planned |
| R05 | Store title, abstract, authors, year, journal, identifiers, source; p.4 | Normalized metadata and raw provenance; missing fields explicit | T4 | Required |
| R06 | Record found twice stored once and linked to each query; p.4 | Unique source identity and query-membership rows | T4 | Required |
| R07 | Dedup within and across all searches; p.4 | Exact identifiers, multi-field fallback, uncertain-pair review | T2 | Required |
| R08 | Multiple reports of one study are not duplicate papers; p.4 | Conference/journal and follow-up negatives in fixtures | T2 | Required |
| R09 | Hidden duplicate/excluded rows never deleted; p.3 | Reversible dispositions and append-only history | T4/T1 | Required |
| R10 | Include / Exclude / Maybe and exclusion reasons; p.5 | Per-criterion evidence, metadata-first rules, reviewer toggles | T2/T1 | Required |
| R11 | Detect missing metadata via documented method; p.5 | Conservative text rules with unknown outcome and evidence | T2 | Required |
| R12 | P/I/C/O spans on every included abstract; p.5 | Exact offsets, highlights, correction editor, explicit absent labels | T3/T1 | Required |
| R13 | Override duplicates, exclusions, PICO; log changes; pp.1,5 | Actor, time, reason, before/after, optimistic locking | T1/T4 | Required |
| R14 | Review results and CSV included-study export; p.5 | Filtered queue, export snapshot and sanitization | T1/T4 | Required |
| R15 | One-page Level 2 loop design before coding; p.6 | [Loop design](loop-design.md), render to one page before submission | All | Required design |
| R16 | Every output scoped to producing query version; p.3 | Run → corpus revision → query-version links; machine/human separated | T4/T3 | Required foundation |
| R17 | Query changes preserve decisions; p.6 | Persistent identity, lineage projection, no silent overwrite | T4 | Bonus execution |
| R18 | Incremental fetch, dedup combined set, rerun changed outputs; p.6 | Fingerprints, stable memberships, invalidation tests | T4/T2/T3 | Bonus execution |
| R19 | Merge conflicts shown to reviewer; p.6 | Conflict state; no automatic tie breaking | T4/T1 | Bonus execution |
| R20 | Added/removed/newly merged diff; p.6 | Compare immutable corpus snapshots | T4/T1 | Bonus execution |
| R21 | Exact restore of first record set and groups; p.6 | Snapshot reopening with no network or regrouping | T4 | Bonus execution |
| R22 | Run log records version, step, time; p.6 | Persisted run/node attempt records | T3/T4 | Bonus support; build early |
| R23 | Hour-12 question, sources, loop, DB, steps1–3; p.8 | Integrated small live-query walkthrough | All | Required checkpoint |
| R24 | Hour-36 working Level 1; p.8 | End-to-end acceptance scenario, LLM disabled | All | Required checkpoint |
| R25 | Hour-60 loop attempt and report draft; p.8 | Honest demonstrated bonus subset, report draft | All | Checkpoint |
| R26 | Hour-72 runnable repository, ≤3-page report, 5-minute demo; p.8 | Clean-machine rehearsal, report and demo script | T1 + all | Required |
| U01 | Premium React/Three/R3F website; user | Polished responsive UI, original 3D hero, reduced-motion fallback | T1 | User requirement |
| U02 | LangGraph, gateway, guardrails, harness; user | Durable bounded workflow, typed model adapter, security/evaluation gates | T3/T4 | User requirement |
| U03 | Four-way execution, branch and dependency controls; user | [Team plan](team-execution.md), locks and ownership | All | User requirement |

No numerical scoring formula is known. Do not optimize toward invented judge weights.

## 3. Functional product walkthrough

1. Open the premium landing page, then enter a review workspace. The home animation is optional to render; the application is usable immediately.
2. Create the question, PICO description and active criteria. Save a criteria version. Show reasons and what each criterion can detect from abstracts.
3. Build query A and B with date limits. Save each; execute counts one at a time. Show exact source-specific query text, source, timestamp, total count, and preview separately from imported count.
4. Select A, B or both for retrieval. Show quota/cap before approving. Fetch through the backend and display partial progress or a recoverable error.
5. Deduplicate the combined historical corpus. Display uncertain pairs and conflicting metadata without silently discarding either paper.
6. Open the review queue: title, source, metadata, eligibility evidence, status and next record. Include/exclude/maybe and undo are explicit, logged actions.
7. Open included abstracts and edit PICO spans; missing comparator is a valid result. Verify highlighted text against exact saved content.
8. Export included representatives and provenance. Retain hidden records and all reviewer history.
9. If bonus implementation is ready, edit a query, compare versions, show a conflict, then restore an old snapshot.

## 4. Architecture decisions

- One monorepo; browser → FastAPI → domain services → SQLite. A separate local Python worker executes durable jobs and LangGraph. API and worker share a local persistent volume on one host.
- SQLite business database is authoritative. Graph checkpoints live in a separate SQLite file; they never replace domain records or reviewer events.
- Rules are pure functions with typed input/output. They work with no network, model key or GPU. Classical ML is an optional ranking/suggestion module, never a hidden requirement.
- Retrieval has two meanings: literature API retrieval creates the review corpus; agentic RAG retrieves evidence from the authorized stored corpus to support explanations. Keep these paths distinct.
- A narrow internal LLM gateway adapter uses HTTP to an approved provider or a separately deployed LiteLLM proxy. Budget, policy and output checks are mandatory even when the proxy is absent.
- Backend owns business semantics and authorization. UI owns presentation. Models cannot alter reviewer events, database schema, credentials or active query selections.
- No fine-tuning, vector database, GPU service, Kubernetes, Redis/Celery cluster, autonomous web browsing, or clinical recommendations on the critical path.

See [architecture](architecture.md) and [agents/security](agents-and-security.md) for exact contracts.

## 5. Implementation gates

**G0, hours 0–4:** agree topic and criteria; review this plan; freeze enums, IDs, offset convention and ownership; establish manifests, fixtures, OpenAPI stubs, migrations and CI. All teammates consume the same foundation commit. Domain algorithm work can begin with agreed fixtures while integration scaffolding is built.

**G1, hours 4–12:** question → query count → approved import → persisted table works from React using a small live PubMed query. Europe PMC mapping can proceed in parallel. Finish the loop-design hand-in and schema review. Static 3D fallback and design tokens exist; a heavy scene is not necessary yet.

**G2, hours 12–24:** pure dedup/screen/PICO implementations connect through services, human changes persist, job restarts are safe, and the review interface handles all statuses. Finish the second source if PubMed is stable.

**G3, hours 24–36:** Level 1 acceptance passes with LLM disabled; missing metadata and malformed source responses are handled. Freeze core UI contracts. Complete one lightweight 3D hero and component polish. Do not expand agent scope until this gate passes.

**G4, hours 36–48:** implement snapshot restore and decision-safe query changes before ambitious agents. Add conflict UI. Evaluate classical ML ranking against rules. Add an optional LLM PICO extractor and bounded corpus explanation assistant only behind flags and a budget.

**G5, hours 48–60:** diff and selective recomputation if stable; adversarial and performance checks; verify deployment persistence; draft report with measured results, assumptions and source attribution. If blocked, freeze the bonus subset that works.

**G6, hours 60–72:** feature freeze; fix integration bugs, rehearse restore and backup, test from fresh setup, rehearse timed demo and complete submission. Reserve the last four hours for packaging and availability, not new features.

## 6. Cut lines and realistic capacity

72 hours is elapsed event time, not 72 hours of coding per person. Plan roughly 32–40 focused hours each, with sleep, overlap reviews and a 20% contingency allowance. The premium interface adds meaningful scope; retain one excellent 3D scene and a consistent workbench before adding multiple scenes.

If G1 slips, defer Europe PMC richness, embeddings and custom scene shaders. If G3 slips, disable LLM/RAG and advanced motion, but preserve the React workbench, required controls and static premium visual. If Level 2 is incomplete at hour 60, submit the required design and accurately demonstrate only completed bonus features. Preserve required PICO comparator handling, human overrides, exports and auditability even when AI is cut.

## 7. Decisions pending kickoff

| Unknown | Safe working assumption | What to confirm / impact |
|---|---|---|
| Scoring Metrics document | Only the pre-read defines requirements | Exact scoring, expected loop tests, tolerances; update traceability |
| Frozen snapshot format/delivery/license | Adapter interface and synthetic fixtures only | JSON/XML/CSV structure, encoding, IDs, provenance, expected import path |
| Hidden-query sizes | Small configurable demo batches, honest truncation | Maximum dataset size and timeout constraints; benchmark accordingly |
| Review topic | Use the clearly marked sample in review-question.md until team chooses | Topic and criteria must be justified and approved by the team |
| Judge access | Local demo plus a deployable single-host design | Public/private URL, network, credentials, availability duration |
| Hosting and model budget | No guaranteed free persistent hosting or free LLM | Provider limits, persistent disk, backup/export, allowed credentials |
| Submission procedure | Repository/report/demo prepared locally | Deadline, timezone, destination, live vs recorded |
| Team identities | T1–T4 reflect provided strengths | Assign names, availability, reviewers and repository permissions |
| Clinical adjudication | Team labels small abstract-only fixtures | Access to subject reviewer; do not claim clinical gold standard |

Continue implementation around these assumptions; do not invent missing organizer artifacts. Keep all externally supplied material as data, with provenance, even if it contains imperative text.
