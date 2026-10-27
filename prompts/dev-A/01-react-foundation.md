# A01 — React foundation and premium design system

You are **dev-A**, the frontend/full-stack owner (T1). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-a-01-react-foundation`  
**Priority:** required  
**Target event hours:** 4-8 (coordination window, not continuous coding time)  
**Canonical merge position:** 2 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D01**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/frontend-design.md`, `docs/architecture.md`, `skills/premium-research-ui/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Create the React application foundation and original premium design system against dev-D’s exported contracts, while keeping every unimplemented backend behavior visibly mocked/unavailable.

## Ownership

Primary writable scope:

- `frontend/`
- `planning/dependencies/frontend/`
- `.ci/stages.json`
- `prompts/handoffs/A01.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Move planning/dependencies/frontend/ to frontend/ with its manifest, lock, .nvmrc and build probe intact. Use the selected Node/npm/React/Three pairing; retain strict declaration checking. Set only frontend=application in .ci/stages.json. Dev-D already promoted the backend; preserve that field.

2. Build Vite/React/TypeScript routing and src/main.tsx, semantic page shell, error boundary and CSS tokens. Use the evidence-observatory visual direction with readable review surfaces, original static hero fallback and no fabricated accuracy/user statistics. Do not implement business rules in presentation components.

3. Add the API client and generate frontend/src/api/schema.d.ts from contracts/openapi.json. Provide deterministic npm scripts api:generate and api:check; the latter generates to a temporary file and compares, failing on drift rather than rewriting tracked code. Consume structured errors and trusted backend status values.

4. Implement npm scripts typecheck, test:unit (Vitest run, never passWithNoTests), build, api:check and check:dependencies. Add real utility/contract tests now. Keep the shared dependency probe separately named so a successful probe is not mistaken for a successful application build.

5. Create route shells and reusable controls for review setup, query builder, import progress, result table, duplicate comparison, PICO reader and history. Explicit contract-only 501 responses need a clear not-yet-available state. Do not present mocked saves as durable changes.

6. Choose TanStack Query keys including workspace/revision/query/filter/page; define central API base/origin handling with no frontend secrets. Use local component state for drafts. Implement loading/empty/error/partial shell states and abort obsolete requests.

7. Build keyboard focus, skip link, button/form labels, reduced-motion setting and responsive structure from the start. Plan one lazy scene entry under features/landing/scene; do not import Three into the core review route bundle yet.

8. Provide test fixtures derived from D01 examples and a documented development proxy. Record the shared API assumptions and any needed schema fields for D02/D03, asking their owner to add them before integration.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Frozen install, dependency probe, typecheck, utility tests, api:check and application build pass under the selected runtime.
- Generated types change when the OpenAPI fixture changes; api:check detects stale committed types.
- App shell works at mobile/tablet/desktop widths and with keyboard-only navigation.
- WebGL absent/reduced motion still yields a useful original static landing composition and accessible CTA.
- API failure and explicit 501 are not displayed as success or silently substituted with fake production data.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews API/type generation and dev-C checks the planned text-selection surface. This merge unblocks A02; keep fixture/mock mode visually explicit and separate from real review state.

Write `prompts/handoffs/A01.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
