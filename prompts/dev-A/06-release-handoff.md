# A06 — Deployment packaging, browser acceptance and final handoff

You are **dev-A**, the frontend/full-stack owner (T1). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-a-06-release-handoff`  
**Priority:** required  
**Target event hours:** 62-72 (coordination window, not continuous coding time)  
**Canonical merge position:** 24 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **A04, D06, B06, C03**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/frontend-design.md`, `docs/architecture.md`, `skills/premium-research-ui/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Package the implemented application for a reproducible handoff, finish the report/demo, and validate the actual release with honest feature and hosting limits.

## Ownership

Primary writable scope:

- `frontend/`
- `infra/`
- `README.md`
- `docs/report.md`
- `docs/demo-script.md`
- `docs/release-checklist.md`
- `docs/frontend-results.md`
- `audit.md`
- `prompts/handoffs/A06.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Read D06 operations and B06 evaluation handoffs plus all selected optional handoffs. A05 is required only if the release claims Level 2 UI; C06 requires D06 endpoint wiring before any assistant UI is added. Do not block Level 1 release on deliberately deferred extras.

2. If AI endpoints are selected and wired, add a modest assistant/extraction proposal panel in owned frontend paths using authorized contracts, evidence citations, budgets/unavailable state and explicit human apply action. Allocate at most 1–2 focused hours; if this threatens release, keep AI an evaluated nonexposed module and report that status. Never imply a backend module alone is a delivered user feature.

3. Create single-host deployment packaging under infra/: React build, same-origin /api routing, API plus worker, persistent local data volume, pinned runtime images/digests verified at packaging, no embedded secrets. Runtime image digest selection is a release task, not a fabricated placeholder. Public deployment only through the team’s chosen authorized platform.

4. Implement startup/readiness/shutdown scripts using D06 interfaces. Validate that SPA fallback does not swallow API errors, browser asset paths work, API origin/session configuration is correct and a restart preserves reviewer data. Keep local demo instructions available if judge hosting requirements remain unknown.

5. Write a stranger-runnable README covering prerequisites, frozen installs, migrations, source/contact configuration, LLM-off mode, starting API/worker/frontend, fixtures vs live data, tests, backup/restore, known limits and actual deployment access. Do not publish private abstracts, credentials or unrestricted datasets.

6. Assemble docs/report.md from actual domain evidence within the three-page submission constraint, with assumptions/estimates labeled and no fabricated metrics. Keep the one-page Level 2 design as a separate artifact; confirm final format/page count if rendering.

7. Write docs/demo-script.md using the five-minute timing: short premium hero, small live search/import, duplicate override, screening reason, PICO edit, bonus snapshot if implemented, CSV/run log and measured result. Include a clearly labeled outage fallback, not a fake live demo.

8. Run final clean installation, all active CI checks, browser/reduced-motion/WebGL fallback checks and deployment persistence rehearsal. Finish docs/release-checklist.md with evidence, selected/cut features, unresolved organizer details and owner. Consolidate audit.md and prepare the release PR/tag recommendation; do not merge/publish without the team’s actual release workflow.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- A teammate can run the documented setup from a clean checkout with no developer-local paths or hidden packages.
- Browser Level 1 and any enabled Level 2/AI flows pass against release configuration; disabling AI retains the core workflow.
- Container/local service restart and safe backup restore preserve decisions and selected snapshots.
- No frontend secrets, fake metrics, dead optional buttons or accidental dataset dumps ship.
- Demo rehearses within five minutes and final report reflects implemented/tested behavior only.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Request dev-D review for operations/auth and dev-B/dev-C review for reported methods and limitations. Deliver the final release checklist, reviewable commit/PR and reproducible commands; explicitly distinguish locally verified, CI-verified and deployed states.

Write `prompts/handoffs/A06.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
