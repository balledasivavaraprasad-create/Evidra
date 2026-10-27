# C03 — Agent boundaries, replay safety and baseline security

You are **dev-C**, the PICO, LangGraph and bounded AI owner (T3). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-c-03-agent-security`  
**Priority:** required  
**Target event hours:** 28-36 (coordination window, not continuous coding time)  
**Canonical merge position:** 13 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **C02, D04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/agents-and-security.md`, `docs/architecture.md`, `skills/bounded-research-agent/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Harden the integrated baseline against replay errors, unauthorized agent actions and untrusted content, and define the narrow gateway boundary before optional model work.

## Ownership

Primary writable scope:

- `backend/app/workflows/`
- `backend/app/gateway/`
- `backend/tests/workflows/`
- `backend/tests/agent_security/`
- `docs/agent-security-results.md`
- `prompts/handoffs/C03.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Exercise the D04 integrated graph and authenticated resume endpoints. Trace all authority boundaries: browser → API → services → graph → tool/model. Record assets/threats in docs/agent-security-results.md with actual tested evidence.

2. Add negative tests for forged workspace/thread/event IDs, stale expected versions, repeated resume and checkpoint replay. Route API authorization defects to dev-D through a small follow-up; do not assume a random UUID is authorization.

3. Introduce a narrow gateway Protocol/result model only within existing frozen contracts or a reviewed dev-D contract addition. Define task/model alias/context/schema/budget inputs, typed failure and deterministic fallback. No live provider call is needed for this required baseline step.

4. Ensure abstracts, citations, tool outputs and model-like fixture text are data, not executable instructions. No arbitrary SQL/shell/URL tool, no credentials in prompts, no mutation tool for reviewer decisions. Include indirect prompt-injection fixtures that attempt to override criteria or expose secrets.

5. Validate output/text evidence deterministically and fail unsupported/unknown commands closed. Specify runtime call/time/token limits for optional agents, but do not require an LLM to pass the baseline. Guardrail failure means AI unavailable and rules/manual review remain available.

6. Inspect logging/checkpoint payloads for credentials, private notes, unbounded abstracts and accidental exception dumps. Keep trace IDs, hashes, method versions and safe errors instead of raw secrets or hidden reasoning.

7. Run restart/cancellation/partial-failure drills and fix own workflow defects. Coordinate dev-A XSS/selection and dev-D CSV/SSRF/auth checks through explicit failing cases; a generic security checklist is not evidence.

8. Publish passed/failed/not-tested cases, residual risks and the exact optional model adapter contract. Contribute PICO validation results to the Level 1 gate. Do not claim penetration testing or perfect injection immunity.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Unauthorized graph resume and cross-workspace citation/event access are rejected at service boundaries.
- Injected abstract cannot cause DB mutation, external arbitrary request or secret disclosure.
- Invalid evidence/span and unknown tool/task fail validation without breaking deterministic review.
- Replayed/duplicated graph operations preserve one committed effect and reviewer history.
- Logs and checkpoints contain no configured secret canary; LLM-off Level 1 stays green.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews authority and transaction boundaries; dev-A addresses UI attack fixtures. This is C’s contribution to G3 and the prerequisite for C05. Hand B06 actual PICO/agent evidence and honest remaining limitations.

Write `prompts/handoffs/C03.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
