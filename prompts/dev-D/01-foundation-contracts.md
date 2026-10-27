# D01 — Backend foundation and frozen contracts

You are **dev-D**, the API, database and data-integrity owner (T4). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-d-01-foundation-contracts`  
**Priority:** required  
**Target event hours:** 0-4 (coordination window, not continuous coding time)  
**Canonical merge position:** 1 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **None: this is the first implementation prompt after the planning/CI bootstrap commit.**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/architecture.md`, `docs/algorithms-and-sources.md`, `skills/review-data-integrity/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Establish the shared backend and schema/API contracts that allow all four developers to work independently. This is foundation behavior, not a finished Level 1 pipeline.

## Ownership

Primary writable scope:

- `backend/app/contracts/`
- `backend/app/db/`
- `backend/app/main.py`
- `backend/tests/contracts/`
- `backend/migrations/`
- `contracts/`
- `backend/scripts/`
- `.ci/stages.json`
- `scripts/ci/`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `planning/dependencies/backend/`
- `backend/app/settings.py`
- `backend/alembic.ini`
- `backend/dependency_smoke.py`
- `backend/.python-version`
- `backend/tests/conftest.py`
- `backend/tests/fixtures/`
- `prompts/handoffs/D01.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Move the entire locked baseline from planning/dependencies/backend/ to backend/ without changing resolved versions; retain dependency_smoke.py as a library integration probe. Preserve project Python constraints and add application module layout, settings and a minimal FastAPI app. Do not create a second active manifest. Update only the backend field of .ci/stages.json to application in this same PR.

2. Freeze Pydantic types for normalized source records, immutable record text revisions, query AST/date settings, search counts, job progress, criterion evidence, ScreenResult, DedupProposal, PicoResult, review commands, conflicts, snapshots and error envelopes. Include workspace/revision identity, method versions, content hashes and expected-version/idempotency fields. Publish examples for empty, partial, missing-data and conflict cases in contracts/examples/.

3. Create source/service Protocols and pure algorithm ports in app/contracts/ports.py. Specify the function signatures B01/B02/C01 implement, deterministic order and result serialization. Define ports for graph orchestration/reviewer resume, while allowing D02 to run import-only jobs before the graph exists. Reserve a narrow authorized read-only evidence port with workspace, corpus revision, record revision, text/hash and pagination limits; define RetrievalChunk, AssistantProposal and Gateway request/result schemas for optional C05/C06. D03 implements the repository port; these schemas do not activate AI or require bonus snapshots. Do not import unfinished B/C modules at startup.

4. Create the first Alembic migration and SQLAlchemy models for workspaces, criteria/query versions, search executions, source records/revisions, memberships, jobs and run logs. Use stable IDs, unique source identities, FK constraints, UTC times, atomic idempotency records and short transactions. Stage later tables in later migrations; never delay all work to build every bonus table now.

5. Implement health/live and health/ready, validated settings and local-loopback development identity. Define the production authentication boundary and expected workspace membership checks. No public insecure identity mode. Create app/main.py, alembic.ini and scripts/export_openapi.py supporting --check against contracts/openapi.json at repo root.

6. Commit declared route schemas for the planned /api/v1 operations so A can generate types. Stub not-yet-implemented operations must return an explicit structured 501 and must not pretend to save data. Distinguish contract-only status in the handoff. Export deterministic OpenAPI without environment timestamps or unstable ordering.

7. Create backend/tests/contracts/test_contracts.py plus fixtures and a default offline test guard. Add 12–20 clearly synthetic canonical examples containing an exact duplicate, uncertain duplicate, same-study separate reports, missing DOI/abstract/language, Unicode/repeated PICO phrases and conflicting decisions. Keep source fixtures in tests/fixtures, not production data.

8. Run promoted backend CI: strict locks, smoke, Ruff, exactly one migration head, fresh migration, OpenAPI drift check and pytest. Keep frontend stage planning. Update dependency evidence paths consistently and document the promotion in your handoff.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Fresh empty SQLite migration creates required constraints; duplicate source import key fails/upserts as specified.
- Invalid dates/Boolean nodes/status/spans produce stable validation errors; valid examples serialize deterministically.
- Health readiness distinguishes unavailable DB from healthy process; provider absence does not fail core readiness.
- OpenAPI --check fails after a deliberate uncommitted schema drift, and passes after regeneration.
- Backend stage cannot claim application mode without required files; all current planning checks remain green.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Request reviews from dev-A for usability of contracts and dev-B/dev-C for algorithm signatures. This merge unblocks A01, B01, C01 and D02. Publish the exact callable interfaces, not only a schema diagram.

Write `prompts/handoffs/D01.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
