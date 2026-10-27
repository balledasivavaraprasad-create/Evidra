# A05 — Version history, conflicts, diff and restore UI

You are **dev-A**, the frontend/full-stack owner (T1). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-a-05-history-ui`  
**Priority:** bonus  
**Target event hours:** 48-56 (coordination window, not continuous coding time)  
**Canonical merge position:** 18 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **A04, D05, B04, C04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/frontend-design.md`, `docs/architecture.md`, `skills/premium-research-ui/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Expose the completed Level 2 backend/graph behavior through an understandable history, conflict, diff and exact-restore experience.

## Ownership

Primary writable scope:

- `frontend/src/features/history/`
- `frontend/src/features/conflicts/`
- `frontend/src/api/`
- `frontend/tests/e2e/level2/`
- `prompts/handoffs/A05.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Wait for merged D05/B04/C04 and regenerate API types. Do not build a separate client-side notion of group lineage or reconstruct historical results from current records.

2. Implement query-execution/corpus-version timeline with criteria/method versions, source execution times and counts. A same-text refresh must be visibly different from reopening an immutable snapshot.

3. Implement diff categories for added/removed-from-active-view/text-changed records, newly merged/split groups, representatives and pending decisions. Distinguish paper-group counts from source-record counts and retain filters/pagination.

4. Build a conflict panel showing competing human decisions, provenance and group members. Require deliberate resolution with a reason and expected version. Do not choose a default winner or export unresolved groups as included.

5. Add exact restore action that clearly names the saved snapshot and decision cutoff. If latest-decisions view exists, expose it as a separate labeled mode. Restore is view/state change backed by server snapshots, never a live re-search.

6. Handle pending reruns, stale annotations, criterion revalidation and graph failures without losing the previous published view. Preserve existing drafts when navigating history and warn only when a real unsaved edit would be abandoned.

7. Create frontend/tests/e2e/level2/restore.spec.ts using D05 fixtures and real backend: include/exclude merge conflict, resolve, query edit, diff, restore v1 and confirm exact member/representative identity.

8. Keep level2 CI activation for D06 after this PR merges; once enabled these tests become mandatory. If this bonus is cut, do not leave dead navigation or claims of implemented revert in the release UI.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Record excluded in v1 and reappearing in v2 remains excluded; conflict details reflect saved reviewer events.
- Merge/split diff and representative changes match server snapshots.
- Restore while external network is disabled returns exact v1 identity/partition and correct decision cutoff.
- Latest-decisions and historical-cutoff views cannot be confused in UI labels/export metadata.
- Stale edits, failed reruns and restore errors preserve the last valid review state.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews identity/restoration semantics and dev-B reviews scenario coverage. Hand D06 the passing Level 2 browser command and fixtures so it can promote CI, and A06 the exact demo sequence.

Write `prompts/handoffs/A05.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
