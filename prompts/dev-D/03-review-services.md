# D03 — Reviewer services and deterministic pipeline integration

You are **dev-D**, the API, database and data-integrity owner (T4). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-d-03-review-services`  
**Priority:** required  
**Target event hours:** 12-24 (coordination window, not continuous coding time)  
**Canonical merge position:** 8 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D02, B02, C01**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/architecture.md`, `docs/algorithms-and-sources.md`, `skills/review-data-integrity/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Connect the pure dedup, screening and PICO modules to durable review services and expose all Level 1 controls, while keeping reviewer decisions separate from machine suggestions.

## Ownership

Primary writable scope:

- `backend/app/services/`
- `backend/app/api/`
- `backend/app/db/`
- `backend/app/contracts/`
- `backend/migrations/`
- `backend/tests/integration/`
- `contracts/`
- `prompts/handoffs/D03.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Use the actual merged B01/B02/C01 call signatures. Add immutable paper groups, group memberships/snapshots, criterion/machine results, review events and PICO annotation persistence through a single migration chain. Preserve source-record/revision identities and all hidden rows.

2. Implement a deterministic process_corpus service that gathers selected records, calls dedup proposals/group rules, screens each representative and extracts PICO for included abstracts. Persist stage fingerprints and results. C02 will wrap these services; do not bury business logic in a future graph node.

3. Implement current effective-decision projection: human event wins over machine suggestion, unknown/uncertain states remain visible, Exclude requires a reason. Persist actor from trusted session context, expected row version and before/after audit references. Undo appends a superseding event.

4. Expose paginated group/detail review API, duplicate confirmation/rejection/representative change, include/exclude/maybe, PICO corrections and CSV export. Confirmed/rejected duplicate evidence survives reruns. Handle separate publications about one study conservatively.

5. Validate PICO quote/hash/code-point spans and allow overlapping labels; never accept offsets for stale text. A human include schedules missing PICO. A representative change retains old annotations on old revisions and flags new text for review.

6. Create an immutable first corpus snapshot and export cutoff even before Level 2 edits are implemented. Implement D01's read-only evidence repository port with server-derived workspace authorization, selected corpus membership, immutable text revision/hash and strict pagination/byte limits; it serves optional retrieval later without granting raw SQL access. Export one included representative per group, omit unresolved conflicts, include provenance and escape spreadsheet formulas without altering the DB text.

7. Add a narrow service port for C02 to persist/inspect pending human reviews and resume by an authenticated saved event ID. Supply serialization examples and stable error codes. Keep worker wiring unchanged until D04; avoid mutually dependent imports.

8. Ensure every state-changing command atomically persists its review event and any follow-up job. Handle two reviewer writes with 409; idempotent retries return the original result. Keep locks brief and response errors sanitized.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Baseline corpus produces deterministic groups/statuses/PICO from fixtures with no model credentials.
- Human exclusion survives processing rerun; duplicate reject and undo remain recoverable after restart.
- Two edits to one expected version cannot silently overwrite; cross-workspace access fails for all new routes.
- Unicode, repeated quote, overlap and changed text tests validate annotations exactly.
- CSV count/content match revision and decision cutoff; formula-injection fields are safely exported.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-A and dev-C review service usability. Publish the exact command/result examples needed by A03 and the idempotent stage/review ports for C02. No contract or table is left for another developer to invent.

Write `prompts/handoffs/D03.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
