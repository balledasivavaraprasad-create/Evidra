# C05 — Optional budgeted LLM gateway and validated extraction

You are **dev-C**, the PICO, LangGraph and bounded AI owner (T3). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-c-05-llm-assistance`  
**Priority:** optional  
**Target event hours:** 36-48 (coordination window, not continuous coding time)  
**Canonical merge position:** 20 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **C03, B03, A04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/agents-and-security.md`, `docs/architecture.md`, `skills/bounded-research-agent/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Implement optional LLM assistance through the narrow gateway with validated evidence, enforceable budgets and a deterministic fallback; keep model access out of the core dependency path.

## Ownership

Primary writable scope:

- `backend/app/gateway/`
- `backend/app/pico/llm.py`
- `backend/tests/gateway/`
- `backend/tests/pico/test_llm.py`
- `evals/llm/`
- `prompts/handoffs/C05.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Confirm G3 and use C03’s reviewed gateway contract. Implement a direct approved-provider HTTPX adapter and a protocol-compatible mock. Optional LiteLLM may remain an external future service; do not add its SDK/dependency tree to the core backend without a separately reviewed need.

2. Accept only server-created task/model/context values and allowlisted base URLs/models from configuration. Keep credentials server-side. Enforce timeout, input/output sizes, token/call/spend reservation and bounded retry before dispatch; do not let user payloads override policy.

3. Handle provider outage, malformed response, policy rejection and budget exhaustion with typed failures. Do not retry policy blocks or fallback to a provider with weaker privacy/policy. AI validation outage disables the AI request while rules/manual review continue.

4. Implement optional LLM PICO extraction in app/pico/llm.py: one immutable abstract/revision, exact schema and evidence quote/offset output. Validate every range/quote/hash and repeated occurrence. At most one repair attempt within the total budget; then rules/manual fallback.

5. Optional screening explanations may explain saved criterion evidence but must not automatically commit eligibility. Keep model output/provenance separate from human events. No tool may change criteria, export data or execute arbitrary commands.

6. Cache only accepted outputs under workspace/corpus/text/criteria/model/prompt/schema/policy identity. Preserve resolved model ID and token/cost metadata without retaining secrets/private notes in logs.

7. Compare rules versus LLM assistance on the same held-out PICO/explanation cases. Report P/I/C/O quality, invalid-span rate, abstention, latency and cost; use explicit “not run” if no approved provider key is available. Mock tests validate plumbing, not model quality.

8. Publish tested module interfaces and default-off configuration for D06. Do not expose a new API route or UI yourself. If no measured value or time remains, retain an evaluated experiment and keep release AI disabled.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Unsupported provider/model/task, oversized payload and budget exhaustion prevent outbound dispatch.
- Provider timeout, 429, malformed JSON and failed guardrail produce bounded fallback.
- Forged citation/invalid offset/repeated-quote ambiguity cannot persist a PICO result.
- Injected abstract cannot enable a tool or mutate reviewer decisions; secret canaries do not enter outputs/logs.
- Rules-only flow works with no key and provider failure; actual model evaluation is separated from mocked contract tests.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews auth/config/endpoint integration needs and dev-B evaluation methodology. C06 consumes this adapter; D06 decides release exposure. This prompt alone does not claim a delivered chatbot or model accuracy.

Write `prompts/handoffs/C05.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
