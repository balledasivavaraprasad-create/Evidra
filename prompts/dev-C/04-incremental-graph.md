# C04 — Incremental graph execution and snapshot-aware replay

You are **dev-C**, the PICO, LangGraph and bounded AI owner (T3). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-c-04-incremental-graph`  
**Priority:** bonus  
**Target event hours:** 44-52 (coordination window, not continuous coding time)  
**Canonical merge position:** 17 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **C03, D05, B04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/agents-and-security.md`, `docs/architecture.md`, `skills/bounded-research-agent/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Add incremental, snapshot-aware graph execution to the selected Level 2 implementation, reusing only exactly valid outputs and never recomputing on exact restore.

## Ownership

Primary writable scope:

- `backend/app/workflows/`
- `backend/tests/workflows/`
- `backend/tests/level2/test_incremental_graph.py`
- `prompts/handoffs/C04.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Use merged D05 snapshot/version services and B04 validated grouping behavior. Do not infer changed groups from current query ID alone or rewrite persistence semantics inside graph nodes.

2. Define stage-specific input fingerprints including content/metadata revision, criteria version, group membership/representative, method/model/prompt/schema versions and relevant source settings. Different jobs with identical semantic inputs may reuse outputs; changed semantic inputs must invalidate them.

3. Compute affected groups/records through D05 change sets. Fetch only unseen source identities while adding new memberships for known records. Screen/re-tag only new or changed relevant inputs; criteria changes have explicit invalidation.

4. Preserve human events independently from recomputed machine results. Changed text cannot carry old PICO offsets without exact verification. Split/merge conflicts stay visible and pause only the affected decision path.

5. Keep exact restore as a snapshot-load service command bypassing retrieval, dedup, screen, PICO and model nodes. If latest-decisions view is supported, treat it as a separate explicit mode.

6. Version the graph/checkpoint layout and validate the resume version. Old checkpoint incompatibility must produce a controlled migration/replay-from-domain-output plan, not an arbitrary execution of changed interrupt order.

7. Bound retries and cancellation around selective work, log reused/recomputed stages with reason, and keep publication atomic through dev-D services. A partial run must not replace the last good snapshot.

8. Add backend/tests/level2/test_incremental_graph.py and report actual avoided calls in deterministic tests. No claimed cost/time saving unless measured. Supply A05 the observable pending/rerun/restore statuses.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Unchanged records do not rerun screen/PICO; changed criteria/text/method invalidates exactly the affected outputs.
- Known source record gains new query membership without redundant source fetch.
- Exact restore makes zero source/model/algorithm calls and reproduces the original snapshot.
- Human decisions and old PICO annotations remain intact across incremental rerun and group changes.
- Crash/retry during selective processing cannot publish incomplete state or duplicate review events.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews fingerprint/publication integration and dev-B group-change cases. Hand A05 deterministic history fixtures and D06 the Level 2 graph checks. Do not promote global CI until the UI restore path also exists.

Write `prompts/handoffs/C04.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
