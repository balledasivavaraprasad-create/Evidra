# B05 — Optional classical ML ranking with leakage-safe evaluation

You are **dev-B**, the deduplication, screening and ML evaluation owner (T2). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-b-05-ml-ranking`  
**Priority:** optional  
**Target event hours:** 36-48 (coordination window, not continuous coding time)  
**Canonical merge position:** 19 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **B03, A04, C03**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/algorithms-and-sources.md`, `docs/architecture.md`, `skills/literature-pipeline/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Add classical ML only as an evaluated optional prioritization aid, preserving the rules/manual baseline and avoiding label leakage or unsafe model loading.

## Ownership

Primary writable scope:

- `backend/app/screening/ml/`
- `backend/tests/algorithms/ml/`
- `evals/ml/`
- `prompts/handoffs/B05.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Confirm G3 is complete before training. Use the baseline/holdout protocol from B03; keep paper/study duplicates and whole reviews together when possible. Obtain permitted labels with provenance; do not download/repackage restricted data just to make the experiment look larger.

2. Implement a versioned TF-IDF plus class-weighted logistic-regression pipeline in screening/ml. Fit vectorizer/weights only on training data. Handle empty vocabulary, tiny samples, missing classes and missing labels by returning a typed unavailable result while rules continue.

3. Keep model scores separate from deterministic eligibility and human events. Initial use is review ordering or a disagreement suggestion, never automatic exclusion. Do not call an uncalibrated score a clinical probability.

4. Freeze training/split hashes, seed, feature config, sklearn/runtime version, artifact checksum and label mapping. Load only team-generated trusted artifacts with validated metadata; no arbitrary user-uploaded pickle/joblib execution.

5. Compare against the rules and a transparent fixed ordering on the same holdout. Report recall-at-k or work-saved only with a declared threshold/stopping rule, along with computation and inference time.

6. Retain the model only if observed results justify it; otherwise deliver a documented negative result and keep runtime ranking disabled. An assigned experiment can conclude “not worth integrating” without falsifying its outcome.

7. Publish a pure optional ranking callable compatible with frozen ports. New API fields must come through dev-D’s additive contract change; D06 decides release wiring. Do not modify database schemas, core pyproject or frontend directly.

8. Prepare evals/ml/results.md with reproducible command, actual metrics, errors and limits. Keep expensive retraining out of ordinary PR CI; tests use a tiny deterministic synthetic dataset and no network.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- One-class, insufficient-label, missing-artifact and empty-vocabulary cases keep baseline available.
- No held-out text participates in vectorizer fitting or model selection.
- Artifact version/hash/schema mismatch is rejected; untrusted model files are not loaded.
- Ranking never changes a stored eligibility decision or human event.
- Comparison is reproducible and the adoption/cut recommendation follows evidence.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-C reviews ML evaluation and dev-D the ranking interface. D06/B06 consume only the selected tested artifact/method; an unintegrated experiment is labeled as such. This optional prompt is never a hard prerequisite for release.

Write `prompts/handoffs/B05.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
