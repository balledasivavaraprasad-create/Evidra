# D04 — Level 1 wiring, authorization and integrated CI activation

You are **dev-D**, the API, database and data-integrity owner (T4). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-d-04-level1-integration`  
**Priority:** required  
**Target event hours:** 24-30 (coordination window, not continuous coding time)  
**Canonical merge position:** 11 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D03, C02, A03**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/architecture.md`, `docs/algorithms-and-sources.md`, `skills/review-data-integrity/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Wire the real LangGraph implementation into durable jobs, complete Level 1 authorization, and activate application end-to-end CI only when the actual fixture-backed workflow is ready.

## Ownership

Primary writable scope:

- `backend/app/services/`
- `backend/app/api/`
- `backend/app/worker.py`
- `backend/app/testing/`
- `backend/tests/integration/`
- `backend/tests/security/`
- `contracts/`
- `.ci/stages.json`
- `scripts/ci/`
- `.github/workflows/ci.yml`
- `audit.md`
- `prompts/handoffs/D04.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Integrate C02 graph facade through the worker/service extension points established by D02/D03. The API enqueues jobs; it does not run a long pipeline inside a request. Persist job/revision/trace identifiers and ensure a failed graph does not replace a published snapshot.

2. Authorize graph resume through pending-review lookup and a saved human event. Use expected versions, workspace membership and replay-safe command keys. Never expose raw checkpoint/thread mutation as a public API.

3. Finish baseline local/remote identity boundaries, origin/CSRF controls appropriate to cookie sessions, safe errors and authorization tests. Document that loopback local demo identity is not production authentication.

4. Implement backend/app/testing/serve.py for CI-only startup and seeding: refuse unless APP_ENV=test, require SOURCE_MODE=fixture, create a disposable SQLite DB, migrate/seed synthetic data, start API plus worker with clean signal/shutdown handling and loopback binding. Do not add a public seeding/reset endpoint.

5. Coordinate A03 Playwright config, ports and health checks. The test server must use synthetic source responses even when the browser exercises search/import endpoints. Verify a browser can complete search → import → duplicate override → screening override → PICO edit → CSV.

6. Set .ci/stages.json integration=true in this PR only after both application modes and all required test/config paths exist. Keep level2/ai false. The workflow must fail on missing tests, server startup failure or failed browser assertions, not silently skip.

7. Collect run logs and restart evidence. Add process-crash/replay tests around commit/checkpoint boundaries and source failures. Fix backend integration defects in owned modules; route frontend defects to a small A03 follow-up and wait for its merge.

8. Consolidate handoff status into audit.md as captain; distinguish integrated fixture CI from a live-provider/manual demo. Verify the same build works with LLM/RAG disabled and without secret environment variables.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Complete Level 1 fixture-backed browser scenario passes against real API/DB/worker, not mocked browser responses.
- API/job restart retains human events and resumes stages without duplicate domain effects.
- Malicious thread/workspace IDs cannot resume or read another review.
- Test launcher refuses production mode and cleans up child processes; fresh DB and migrated DB both work.
- CI integration flag makes e2e mandatory, and a failing e2e makes the aggregate gate fail.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-A reviews the full browser walkthrough; dev-C reviews resume/replay wiring. This is the shared integration milestone that unblocks B03, C03 and A04. Do not label G3 complete until those three prompts also pass.

Write `prompts/handoffs/D04.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
