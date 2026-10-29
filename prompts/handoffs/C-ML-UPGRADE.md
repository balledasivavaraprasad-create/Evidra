# C-ML-UPGRADE implementation handoff

Date: 29 October 2026. Owner: dev-C scope, executed locally by Codex at the user's request. Branch: `codex/dev-c-advanced-ml`. This is a standalone addendum, not an automatic execution of a new original-plan task.

## Implemented

- Optional pinned XGBoost/CatBoost benchmark group, with CPU-only XGBoost for Linux and no CUDA/NCCL dependency in the resolved graph.
- ColumnTransformer title/abstract/character TF-IDF, numeric lengths, missingness/category handling, safe empty text branches and bounded fold-fitted SVD. No post-review labels/IDs enter the feature matrix.
- Actual bounded model comparison with disjoint training, calibration, selection and test partitions; full requested classification metrics, AP/ranking/WSS, calibration evidence, bootstrap intervals, latency evidence and plotted results.
- Bounded retrospective active-learning experiment with relevance, uncertainty and exploration; only already-reviewed labels reach fitting. Optional correctly transformed train-internal early-stopping helper.
- Fixed demonstrated server-scope bypass, ignored criteria constraint, stale model-policy cache, stale cached human-status projection, old ranker method/record-field mismatches, implicit unknown-to-negative labels, premature score rounding and per-record inference calls.
- Both public ranking APIs now use the canonical scoped scoring service. Explicit legacy artifact calls remain supported. No shared API schema or DB migration was needed.
- Model caches include full manifest/model digest, trusted question/criteria scope, representative identity and text. Old machine outputs are retained; cache refresh never changes human events. Inference batches and representative/decision queries are bounded/batched.
- Runtime supports new feature bundles through the existing artifact interface, verifies schema/sklearn/hash before trusted local deserialization, and memoizes verified model bytes.
- ML page now persists confirmed reviewer actions through the real API, requires exclusion evidence, keeps optimistic concurrency, rejects mutations of sample data, exposes unavailable state, removes fabricated score rationales/probability claims, and distinguishes ranking refresh from training.

## Measured result and active model

See [benchmark report](../../evals/ml_upgrade/README.md). All four required families ran on 2,142 usable public labelled Wilson-review records; held-out test support was 428 records/23 positives. Development selection retained original-style TF-IDF/logistic regression. Test accuracy/precision/recall/F1 for that retrained benchmark baseline were 0.8715/0.2838/0.9130/0.4330; AP 0.6362. No clinical or cross-topic accuracy claim follows from those values.

**The existing metformin artifact remains active.** A Wilson-review candidate must not replace it. The new benchmark/feature infrastructure is usable, but real-world improvement for the current metformin topic remains unverified without suitable human-labelled topic data. No booster was promoted simply to satisfy an algorithm preference.

## Verification evidence

- Starting baseline: `backend/.venv/bin/python -m pytest -q backend/tests` — 277 passed, 2 pre-existing deprecation warnings.
- Four targeted reproductions failed before the fixes: scope override, changed-model cache, stale human-status cache and ignored criteria constraint.
- Final backend pytest result and counts are recorded in `evals/ml_upgrade/verification.json`.
- Scoped Ruff, frozen lock verification, frontend typecheck/unit/build, generated API drift, and disposable browser test results are recorded in that verification file.
- Browser command, from frontend: `npm exec -- playwright test --config playwright.ml-upgrade.config.ts`. It creates its own synthetic database and scoped test model on isolated ports 8891/4281, checks Include persistence across reload, requires exclusion evidence, then checks Exclude persistence across reload. It does not touch a user's real database.
- Public benchmark command/configuration/splits/predictions and comparison figure are in `evals/ml_upgrade/wilson-final/`. Active simulation is in `evals/ml_upgrade/active-learning.json`. Raw downloaded abstracts remain outside the repository.
- Stage validation and original 24-task DAG validation pass; the task DAG is unchanged.
- Full-repository Ruff has **62 existing findings**, also reproduced against an exported pristine HEAD baseline. No findings were introduced; changed ML files pass the scoped check. Do not auto-fix other owners' files as part of this task.
- Planning validation has the same six errors on pristine HEAD and the working tree: three old Windows `file:///` links, the existing psycopg-extra validation mismatch, and two outdated frontend metadata comparisons. These are not claimed fixed. Therefore the full repository's hosted CI is not claimed green.
- Actual Linux execution, hosted GitHub Actions, deployment, prospective recall/time-savings validation, and a validated metformin challenger promotion are unverified.

## Integration and conflict control

The starting tree had only the new, untracked ML prompt. The work is isolated on one local branch and does not alter main, the task DAG, CI stage flags, migrations, shared contracts, generated API types, frontend manifests or the original merge guide. The only shared dependency changes are the backend manifest/uv lock; merge those together and perform a frozen sync. Never splice the lock manually.

Keep this change as one dependent integration slice. Review the ML modules/tests first, then the backward-compatible service adapter and ML page, then the manifest/lock and evidence. A single local integration branch avoids unresolved conflicts now; concurrent future edits to these same files still require review and cannot be guaranteed conflict-free.

No remote push, merge, publishing or deployment was performed. The captain can consolidate `audit.md` after accepting the verified changes; this handoff does not mark all historical planning work complete.

## Limits and future experiments

- This quick comparison used a within-review holdout and two tree configurations, not exhaustive tuning/nested CV. Its test set must not become a tuning set for later experiments.
- Missing-abstract groups, contradictory labels and missing titles were explicitly excluded from the numeric benchmark coverage; production retains them for manual review.
- Dataset study IDs were unavailable, so known publication leakage is controlled but complete study-level independence is not proven.
- Active learning is an offline simulation, not automatic live retraining. Stacking, native CatBoost text, large embeddings and formal uncertainty guarantees were not claimed implemented.
- Detailed model explanations are not inferred from scores; the UI now says what the score can support instead of inventing a clinical rationale. Model-specific attribution UI remains future work.
- OpenMP was required for the Mac XGBoost benchmark; a local scikit-learn-wheel runtime was used through an explicit environment variable. Linux CPU wheel resolution is separate from runtime testing.

## Rollback

No new artifact is enabled by default. Revert the local ML integration commit to undo code/dependency/UI changes, or remove a future server-side `EVIDRA_ML_ARTIFACT_DIR` override and restart to select the preserved baseline. Preserve DB backups and append-only machine/human history. There is no migration to reverse.
