# B06 — Final evaluation evidence and report contribution

You are **dev-B**, the deduplication, screening and ML evaluation owner (T2). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-b-06-final-evaluation`  
**Priority:** required  
**Target event hours:** 60-66 (coordination window, not continuous coding time)  
**Canonical merge position:** 23 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **B03, D06**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/algorithms-and-sources.md`, `docs/architecture.md`, `skills/literature-pipeline/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Produce the final reproducible algorithm/evaluation contribution for the methods actually included in the release, without inflating results from optional experiments.

## Ownership

Primary writable scope:

- `evals/`
- `docs/report-evaluation.md`
- `backend/tests/algorithms/`
- `prompts/handoffs/B06.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Inspect D06’s selected-feature list and all merged algorithm changes. If B04/B05 or C05/C06 were attempted, record whether they are integrated, module-only or cut. Do not require missing optional branches to complete this prompt.

2. Rerun the frozen dedup/screening evaluation on the release candidate commit. Include the mandatory edge cases and any actual defect regressions; keep hidden organizer data separate if it has become available.

3. Collect C01/C03/C04/C05/C06 PICO/agent evidence as applicable rather than inventing results outside your scope. Report P/I/C/O separately, with comparator limitations and exact-span validity.

4. Compare baseline versus adopted improvements using the same split and workload. Separate measured elapsed/reviewer task time from estimates, give assumptions and compute context, and report failure/abstention rates alongside quality.

5. Write docs/report-evaluation.md as a concise contribution suitable for a three-page final report. Include data provenance/rights, metrics/counts, simplest approach tried, reasons for keeping/replacing it and honest limitations.

6. Ensure result tables can be regenerated from tracked scripts/configs and appropriately retained data hashes. Do not commit copyrighted/private raw abstracts or credentials as a convenience for reproducibility.

7. Hand dev-A a short demo evidence summary and concrete correctly labeled examples. Do not replace the actual live API demo with an evaluation screenshot or claim unknown judge scores.

8. If a late material defect is found, create a minimal owner-scoped fix and regression evidence, then rerun only affected evaluations. Keep the release feature freeze; no new training architecture in the final hours.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Every reported figure has saved inputs/predictions/provenance or is explicitly an estimate with assumptions.
- Final metrics use the actual selected method versions and split; no cherry-picked duplicate leakage.
- Baseline still operates without ML/LLM artifacts and credentials.
- Optional results are clearly distinguished from delivered functionality.
- Report text does not claim clinical validation, hidden organizer scores or unperformed tests.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-C reviews model/evidence claims and dev-D confirms release versions. A06 consumes this report contribution and demo evidence. Deliver reproducible commands and limitations, not a polished table of invented results.

Write `prompts/handoffs/B06.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
