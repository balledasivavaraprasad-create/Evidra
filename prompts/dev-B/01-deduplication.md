# B01 — Deterministic deduplication engine

You are **dev-B**, the deduplication, screening and ML evaluation owner (T2). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-b-01-deduplication`  
**Priority:** required  
**Target event hours:** 4-12 (coordination window, not continuous coding time)  
**Canonical merge position:** 3 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D01**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/algorithms-and-sources.md`, `docs/architecture.md`, `skills/literature-pipeline/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Implement a pure, deterministic deduplication engine that identifies copies of the same publication without destroying source data or conflating separate reports of a study.

## Ownership

Primary writable scope:

- `backend/app/dedup/`
- `backend/tests/algorithms/dedup/`
- `evals/dedup/`
- `prompts/handoffs/B01.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Use D01 NormalizedRecord and DedupProposal contracts exactly. Implement app/dedup public entrypoints defined by ports.py; no database writes, source HTTP calls, graph imports or reviewer-event mutation. Return evidence and proposed group/edge actions for dev-D services to persist.

2. Normalize DOI wrappers/case/whitespace, PMID digits and title Unicode/punctuation/whitespace while preserving original values and meaning-bearing numbers. Treat missing/invalid metadata as unknown, never a positive exact match.

3. Detect consistent exact DOI/PMID copies and repeated source identity separately. Contradictory strong identifiers, correction/retraction/version signals or known rejected edges require manual handling, not automatic group union.

4. Implement multi-key candidate blocking using title tokens/year/author/journal with explicit missing-field behavior. For small fixture sets retain an all-pairs reference to evaluate blocking recall. Avoid excluding a plausible pair just because an author or DOI is missing.

5. Compute documented multi-field scores and evidence with at least two independent supporting fields for a fuzzy proposal. Similarity is not a calibrated probability. Initially only consistent exact identifier matches can auto-merge; fuzzy pairs stay pending human confirmation.

6. Build deterministic accepted-edge components honoring cannot-link constraints and whole-component identifier consistency. Test the transitive bridge A–B–C before merging; do not let pairwise similarity bypass a rejected A–C relation.

7. Choose a representative deterministically: valid reviewer pin, complete abstract/richer metadata, documented source preference, stable record ID. Do not use arrival order or wall time. Return relation information without deleting/hiding records directly.

8. Create own synthetic positives/negatives under evals/dedup and tests, including conference/journal reports, protocol/results, follow-up analyses, shared registration number and missing DOI. Record heuristic assumptions and candidate workload.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Input permutation yields identical proposals/partition/representative choices for identical accepted evidence.
- Null DOI values never merge; equivalent normalized DOI strings do; contradictory identifiers abstain.
- Same-study separate publications remain separate unless same-paper evidence supports the pair.
- Cannot-link and whole-component contradiction block a transitive false merge.
- Missing fields still permit candidate generation without treating absent fields as agreement.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews the returned proposal/persistence contract and dev-C reviews fixtures. Publish exact normalization/evidence behavior and the thresholds as provisional heuristics. B02 can continue independently; D03 consumes these outputs only after they merge.

Write `prompts/handoffs/B01.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
