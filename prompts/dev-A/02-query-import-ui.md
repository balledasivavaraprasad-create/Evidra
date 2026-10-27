# A02 — Query builder and approved import experience

You are **dev-A**, the frontend/full-stack owner (T1). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-a-02-query-import-ui`  
**Priority:** required  
**Target event hours:** 8-12 (coordination window, not continuous coding time)  
**Canonical merge position:** 7 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **A01, D02**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/frontend-design.md`, `docs/architecture.md`, `skills/premium-research-ui/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Deliver the first real React question/search/import workflow with transparent counts, approval and recoverable job progress.

## Ownership

Primary writable scope:

- `frontend/src/features/review-setup/`
- `frontend/src/features/search/`
- `frontend/src/features/runs/`
- `frontend/src/api/`
- `frontend/tests/`
- `prompts/handoffs/A02.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Regenerate types from merged D02 OpenAPI and remove browser mocks only for implemented operations. Keep remaining module stubs explicit. Build workspace/question/PICO/criteria form with reasons, version badge and active-rule controls.

2. Implement a grouped Boolean query builder with AND/OR/NOT, phrases, date validation and source options. Show a readable query preview but send the frozen AST, not untrusted interpolated SQL or arbitrary upstream URLs. Persist query versions through the API.

3. Run search counts one at a time and save/show source-specific execution IDs, translated query, timestamp and total hits. Distinguish query text version from repeated live search execution. Preserve previously compared searches when adding another.

4. Allow the researcher to select specific executions, inspect cap/source choices and explicitly approve import. Generate a stable request idempotency key for retries; disable duplicate click while pending without relying on that UI state for correctness.

5. Poll durable job status with backoff and cancellation. Display actual fetched/unique/partial/truncated counts and stage progress; never manufacture a percentage when total is unknown. Preserve work after reload using job IDs from the server.

6. Implement bounded retry UI using server retryable errors and existing job state. Aborted/stale requests must not replace a newer selection. Missing API credentials show actionable server configuration state without exposing secrets.

7. Present the NCBI attribution/disclaimer link and source provenance supplied by the backend. Ensure real live searches are labeled live and fixture mode is labeled synthetic. Prepare the hour-12 walkthrough using a small allowed live query outside CI.

8. Wire pagination/empty results as available. Record any field/schema mismatch for D02; fix through additive upstream contract change, then regenerate types. Do not silently rename backend enums in the UI.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Create review, save two searches, compare counts, select one/both, approve import and inspect persisted records.
- Zero hits is a successful empty state; 429/partial import/cancel/error are distinct states.
- Reload during job preserves its status and selection; repeated submit uses the same idempotency key until payload changes.
- Keyboard form workflow, invalid dates/grouping and error associations work.
- Old query response arriving late cannot overwrite current query state or display another workspace data.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews request/response examples and a fixture-backed UI walkthrough. Hand A03 the stable workspace/query/revision context and selection/error components. Document manual live demo evidence separately.

Write `prompts/handoffs/A02.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
