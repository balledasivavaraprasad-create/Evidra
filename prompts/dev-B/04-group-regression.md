# B04 — Group merge/split and cross-version regression suite

You are **dev-B**, the deduplication, screening and ML evaluation owner (T2). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-b-04-group-regression`  
**Priority:** bonus  
**Target event hours:** 42-48 (coordination window, not continuous coding time)  
**Canonical merge position:** 16 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **B03, D05**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/algorithms-and-sources.md`, `docs/architecture.md`, `skills/literature-pipeline/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Validate and, within the dedup module, correct the merge/split behavior used by the new snapshot services, with particular attention to preserving reviewer work.

## Ownership

Primary writable scope:

- `backend/app/dedup/`
- `backend/tests/algorithms/dedup/`
- `backend/tests/level2/test_group_regression.py`
- `evals/dedup/`
- `prompts/handoffs/B04.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Use the actual D05 lineage/conflict contracts and immutable snapshot fixtures. Do not create alternative group tables or write persistence logic from the algorithm module.

2. Build scenarios where a new source record bridges previously separate groups, exact identifiers conflict, fuzzy candidates have a cannot-link decision, and the human explicitly reverses a mistaken duplicate decision.

3. Test component validation and deterministic representatives through accepted/rejected edges. Group membership order must not depend on query arrival or batch page order. Record proposals separately from human confirmation.

4. Exercise include/exclude and agreeing parent decisions through D05 integration services. Assert conflict creation/provenance and export omission without implementing a hidden decision winner in B code.

5. Exercise split after a merged-group decision and changed representative/text. Original events must remain attributable; merged-scope decisions become pending for child groups, and PICO stays tied to old text until validated.

6. Compare pre-change and restored snapshot partitions using immutable record/revision identity, not merely count equality. Test both the global accumulated dedup universe and active-query membership semantics.

7. Fix dedup algorithm issues only under owned paths and report DB/lineage bugs to dev-D as a blocking follow-up. C04 must receive stable fingerprints/affected-group semantics before its incremental logic begins.

8. Keep fixtures and measured false-merge cases in evals/dedup and backend/tests/level2/test_group_regression.py. Do not activate global Level 2 CI; D06 does that after frontend tests exist.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Bridge changes only the new snapshot; original partition and representative remain exact on restore.
- Rejected edges/cannot-link constraints survive rerun and prevent contradictory transitive unions.
- Different publications from one trial remain separate through query additions.
- Conflicting decisions are visible and excluded from included export until explicitly resolved.
- Split/representative-change scenarios preserve annotation/event provenance rather than silently transferring it.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews domain expectations and dev-C consumes the affected-group/fingerprint behavior for C04. Hand A05 the concrete conflict/restore fixture story. If a D05 defect blocks correctness, report it precisely and wait for the small upstream fix.

Write `prompts/handoffs/B04.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
