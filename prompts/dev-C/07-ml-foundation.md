# C-ML01 - Required ML foundation, training and inference

You are **dev-C**, responsible for the complete ML feature under the user's explicit cross-layer ownership instruction. Implement this assignment, not another plan. Read [the ML addendum](ML-ADDENDUM-EXECUTION.md) first; it carries the latest user scope and explains the exception to older ownership/optional labels.

**Branch:** `feat/dev-c-ml01-foundation`  
**Priority:** required  
**Prerequisite merges:** D01, C01, B02  
**Placement:** ready after B02; the example queue places this after A02 and before D03, but unrelated original tasks do not wait for it.  
**Expected effort:** 3-5 focused hours, more if permitted labels are missing.

## Read and inspect before editing

Read `AGENTS.md`, `docs/architecture.md`, `docs/algorithms-and-sources.md`, `docs/review-question.md`, `prompts/CI-AND-CONTRACTS.md`, and `skills/literature-pipeline/SKILL.md`. Inspect the real D01/C01/B02 handoffs and merged interfaces. Use the existing locked Python/scikit-learn environment. ML remains independent of LLM keys, embeddings and GPU services.

The existing B05 prompt is not selected for this release; do not ask B to implement it or copy a second competing ML package. B's rules and reviewer eligibility remain unchanged. You own the ML data preparation, model, evaluation and downstream connection contract.

## Owned files and boundary

Create `backend/app/ml_feature/` for domain types, dataset validation, training, artifact metadata and inference; `backend/tests/ml_feature/` for tests; `evals/ml_c/` for reproducible commands, dataset manifests, split definitions and results; and `prompts/handoffs/C-ML01.md` for evidence. These are new isolated feature paths. Do not edit startup, OpenAPI, shared schemas, database migrations, frontend code, B's algorithms, dependency locks, the old plan or other prompt files in this task.

## Implementation

1. **Freeze the ML use case.** Predict review priority for the agreed review question from title/abstract text. Return a score and provenance; do not decide final eligibility. Match each artifact to the question, criteria version and label definition. Treat a different question/criteria as potentially out of scope; never silently apply a topic-specific model to every review.

2. **Prepare permitted labeled data yourself.** Use an appropriately licensed, review-specific labeled source already allowed by the project, or label a modest selected-topic development set with documented criteria. Record source identity, rights, label author/method and limitations. Do not treat missing labels, Maybe, unlabeled papers or machine suggestions as negative human labels. Do not depend on B performing extra labeling. No organizer hidden test data enters training or model selection.

3. **Split before fitting.** Keep duplicate papers and related study reports together. If combining reviews, preserve review scope and prevent cross-review leakage. Record train/validation/test membership hashes. Fit vocabulary and feature weights only on training data; choose settings with validation data; use the holdout only for final evaluation. Use a seed. If data cannot support the split or both classes, return a specific blocker rather than a fabricated quality score.

4. **Implement a small real model.** Use the pinned scikit-learn pipeline with TF-IDF and class-weighted logistic regression as the first implementation. Bound feature count, input size and training resource use in a saved config. Keep preprocessing identical for fit and inference. Training is an explicit offline command, not something triggered at API import or every user request. Validate labels, empty text, empty vocabulary and missing classes.

5. **Provide stable pure interfaces.** Define `train_ranker(dataset, config) -> artifact_manifest`, `load_ranker(trusted_artifact, expected_scope) -> ranker`, and `rank_records(ranker, records, context) -> RankingBatch` or equivalent typed interfaces with these behaviors. A result includes model/version, criteria/question scope, immutable record/text IDs, score, scored/unavailable state and safe reason. Use stable record IDs to break equal scores; missing abstracts are handled explicitly. Scores are not clinical probabilities unless separately calibrated and evaluated.

6. **Version and protect the artifact.** Save model/vectorizer together with feature settings, seed, runtime/sklearn version, dataset/split fingerprints, label mapping, model version and checksums. Only load team-produced files from a server-configured trusted artifact directory. If using Python serialization, loading is allowed only after verifying against a trusted release manifest; a checksum supplied alongside an arbitrary uploaded file does not establish trust. No model upload API, remote-code loading or user-supplied filesystem path. Reject incompatible or corrupt artifacts.

7. **Evaluate actual predictions.** Compare model ranking with a transparent fixed order and the rules ordering on the same held-out records. Report sample/class counts, ranking metrics at declared review budgets, classification metrics only with a declared threshold, inference time and relevant error cases. Report undefined metrics explicitly. Document weak results and topic limits honestly; required delivery does not mean claiming that ML must outperform every baseline.

8. **Make downstream integration easy.** Return plain serializable values with no database writes or FastAPI dependency. Keep eligibility and human-event structures untouched. Document required repository inputs and the planned ML-only response schema. C-ML02 will implement the adapters and UI; do not create implementation tasks for A, B or D.

## Required tests and observable acceptance

- Use small synthetic data for repeatable CI fit/serialize/load/predict tests; distinguish those tests from real quality evaluation.
- Holdout text cannot change the fitted vocabulary or selected hyperparameters. Related records never cross split boundaries.
- Training with one class, missing labels, tiny data or empty vocabulary returns a clear error; it cannot silently train a constant "successful" model.
- The loaded pipeline produces matching scores within a documented tolerance; corrupt, mismatched or untrusted artifacts are rejected.
- Identical inputs and artifact yield stable ordering; missing text, equal scores and out-of-scope criteria are explicit cases.
- Predictions never mutate source records, rule eligibility or reviewer events.

Run the relevant frozen backend checks and the new tests using the active application root. No new package is expected. Do not bypass a lock conflict or require network/model credentials in ordinary CI. Save actual evaluation evidence; an import smoke test or hardcoded score is not an implemented model.

## Handoff and next task

Write `prompts/handoffs/C-ML01.md` with predecessor SHAs, callable signatures/examples, owned paths, actual data provenance, training/evaluation commands, artifact manifest location, measured results, test outcomes, limits and unresolved ML delivery blockers. Retain permitted artifacts in the approved local/release location; do not commit restricted raw data. Include enough instructions to reproduce the artifact without relying on an undocumented local notebook.

C-ML01 is module work, not a delivered web feature. It unblocks C-ML02 only after that task's other dependencies merge. Original D03/C02/A03 work can proceed independently. Prepare a reviewable PR under the normal repository policy; perform a second-pass code review yourself, but do not claim independent approval or auto-merge. Leave existing planning files unchanged.
