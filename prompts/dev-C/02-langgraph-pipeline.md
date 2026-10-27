# C02 — Durable LangGraph pipeline and human review subgraph

You are **dev-C**, the PICO, LangGraph and bounded AI owner (T3). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-c-02-langgraph-pipeline`  
**Priority:** required  
**Target event hours:** 18-26 (coordination window, not continuous coding time)  
**Canonical merge position:** 9 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **C01, D03**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/agents-and-security.md`, `docs/architecture.md`, `skills/bounded-research-agent/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Implement durable LangGraph orchestration around the already working domain services, with replay-safe effects and resumable human review while keeping the core pipeline deterministic.

## Ownership

Primary writable scope:

- `backend/app/workflows/`
- `backend/tests/workflows/`
- `prompts/handoffs/C02.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Read D03 service ports and D02 job extension contract; call those services rather than writing duplicate DB logic. Implement a graph facade in app/workflows/pipeline.py with explicit typed input/output that D04 can wire into the worker.

2. Create nodes for validation/loading, missing-record retrieval/normalization as appropriate, dedup proposals, persisted groups, screening, included-only PICO, snapshot publication and run summary. Avoid repeatedly storing large abstract bodies in graph state; keep IDs, fingerprints, versions, budget counters and bounded errors.

3. Use the locked persistent SQLite checkpointer and namespaced thread IDs from trusted workspace/job identities. Record graph version and plan for incompatible checkpoint layouts. Never use in-memory persistence as the application restart strategy.

4. Place uncertain pair reviews in a queue so unaffected papers can continue. A blocking conflict/review uses a small separate interrupt/resume subgraph with stable interrupt ordering and JSON-serializable payloads.

5. Resume only using a domain event ID validated through the D03 service. Do not treat caller-supplied graph state/thread ID as authority. Keep approval nodes separate from side effects; never catch the LangGraph interrupt with an overly broad exception handler.

6. Before/after each effect, use domain idempotency/fingerprint checks and committed outputs. Checkpoint and business DB are separate transactions; a replay after domain commit must not duplicate an event, import or output. Do not promise exactly-once provider calls.

7. Add bounded transient retry/cancellation logic and per-step run traces without secrets/full private notes. Permanent schema/policy errors stop the relevant stage visibly. Core graph must run with LLM_ENABLED=false.

8. Create durable checkpoint tests using a reopened connection/process boundary and an executable example for D04. Do not edit the dev-D-owned worker directly; supply the facade and an exact wiring handoff.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Fixture corpus runs end to end through graph service calls with no LLM/network.
- Interrupt persists, graph/checkpointer closes, new process/connection resumes using the approved domain event.
- Crash after business commit but before checkpoint yields one domain effect after replay.
- Repeated resume/cancel and unknown/stale event IDs are handled safely; other groups can still proceed.
- Graph/state size is bounded and traces have stage/revision/attempt/error context without credentials.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews facade/transaction integration and dev-B deterministic behavior. D04 performs the worker/API wiring after merge. Publish method and graph versions, pending-review payloads and tested failure boundaries.

Write `prompts/handoffs/C02.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
