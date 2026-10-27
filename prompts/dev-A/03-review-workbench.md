# A03 — Review workbench, duplicate controls and PICO editor

You are **dev-A**, the frontend/full-stack owner (T1). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-a-03-review-workbench`  
**Priority:** required  
**Target event hours:** 16-28 (coordination window, not continuous coding time)  
**Canonical merge position:** 10 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **A02, D03**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/frontend-design.md`, `docs/architecture.md`, `skills/premium-research-ui/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Build the usable Level 1 review workbench with duplicate decisions, eligibility overrides, exact PICO editing, audit visibility and CSV export.

## Ownership

Primary writable scope:

- `frontend/src/features/review-queue/`
- `frontend/src/features/duplicates/`
- `frontend/src/features/pico/`
- `frontend/src/api/`
- `frontend/tests/`
- `frontend/playwright.config.ts`
- `frontend/package.json`
- `frontend/package-lock.json`
- `prompts/handoffs/A03.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Regenerate D03 API types and build list/filter/detail layout around actual group snapshots. Use group identity for eligibility and record revision/hash for text annotations. Paginate instead of mounting an unbounded abstract list.

2. Implement duplicate candidate side-by-side comparison showing identifiers, metadata evidence and same-paper versus same-study distinction. Confirm/reject/choose-representative actions send expected versions and a reason; hidden records remain inspectable.

3. Implement Include/Exclude/Maybe controls, required exclusion reason, criteria evidence, notes, provenance badges, undo and pending save state. Do not show unsaved decisions as persisted; retain drafts and allow recovery after failure.

4. Build the PICO reader with semantic DOM text. Convert UTF-16 browser selections to half-open code-point offsets against the exact abstract text/hash. Support P/I/C/O labels, repeated quotes, multiple spans and overlaps without changing source whitespace.

5. Handle stale text/409 conflicts with a compare/reload flow; do not auto-resubmit over another reviewer. Preserve the user’s intended draft separately and require a deliberate save after refresh. Show missing comparator as absent, not an invented label.

6. Expose history/audit events available in D03, CSV export scoped to current snapshot/cutoff, unresolved-conflict omissions and source links. Downloads use backend-authorized responses; do not reconstruct included sets from a stale browser cache.

7. Create Playwright config and frontend/tests/e2e/level1.spec.ts with test:e2e script. Use real HTTP calls to the backend; do not mock API responses for the integrated acceptance test. It will start backend/app/testing/serve.py once D04 creates it. Before D04, run smaller existing browser/utility tests and explicitly mark full integrated e2e pending.

8. Define exact test-server contract for D04: API loopback 8000, frontend preview 4173, fixture source mode, deterministic seeded IDs, readiness checks and process cleanup. The CI integration flag stays false until D04. Do not add skips that survive activation.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- PICO selection/serialization round trip works for emoji, Greek letters, combining marks, multiline text and repeated phrases.
- Conflicting reviewer update shows 409 recovery without losing draft or falsely indicating saved state.
- Duplicate undo/reject, exclusion reason, human include and export flows match actual service responses.
- HTML/script-like abstract content renders as inert text; highlighted spans remain valid.
- Browser acceptance test exists and fails clearly when the required D04 test server is absent; no passWithNoTests or permanent skip.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-C reviews offset semantics and dev-D reviews mutation/version contracts. Hand D04 the exact browser-server startup expectations so integration CI can be activated in one coordinated PR.

Write `prompts/handoffs/A03.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
