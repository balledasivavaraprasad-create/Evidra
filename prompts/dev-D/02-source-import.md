# D02 — Live literature adapters and durable import jobs

You are **dev-D**, the API, database and data-integrity owner (T4). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-d-02-source-import`  
**Priority:** required  
**Target event hours:** 4-12 (coordination window, not continuous coding time)  
**Canonical merge position:** 5 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D01**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/architecture.md`, `docs/algorithms-and-sources.md`, `skills/review-data-integrity/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Deliver the first real question → saved search/count → approved retrieval → persisted record loop, with durable import jobs and both source adapters where time permits.

## Ownership

Primary writable scope:

- `backend/app/sources/`
- `backend/app/services/imports.py`
- `backend/app/services/jobs.py`
- `backend/app/api/`
- `backend/app/worker.py`
- `backend/app/db/`
- `backend/migrations/`
- `backend/tests/sources/`
- `backend/tests/integration/`
- `contracts/`
- `prompts/handoffs/D02.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Implement question/criteria creation, immutable query versions and source-specific query translation from the frozen Boolean AST. Validate AND/OR/NOT grouping, date inclusivity and unsupported source settings; preserve exact translated text and execution timestamp. Count queries sequentially and store execution identity independently from query text.

2. Implement PubMed ESearch/EFetch with shared pacing below documented limits, configured tool/contact, bounded retries/timeouts, hardened XML parsing, structured abstract assembly and safe provenance. Count is not import count. Explicitly surface any retrieval cap or source limitation.

3. Implement Europe PMC behind the same protocol: explicit synonym setting, core results, cursor checkpoint, source namespace and safe normalization. Never label every ID as a PMID. Handle repeated cursors, missing abstract/date/authors and per-source partial failure without looping or discarding successfully saved data.

4. Add approval/import endpoint requiring selected search execution IDs, workspace authorization, displayed cap and idempotency key. Browser query text alone is not approval to fetch. Unique source identities upsert and add memberships; changed metadata creates a revision, not historical overwrite.

5. Implement app/worker.py and jobs service with one-worker leases, atomic enqueue and short writes. Initial dispatch supports source-import jobs and a documented extension point for D04 to invoke C02. Do not hold SQLite transactions across HTTP calls. Page writes and cursor advancement commit together.

6. Persist totals/fetched/unique/partial/truncated/progress/errors. Expose GET job status and safe retry/cancel behavior. Resume after a crash without duplicating records; missing IDs already stored must still gain membership. Use cancellation checks between batches.

7. Provide test-only fixture source transport gated by APP_ENV=test/CI_OFFLINE; never a production route accepting arbitrary fixture data. Supply fixture integration examples to A02 and a small manual live-query procedure for the hour-12 checkpoint.

8. Update OpenAPI only through the frozen contract rules and add any migration serially. Record NCBI registration/disclaimer work still pending rather than claiming registration through configuration alone.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Count/approve/fetch persists expected records and source/query memberships through application restart.
- Double import of one execution is idempotent; reused key with changed payload is rejected.
- 429/Retry-After, 5xx, missing abstract, malformed XML, repeated Europe PMC cursor and cancellation produce bounded visible outcomes.
- Failed source or interrupted page leaves recoverable partial job, not a false completed import.
- Cross-workspace job/record reads and approvals fail authorization; stored payload excludes credentials.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-A reviews endpoint responses for A02. Hand C02 the job extension contract and D03 normalized record/revision/group-input interfaces. Merge before A02 integration; run a small real API smoke separately from fixture CI.

Write `prompts/handoffs/D02.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
