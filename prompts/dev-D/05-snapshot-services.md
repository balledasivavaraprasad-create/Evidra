# D05 — Version snapshots, decision lineage and exact restoration

You are **dev-D**, the API, database and data-integrity owner (T4). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-d-05-snapshot-services`  
**Priority:** bonus  
**Target event hours:** 36-46 (coordination window, not continuous coding time)  
**Canonical merge position:** 15 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D04, B03, C03, A04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/architecture.md`, `docs/algorithms-and-sources.md`, `skills/review-data-integrity/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Implement the optional Level 2 data services after the complete Level 1 gate, preserving decisions across query changes, merges, splits and exact restoration.

## Ownership

Primary writable scope:

- `backend/app/services/`
- `backend/app/db/`
- `backend/app/api/`
- `backend/app/contracts/`
- `backend/migrations/`
- `backend/tests/level2/`
- `contracts/`
- `prompts/handoffs/D05.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Verify D04/B03/C03/A04 are merged and the baseline is stable. Implement this selected bonus as one coherent slice; keep Level 1 available if the bonus fails. No live API call is allowed for exact restoration.

2. Publish additive snapshot/lineage/conflict/diff contracts first inside this branch or a small reviewed upstream contract PR. Freeze member IDs, record revisions, selected executions, criteria/method versions, group partition, representative choices and decision cutoff for each published snapshot.

3. Implement new query/criteria selection as a new corpus revision. Preserve all historical memberships; removed means removed from active view. Dedup the accumulated set while respecting saved cannot-link decisions and without rewriting previous group snapshots.

4. Implement lineage projection: carry one nonconflicting human decision with its provenance; retain agreeing parents; conflicting parents create an unresolved conflict. Group splits preserve original events and flag merged-group decisions for reaffirmation. Changed criteria retain but mark old human decisions for review.

5. Implement exact snapshot restore from saved data and separately labeled latest-decisions view only if useful. Restore text revisions/representatives/criteria/machine results and decision cutoff exactly; append later edits rather than mutating historical events.

6. Implement diff showing added/removed/changed records and merges/splits/representative changes. Count records separately from paper groups. Create deterministic input invalidation fingerprints for C04 to consume; do not recompute solely because a job ID changed.

7. Expose conflict-resolution and restore endpoints with expected versions, actor/revision authorization and audit events. Snapshot publication must be atomic; failed jobs do not advance current_revision_id.

8. Add migrations without changing applied revisions; write backend/tests/level2/test_snapshot_restore.py. Do not activate level2 CI yet: B04/C04/A05 must complete first, and D06 promotes the gate.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Excluded paper reappearing in a new query stays excluded with provenance.
- Include/Exclude group merge creates visible unresolved conflict and prevents export inclusion.
- New bridge and split do not mutate original snapshot; rejected pair stays rejected.
- Restore initial snapshot reproduces exact saved record revisions, partition and representatives while network is disabled.
- Changed representative does not silently reuse PICO offsets; failed publication leaves previous active revision intact.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-B reviews merge/split semantics; dev-C reviews fingerprints; dev-A reviews API examples. This unblocks B04 and supplies C04/A05 contracts. Mark bonus services implemented separately from completed Level 2 experience.

Write `prompts/handoffs/D05.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
