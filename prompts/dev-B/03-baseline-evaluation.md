# B03 — Baseline evaluation and adversarial algorithm regression

You are **dev-B**, the deduplication, screening and ML evaluation owner (T2). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-b-03-baseline-evaluation`  
**Priority:** required  
**Target event hours:** 28-36 (coordination window, not continuous coding time)  
**Canonical merge position:** 12 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **B02, D04**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/algorithms-and-sources.md`, `docs/architecture.md`, `skills/literature-pipeline/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Validate the required dedup/screening baseline on independent fixtures and expose its failure cases before the team adds optional complexity.

## Ownership

Primary writable scope:

- `evals/`
- `backend/tests/algorithms/`
- `backend/app/dedup/`
- `backend/app/screening/`
- `prompts/handoffs/B03.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Exercise merged D04 services with the actual B01/B02 modules; add integration-facing expectations where previous unit fixtures were insufficient. Keep persistence fixes with dev-D and UI fixes with dev-A.

2. Create an evaluation manifest with dataset/fixture provenance, split identifiers, counts, method hashes, seed and environment. Use synthetic cases immediately; use real abstracts only with provenance and permissible handling. Do not redistribute restricted training data.

3. Measure duplicate pair precision/recall/F1, blocking recall, false-merge examples and uncertain-pair workload. Include group-level consistency and deterministic representative checks, not just a few high-similarity matches.

4. Measure eligibility confusion matrix, include recall, exclude precision, macro-F1 or balanced accuracy, Maybe rate and reason completeness. Explain class imbalance and the reference-label source. Handle zero-denominator metrics explicitly.

5. Expand adversarial cases: missing DOI, punctuation/Unicode titles, conflicting identifiers, same study separate report, negation, mixed age/species, missing abstract, date ambiguity and duplicate order permutation.

6. Use a labeled subset with independent review where available; document disagreements rather than hiding them. Freeze a holdout before tuning. Distinguish team-created fixture results from unknown organizer tests.

7. Fix actual algorithm defects supported by failing cases, add the regression fixture and rerun relevant checks. Do not change method thresholds to memorize expected IDs or alter the hidden-test harness.

8. Publish evals/baseline-results.md with actual measured outputs and clear estimates for reviewer time if not directly observed. Report residual false negatives/merges and recommend whether optional ML is worth attempting. G3 requires safe deterministic baseline behavior, not invented numerical scoring thresholds.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Evaluation scripts regenerate counts/metrics from saved predictions and references, with documented missing/abstaining labels.
- Duplicate and screening fixtures remain split by paper/study; train/tune data do not leak into holdout.
- False-merge/false-exclusion examples are surfaced and high-impact defects have regression tests.
- LLM-off integrated workflow still passes after algorithm fixes.
- Reported numbers match actual files; no organizer score or clinical accuracy claim is fabricated.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-C reviews evaluation design and dev-D checks integration implications. This is B’s contribution to G3 and the basis for deciding whether B05 provides value. Publish pending domain questions and reproducible result commands.

Write `prompts/handoffs/B03.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
