# A04 — Premium 3D experience and Level 1 usability gate

You are **dev-A**, the frontend/full-stack owner (T1). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-a-04-premium-3d`  
**Priority:** required  
**Target event hours:** 28-36 (coordination window, not continuous coding time)  
**Canonical merge position:** 14 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **A03, D04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/frontend-design.md`, `docs/architecture.md`, `skills/premium-research-ui/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Complete the user-requested premium React/Three.js experience and the Level 1 usability gate without slowing down abstract review.

## Ownership

Primary writable scope:

- `frontend/src/features/landing/`
- `frontend/src/components/`
- `frontend/src/styles/`
- `frontend/src/accessibility/`
- `frontend/tests/`
- `frontend/public/`
- `docs/frontend-results.md`
- `prompts/handoffs/A04.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Confirm D04 integrated flow is working. Build an original evidence-lens composition using React Three Fiber/Drei and procedural reusable geometry. Use the referenced artistic principles, not downloaded unlicensed models or copied brand assets. Keep source/license records for anything actually added.

2. Lazy-load a single landing canvas after semantic content/CTA; keep Three out of review routes. Start with inexpensive materials/instancing and restrained lighting. Do not add postprocessing, transmission shaders or a second animation library unless measured benefit fits the budget.

3. Animate with frame refs, not per-frame React state updates. Cap initial DPR, pause offscreen/background work, dispose GPU resources and handle WebGL context loss. Provide static equivalent for no-WebGL, reduced motion and low-performance conditions.

4. Polish typography, spacing, cards, query history, buttons and all loading/error/empty/partial states. Keep continuous decorative motion away from reading/selection panels. Use explicit status labels and accessible PICO colors rather than color alone.

5. Add clear focus styles, accessible dialogs, 200% zoom behavior, mobile panel stacking, keyboard annotation controls, reduced effects/pause and stable layout. Fix product UI defects surfaced by B03/C03 through coordinated upstream handoffs when backend changes are required.

6. Measure production bundle splits, LCP/INP/CLS where tooling supports them, and frame performance on named demo hardware. Record setup and observed results in docs/frontend-results.md. Targets are not guarantees; explain any unresolved gap instead of inventing a passing score.

7. Extend Playwright coverage for the main review workflow, WebGL fallback, reduced motion, stale edit state and basic keyboard navigation. Manual visual checks must inspect representative screen widths and the real PICO selection experience.

8. Prepare a 30-second premium introduction that goes straight into working review controls. Once B03/C03/A04 are all merged, mark the G3 Level 1 gate in the integration handoff and allow optional branches to proceed.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Core review workflow remains fully usable when WebGL initialization throws and when motion is disabled.
- PICO selection and saved offsets are unchanged by styling/highlight refinements.
- Production landing scene is deferred; document actual core/3D chunk sizes and hardware/profile.
- 390/768/1440px layouts, keyboard flow, focus return, reduced motion and 200% zoom are checked.
- LLM-off Level 1 browser suite still passes after visual changes.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews integrated behavior and dev-C reviews text safety. Publish measured UI results and asset provenance. This is the frontend contribution to G3, not permission to spend the remaining event on additional scenes.

Write `prompts/handoffs/A04.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
