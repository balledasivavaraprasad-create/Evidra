# C01 — Exact-span PICO baseline

You are **dev-C**, the PICO, LangGraph and bounded AI owner (T3). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-c-01-pico-baseline`  
**Priority:** required  
**Target event hours:** 4-12 (coordination window, not continuous coding time)  
**Canonical merge position:** 4 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **D01**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/agents-and-security.md`, `docs/architecture.md`, `skills/bounded-research-agent/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Implement a complete rules-based PICO extractor returning exact evidence spans, with conservative absence handling and a contract the React editor can round-trip safely.

## Ownership

Primary writable scope:

- `backend/app/pico/`
- `backend/tests/pico/`
- `evals/pico/`
- `prompts/handoffs/C01.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Use D01 PicoResult/Span/RecordRevision types and frozen callable port. Implement pure functions under app/pico; no database writes, LLM requirement, HTTP fetch or graph orchestration in this baseline.

2. Extract population phrases, intervention/treatment/dose phrases, comparator cues and measured outcome phrases from original abstract text. Support structured sections but keep a single canonical stored text and offsets. Return multiple supported spans rather than a fluent paraphrase.

3. Define zero-based half-open Unicode code-point positions into exact stored text and hash. Match original text case-insensitively or retain a normalization-to-original mapping. Never compute offsets on whitespace-normalized text and apply them to another string.

4. Validate each span’s label, range and quote. Preserve repeated occurrences explicitly and allow justified cross-label overlap. Reject invalid/stale offsets instead of guessing the first matching quote.

5. Handle missing abstracts with unavailable/manual-review status. If no comparator is supported, return C absent; never invent placebo/control. Distinguish a measured outcome phrase from an inferred treatment-effect conclusion.

6. Create synthetic clinical-style examples and separate expected spans for Unicode/non-BMP characters, repeated drug names, multi-arm comparisons, negation, multiline/structured text and no comparator. Labels are software fixtures, not medical gold standard.

7. Publish extraction-method version and fingerprint inputs. Human edits remain a separate dev-D concern; newly included records need extraction through the service/graph, but the function must not schedule jobs itself.

8. Write evals/pico/baseline.md describing rules and limitations, and provide dev-A exact selection examples showing code-point and UTF-16 positions. Do not assume EBM-NLP supplies comparator labels or download restricted data for this baseline.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Every returned quote equals the exact text slice; invalid span/label/hash is rejected.
- Emoji/non-BMP, combining marks, repeated quote and multiline cases round-trip with documented offsets.
- Absent comparator and absent abstract are explicit states, not filled guesses.
- All four labels can be returned when supported and are deterministic under repeated execution.
- Baseline import/extraction works without any model credentials or network.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-A reviews editor offset examples and dev-B the evidence/evaluation cases. D03 consumes the exact extraction callable and data contract. Freeze the representation before frontend text selection is implemented.

Write `prompts/handoffs/C01.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
