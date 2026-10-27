# B02 — Explainable screening criteria and rules

You are **dev-B**, the deduplication, screening and ML evaluation owner (T2). Execute this as a scoped implementation assignment, not another architecture proposal. Deliver working code and evidence for the scope below; do not claim unrelated project completion.

**Branch:** `feat/dev-b-02-screening-rules`  
**Priority:** required  
**Target event hours:** 8-18 (coordination window, not continuous coding time)  
**Canonical merge position:** 6 of 24; use `prompts/EXECUTION-AND-MERGE-ORDER.md` for permitted parallel work.

## Prerequisites

Required merged prompts: **B01**

Read `AGENTS.md`, `audit.md`, `prompts/README.md`, `prompts/CI-AND-CONTRACTS.md` and the execution/merge order. Then read `docs/algorithms-and-sources.md`, `docs/architecture.md`, `skills/literature-pipeline/SKILL.md`. Read prerequisite handoffs in `prompts/handoffs/<ID>.md`, and verify their merged commit and actual exported interfaces. Documentation or a green planning-only check is not proof a prerequisite application feature exists.

Fetch/update from the shared integration branch before starting. Use the named short feature branch from the prerequisite-complete `main`. You may sketch pure functions or mock layouts earlier, but do not merge or invent replacements for missing dependencies. If an interface is genuinely missing, record the exact contract request and owner; continue independent work and keep this PR blocked until the upstream change is merged. Do not silently edit another owner's contracts.

## Outcome

Implement metadata-first, explainable screening with a complete rules baseline and honest Maybe states; write the selected review criteria before integrating model experiments.

## Ownership

Primary writable scope:

- `backend/app/screening/`
- `backend/tests/algorithms/screening/`
- `evals/screening/`
- `docs/review-question.md`
- `prompts/handoffs/B02.md` for your evidence and handoff.

Respect exclusions implied by the other developers' ownership. Dev-D owns Pydantic/OpenAPI contracts, migrations and Python locks; dev-A owns generated TypeScript and frontend locks. Raise a small prerequisite contract/dependency PR through that owner when needed. Do not hand-edit a lock, bypass peer checks, replace the stack, or reformat unrelated files. Shared audit/CI stage updates are restricted to the explicitly assigned prompt and integration captain.

## Implementation

1. Review docs/review-question.md with the actual selected topic. If no team choice exists, retain its explicitly provisional sample and configurable criteria; do not claim medical validation or organizer approval. Define criterion IDs, active status, reasons and metadata/text detection strategy.

2. Use D01 screening contracts and implement pure app/screening functions taking immutable records and a criteria version. Return pass/fail/unknown per criterion, evidence location/value, method/source, rule version and aggregate eligibility.

3. Prefer language/publication type/species metadata where available. Detect absent metadata using documented conservative text methods. Keep disagreements visible; metadata-first does not mean silently ignoring contradictory content.

4. Add context/negation-aware rules for animal-only, simulation-only, case report and topic population/intervention/design criteria. Avoid excluding human trials that mention animal background or statistical models. Missing abstract, mixed population or insufficient evidence should normally yield Maybe.

5. Aggregate only active criteria: supported fail yields Exclude with reasons; supported necessary passes yield Include; otherwise Maybe. Preserve all criterion evidence rather than only the winning rule. Human overrides belong to dev-D, not your algorithm.

6. Provide reproducible fingerprints covering record text/metadata, criteria and method versions. Changes to active criteria invalidate affected results. Do not use query ID alone as a screening cache key.

7. Build a small development and holdout fixture split with justified expected decisions. Keep paper/study families together. Report examples and known limitations; do not produce an “accuracy” number from the same fixtures used to tune rules and call it generalization.

8. Finish rules before classical ML. No model dependency, training set download or LLM key may be needed to import the module or produce baseline outputs. Leave a narrow optional ranking interface for B05.

## Invariants and error handling

Keep the React + Python/FastAPI + SQLite + LangGraph architecture. Level 1 must work without an LLM key. Preserve source records, hidden exclusions/duplicates and human history; same study does not imply same paper. Models cannot commit human decisions. Exclusion needs a reason; uncertain evidence is Maybe. PICO spans use the exact immutable text/hash and half-open Unicode code-point offsets. Backend services enforce workspace scope, idempotency and stale-version conflicts. Handle partial/error/empty results explicitly, and never present fixtures as live data.



## Verification

Run the relevant frozen installs and checks from `prompts/CI-AND-CONTRACTS.md`; the assigned feature must have meaningful tests, not only dependency imports. Do not add `--passWithNoTests`, broad skips or `continue-on-error` to make a green check. Add/update these observable cases:

- Animal-only versus human-trial-with-animal-background, simulation-only versus human-statistical-model examples differ correctly.
- Missing/short/mixed-language abstracts abstain when evidence is insufficient.
- Every Exclude has an active criterion and evidence; disabling a criterion changes only justified results.
- All necessary unknowns yield Maybe, not a fabricated confident label.
- Same inputs and versions yield deterministic outputs/fingerprints; one-class/absent ML data cannot crash rules.

Record exact commands, exit results, environment and any untested browser/live-provider behavior. No network/model call is needed in ordinary CI; use controlled fixtures/transports. A manual live check is separate, within quotas and only with approved runtime configuration. Fix failures within your scope; coordinate cross-owner fixes explicitly.

## Handoff

Dev-D reviews integration output and dev-C evidence semantics. Hand D03 a pure screening implementation, expected fixtures and explicit criteria assumptions; update the review-question worksheet without presenting it as an approved clinical protocol.

Write `prompts/handoffs/B02.md` with: requirement IDs addressed; changed paths; provided interfaces and example payloads; predecessor merge SHAs; migration/lock changes (or none); commands/results; known limitations; remaining contract requests; and which prompts are now unblocked. Link the branch/PR once a team remote exists. Keep implementation, tested and deployed statuses separate. Root `audit.md` is consolidated by the captain; do not concurrently rewrite it from every developer branch.

Before requesting merge, update from `main`, resolve semantic conflicts, rerun affected checks and obtain the designated reviewer from the master order. Prepare a focused commit/PR through the team's configured Git workflow. Do not auto-merge, force-push `main`, publish a deployment, create a remote, or claim a GitHub Actions result that has not actually run. If the task is run without a remote, deliver the local changes and handoff with that limitation.
