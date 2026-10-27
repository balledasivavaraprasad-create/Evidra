# C06 — Optional bounded, cited corpus RAG assistant

You are **dev-C**, the PICO, LangGraph and bounded AI owner (T3). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-c-06-bounded-rag`  
**Priority:** optional  
**Target event hours:** 46-56 (coordination window, not continuous coding time)  
**Canonical merge position:** 21 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **C05**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/agents-and-security.md`, `docs/architecture.md`, `skills/bounded-research-agent/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Build a bounded evidence assistant over the authorized saved corpus, with citations and abstention, and justify the agent loop against simpler retrieval.

## Ownership

Primary writable scope:

- `backend/app/retrieval/`
- `backend/app/workflows/assistant.py`
- `backend/tests/retrieval/`
- `backend/tests/ai/`
- `evals/rag/`
- `prompts/handoffs/C06.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Use C05’s gateway and the D03/D04 current corpus/snapshot authorization model. Do not depend on bonus query-edit features unless they actually exist. Retrieval scope is the selected workspace and corpus revision, including exact text revision IDs.

2. Implement SQLite FTS5/keyword retrieval through D01's narrow read-only repository port implemented by D03. Build a bounded in-memory FTS5 index from authorized rows for the selected corpus revision; never mutate the application database from the assistant module. Key any cache by workspace plus corpus revision, enforce record/byte limits, parameterize queries, escape FTS syntax and invalidate on revision changes. Return an explicit limit/error result rather than silently claiming a partial index covers the corpus. Persistent FTS migrations and vector embeddings are deferred, avoiding an extra schema dependency in this 72-hour scope.

3. Route only explain_screening, suggest_query and propose_pico tasks. Retrieve bounded chunks with immutable citation handles, offsets and criteria version. No arbitrary web search, source URL fetch, shell or SQL-generation tool is exposed.

4. Allow at most one controlled reformulation/retrieval follow-up when evidence is insufficient. Enforce configured retrieval rounds/chunks/input length, total model calls/repair count, tokens, cost and wall deadline in code. Do not nest retry loops that multiply the budget.

5. Validate citations belong to authorized retrieved text and current snapshot; verify quotes/ranges. If support is missing or ambiguous, abstain. Citation existence alone does not establish semantic correctness; include human-rated support cases.

6. Return a proposal/result schema with evidence, limitations and version provenance. Applying query/criteria/PICO changes is an explicit separate human domain command; the assistant cannot update review events.

7. Create backend/tests/ai/test_assistant_boundaries.py plus retrieval fixtures for cross-workspace leakage, stale citations, prompt injection, unsupported task, zero retrieval, repeated text and exceeded budget. Mock model/provider calls in CI.

8. Compare lexical retrieval only, one-pass cited response and bounded agent loop on identical held-out questions. Publish actual support/coverage/abstention/latency/cost evidence and a keep/cut recommendation. Hand D06 the API integration contract and A06 the small optional proposal panel requirements; do not assume module-only code is a delivered UI.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Retrieval cannot access another workspace or a record revision outside the selected corpus.
- No evidence yields abstention; fabricated/out-of-scope/stale citations fail validation.
- Maximum retrieval/model/repair calls and wall budget hold even under repeated provider errors.
- Injected corpus text cannot change tools, bypass policy or persist human decisions.
- Agent-loop benefit is evaluated against simpler baselines; no model evaluation is claimed from mock outputs.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews read-only repository and endpoint authorization; dev-B reviews evaluation. D06 wires selected backend exposure and promotes AI CI; A06 adds UI only if time permits. Report module-tested, provider-tested and user-delivered statuses separately.

Write `prompts/handoffs/C06.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
