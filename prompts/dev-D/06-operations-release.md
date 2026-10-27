# D06 — Operational hardening and release configuration

You are **dev-D**, the API, database and data-integrity owner (T4). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-d-06-operations-release`  
**Priority:** required  
**Target event hours:** 52-62 (coordination window, not continuous coding time)  
**Canonical merge position:** 22 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D04, B03, C03, A04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/architecture.md`, `docs/algorithms-and-sources.md`, `skills/review-data-integrity/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Prepare operational reliability and release-mode enforcement for the actual set of merged features, without making optional AI/Level 2 prerequisites for a valid Level 1 release.

## Ownership

Primary writable scope:

- `backend/app/api/`
- `backend/app/services/`
- `backend/app/settings.py`
- `backend/scripts/`
- `backend/tests/operations/`
- `backend/tests/security/`
- `.ci/stages.json`
- `scripts/ci/`
- `docs/operations.md`
- `.github/workflows/ci.yml`
- `audit.md`
- `prompts/handoffs/D06.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Rebase onto the completed G3 baseline and any selected merged extras. Read all relevant handoffs. Explicitly list which optional prompts are merged, deferred or cut; never claim an unmerged feature in configuration or docs.

2. Implement and test backup/restore using SQLite backup APIs or coordinated quiescence of business/checkpoint files. Coordinate API/worker activity, capture schema and artifact metadata, test restore to an empty directory and document the separate checkpoint/domain transaction boundary.

3. Harden production configuration: secure session/CSRF/origin handling, reviewer authorization, fail-safe missing secrets, local mode loopback-only, sanitized logs and health/readiness. Secrets never enter frontend environment or artifacts. Verify source pacing configuration and persistent volume paths are absolute/consistent across processes.

4. Provide migration/startup/shutdown/runbook commands and a small readiness check for A06 deployment packaging. Confirm one migration head, fresh install and upgrade from the prior schema, disk-space/locked-DB failures and orderly job cancellation/recovery.

5. If D05/B04/C04/A05 are all merged and Level 2 tests pass, enable level2=true. If C05/C06 are merged, integrate authorized assistant/extraction endpoints and real gateway configuration behind default-off runtime flags, then enable ai=true for deterministic mock-backed CI security tests. No missing module import, disabled test or empty test suite counts as activation.

6. If B05 is merged, expose its versioned ranking output through existing service contracts without turning ranking into automatic exclusion. If optional features are absent, leave their runtime routes unavailable/explicit and CI flags false; record the cut. C05 alone may remain a nonexposed module experiment.

7. Collect backend security/operations results in docs/operations.md and prepare a specific handoff for A06: image/runtime needs, entrypoints, ports, health URLs, database backup location, quotas and deployment secrets. Verify host choices later rather than inventing free persistent hosting.

8. Update audit.md and the stage configuration as integration captain. Do not weaken any previously enabled CI stage; a broken implemented feature is fixed or deliberately removed in a separately reviewed architectural change, not hidden by a flag downgrade.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Backup restores required reviewer records and snapshots to a fresh directory; active WAL data is not lost.
- Production configuration rejects insecure local identity/public binding combinations.
- Fresh/upgrade migrations, concurrent writes, worker shutdown/recovery and missing-disk errors are covered.
- Any exposed optional AI endpoint is workspace-authorized, budgeted, default-off and covered by adversarial mock tests.
- Enabled Level 2/AI stages have actual required test files and run in the full suite; absent extras do not break baseline.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-A reviews deployment contract and dev-C security; dev-B receives the final implemented method set for B06. This prompt prepares release operations; public hosting remains A06/team authorization, not an automatic action here.

Write `prompts/handoffs/D06.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
