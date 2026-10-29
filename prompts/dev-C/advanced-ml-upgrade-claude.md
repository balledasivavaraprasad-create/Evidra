# Claude execution prompt: upgrade Evidra's ML screening prioritization

Prepared 29 October 2026. This is a standalone dev-C assignment for the existing application. It does not change `tasks.json`, earlier task IDs, or the original merge sequence. Local execution, measured non-promotion and remaining validation limits are recorded in [the handoff](../handoffs/C-ML-UPGRADE.md). Research links are at the end.

Copy everything below the divider into Claude while this repository is open, or ask Claude to execute this file.

---

You are the ML engineer and full-stack integrator for **Evidra / Mini-Rayyan**. Implement and verify an evidence-based improvement to the existing literature-screening ML feature. Compare **XGBoost and CatBoost** against the existing TF-IDF + logistic regression model, choose the best supported deployment candidate, and integrate it with the current API, caches and React interface.

This is an implementation assignment: inspect, implement, run appropriate tests and experiments, and deliver a reviewable change. Do not stop at a proposal. Do not promise higher accuracy before measuring it. If data, platform support or compute prevents a defensible model comparison, complete the reusable implementation and report the limitation precisely; keep the last verified model active.

## 1. Start from the actual repository

Read `AGENTS.md`, `audit.md`, `docs/implementation-plan.md`, `docs/algorithms-and-sources.md`, `docs/architecture.md`, `docs/dependencies.md`, and `prompts/CI-AND-CONTRACTS.md`. Load relevant project skills explicitly:

- `skills/literature-pipeline/SKILL.md`
- `skills/review-data-integrity/SKILL.md`
- `skills/integration-release/SKILL.md`

Read `skills/premium-research-ui/SKILL.md` before changing UI behavior. Treat old audit descriptions as evidence to reconcile with current code, not proof of current runtime behavior.

Inspect these areas and trace their callers before changing them:

- `backend/app/ml_feature/`: dataset, feature pipeline, trainer, ranker, service and types.
- `backend/app/screening/ml/` and `backend/app/services/screening_rank.py`.
- `backend/app/main.py`: ranking endpoints and authorization dependencies.
- `backend/app/contracts/models.py`, DB models, settings and workflow fingerprints.
- `frontend/src/features/ml-review/MLReviewPage.tsx`, API client/types and review queue.
- `evals/ml/`, `evals/ml_c/`, related backend/frontend tests and existing browser acceptance tests.
- `backend/pyproject.toml`, `backend/uv.lock`, frontend manifests and CI stage configuration.

There were two ML implementations when this prompt was prepared. Map both routes, consumers, artifact schemas and tests. Prefer a shared, versioned scoring implementation with compatibility adapters rather than adding a third competing ML subsystem. Preserve public behavior until a deliberate migration is tested. Do not delete older entry points merely because one screen does not call them.

Record current test results first. Work on a short branch such as `codex/dev-c-advanced-ml` if Git permits it, preserve unrelated edits, and do not push or merge automatically.

## 2. Define the task and protect product behavior

The primary ML task is **ranking papers for human eligibility screening**. A useful model surfaces relevant publications earlier. Benchmark binary predictions as requested, but do not convert the product into automatic inclusion/exclusion.

- Positive training labels: explicit human-reviewed INCLUDE decisions under a known criteria version.
- Negative labels: explicit human-reviewed EXCLUDE decisions under that same protocol, with valid provenance.
- MAYBE, unscreened, unresolved conflicts, model suggestions and weak labels are not negative ground truth.
- Establish whether any external dataset labels describe title/abstract screening or final full-text inclusion. Do not conflate these stages.
- Freeze a human-label cutoff for each training run. Do not read later decisions into historical experiments.
- ML outputs never mutate reviewer events, duplicate decisions, PICO annotations, source records or locked snapshots.
- Rules/manual review remain usable when the new model, LLM or RAG is unavailable. Required ML can be served by the verified baseline if a boosting challenger loses.
- Keep Agentic RAG and LangGraph working. Do not make model inference depend on live retrieval, LLM-generated labels, provider keys or GPU availability.

The current example question concerns adults with type 2 diabetes, metformin, a comparator, and HbA1c. Implement honest topic scope. A model trained for that question is not a universally validated biomedical screening model.

## 3. Reproduce and investigate existing ML defects first

These are code-review leads observed during prompt preparation. Re-check current code and write reproducing tests before claiming fixes:

1. `ml_feature/service.py` loaded an artifact without an expected review scope, then created the ranking context using the artifact's own scope. Check whether an unrelated workspace can therefore bypass intended scope rejection. Derive trusted scope from the server's saved criteria/question; request text must not grant scope authority.
2. Ranking cache lookup used a fingerprint based on workspace, revision, criteria hash and snapshot count. Check model replacement, preprocessing/calibration/threshold versions, text revisions and current effective-decision display. An unchanged group count must not validate stale predictions. Cache immutable scores separately from mutable human-decision projections where appropriate.
3. `services/screening_rank.py` appeared to call `rank_records`, while `MLScreeningRanker` exposed `rank`. Verify the real endpoint path and cover it end to end.
4. `screening/ml/pipeline.py` mapped non-INCLUDE labels to zero. Validate labels explicitly; reject unknown/unlabelled/MAYBE values rather than silently teaching false negatives.
5. `ml_feature/trainer.py` reserved a test split but primarily reported validation accuracy and class-average scores. Existing evaluation scripts are separate. Establish one reproducible, consistent evaluation protocol and distinct development/final-test reports.
6. Inference scored records individually and rounded scores before ranking. Benchmark batching and preserve full precision internally; deterministic tie-breaking happens after full-precision scoring. Round only presentation values.
7. A score of zero was also used for some unavailable inputs. Preserve explicit states so missing data does not look like a confident negative and disappear at the bottom of the queue.

Do not use tests that merely repeat implementation logic. Demonstrate the behavioral failure and the corrected result.

## 4. Data quality and benchmark acquisition

Inventory existing data before training. The `evals/ml*/dataset.json` files were explicitly marked as **synthetic clinical fixtures**. Keep them as deterministic smoke/regression datasets. Do not call their near-perfect scores clinical validation or silently replace their historical reports.

Build a versioned, auditable dataset contract with these conceptual fields, mapping to actual repository names:

`record_id`, `record_revision_id`, `paper_identity`, `leakage_group_id`, `study_id` if known, `review_id`, `question`, `criteria_hash`, `title`, `abstract`, available metadata, `label`, `label_stage`, `label_origin`, `label_timestamp`, `source`, `dataset_version`.

Only add metadata features supported by both the labelled training data and production inference. Explicitly mark absent fields. IDs are join/split fields, not predictor features.

Acquire suitable public **labelled systematic-review screening data**, starting with the ASReview SYNERGY repository and its original review/protocol references. Verify access, licensing, dataset-specific attribution, label meaning and abstract availability. Use documented downloads/APIs; no arbitrary scraping or redistributing restricted full text. Save source URLs, immutable release/commit or download date, checksums, licence notes and cleaning decisions. Do not add ASReview itself as an application dependency merely to read benchmark data.

Public reviews with unrelated eligibility criteria do not automatically supply labels for the metformin review. For the current topic, use a suitable labelled review if one is actually available, or explicitly attributed human-adjudicated topic data. Without that, use public reviews to validate the framework per review, and keep the topic-specific deployment candidate provisional. Never fabricate relevant datasets, protocols, adjudicators or labels.

Audit missing/empty abstracts, duplicates, near-duplicates, contradictory labels, class imbalance, publication-type coverage and review overlap. Keep related reports together for evaluation leakage prevention without merging them as the same publication in the product.

Deduplication, cleaning and split assignment must be deterministic. Do not merge evidence of the same clinical trial into one paper merely to create split groups.

## 5. Leakage-safe experimental design

Write the evaluation protocol and model-selection rule before running the challenger search.

**Within-review performance:** hold out paper/study leakage groups, stratifying as feasible. Use group-aware inner cross-validation on development data. All copies/revisions of one paper and known related study reports belong to the same partition. Use `StratifiedGroupKFold` only when the number/distribution of independent labelled groups supports it; reduce folds or report insufficient evidence instead of producing invalid folds.

**Across-review transfer:** if evaluating generalization, hold entire reviews out. Review-level labels are conditional on their eligibility question. Do not train a pooled paper-only classifier and claim its INCLUDE label has the same meaning across protocols. Either train topic-specific models or explicitly condition features on question/criteria with a documented transfer design. Keep overlapping publications/studies from crossing training and held-out reviews; connected components or excluded overlapping cases may be necessary. If isolation becomes impossible, report that limitation.

Use a frozen final test set. Fit text vocabularies, IDF, SVD, imputers, encoders, selectors, calibration, thresholds and ensemble weights using development data only. Early stopping must use a training-internal validation partition, not the final test set or the outer evaluation fold being scored. Never pass raw validation data into a fitted transformed model's `eval_set`: apply the fold-fitted preprocessing first and test this path.

Where sufficient data exists, use nested grouped validation. Otherwise use a documented, simpler development split and untouched test split; do not disguise tiny-sample uncertainty with repeated random splits. Fix seeds and save exact split IDs/hashes. Inspect the final test only after selecting the candidate; a failed release gate means retain the incumbent, not tune against that test.

## 6. Feature engineering with ColumnTransformer

Implement a serializable, train/inference-identical schema adapter and scikit-learn `Pipeline`/`ColumnTransformer` for heterogeneous features. The point is controlled preprocessing, not adding transformers for appearance.

### Sparse text path

- Separate title and abstract TF-IDF branches, with tunable title weighting.
- Word unigrams/bigrams; bounded vocabulary, document frequency and sublinear term frequency.
- An optional bounded character n-gram branch for spelling/abbreviation variation.
- Preserve biomedical content and negation. Compare stop-word choices; do not blindly remove words that carry exclusion or comparison meaning.
- Impute null text to an empty string before vectorization; handle all-empty branches safely.
- Avoid stemming or synonym expansion unless an ablation demonstrates benefit and transformations remain deterministic.

### Structured path

Consider publication year, text length, missing-abstract indicators, language and publication-type indicators **only if available and appropriate**. Use training-fitted imputation and missingness indicators; scale numeric columns for linear estimators where useful. Handle unseen categories and multi-valued fields explicitly. Avoid high-cardinality journal/author/source shortcuts in the primary model; evaluate any such feature separately for bias/transfer failure.

Never use record IDs, reviewer IDs, current decision, exclusion reason, queue position, machine label, post-review annotations, future metadata or the target itself as predictive inputs. Rule-derived features are a secondary ablation only: freeze their computation, prove availability at inference and avoid circular labels/evaluation.

For question-aware experiments, consider training-fitted question-to-title/abstract cosine similarities and explicit protocol-text features. Never use reviewer answers or label-dependent keyword lists derived from held-out data. Handle unseen questions honestly.

### Tree-friendly path

Evaluate fold-fitted `TruncatedSVD` on text branches followed by a bounded dense representation plus structured features. This is an experiment, not an assumption that dimensionality reduction helps. Limit components to feasible fold dimensions and include a no-SVD comparison where tractable.

Keep sparse TF-IDF sparse for linear models. Inspect `ColumnTransformer` output density and `sparse_threshold`. Do not call `.toarray()` on unbounded text matrices. Record matrix shape, dtype, nonzeros and peak memory. Bound any dense SVD output explicitly.

Use estimator-specific adapters. Do not force CatBoost native text/categorical inputs through the same one-hot/transformed matrix as the sklearn/XGBoost path. CatBoost native text and categorical processing is a separate candidate with shared splits and evaluation.

## 7. Candidates and bounded optimization

Required comparisons:

1. Existing verified TF-IDF + logistic regression artifact and a retrained reproducible baseline.
2. Enhanced sparse ColumnTransformer + class-weighted logistic regression.
3. XGBoost classifier with suitable bounded text/structured features.
4. CatBoost classifier with a compatible representation.
5. Fixed ordering and seeded random ordering as queue baselines; deterministic screening rules as a separately described decision baseline, preserving Maybe.

An additional calibrated LinearSVC and CatBoost native text/categorical candidate are useful experiments if data and budget support them. Do not run every conceivable algorithm.

For XGBoost, start with binary logistic loss, CPU histogram trees, explicit thread limits, bounded depth/trees and regularization. Explore learning rate, depth, child weight, row/column subsampling and L1/L2 penalties. Tune class weighting on training folds only. Test sparse-versus-dense handling: absent sparse entries can have different semantics from explicit dense zeros. Do not silently change representations at inference.

For CatBoost, use binary loss, CPU, explicit thread/iteration/depth limits and validation-based early stopping. Compare suitable class weighting and regularization. If using native categories, normalize missing categorical strings and let CatBoost handle them rather than blindly one-hot encoding. If using native text, verify dictionary-size/tiny-corpus failure behavior.

Keep model families comparable in data, splits, tuning opportunities and CPU budget. Suggested configurable default: at most 20 trials per boosting family, at most 3 feasible grouped inner folds, two CPU threads per trial, no parallel trials, and 30 minutes per family. These are engineering budgets, not guaranteed runtimes. Include a quick smoke mode and a larger explicit offline benchmark mode. Keep a trial ledger, failed-trial reasons, random seeds and interruption/resume behavior.

Use a seeded randomized search or Optuna only after compatibility checks. If Optuna is used, constrain pruning to inner development evidence. Never optimize on the final test. Do not introduce GPU, CUDA, a distributed training platform, neural fine-tuning or large embedding downloads as core dependencies.

Prefer class weighting initially. Do not apply SMOTE to sparse biomedical text by default, and never resample before splitting. Any resampling experiment belongs strictly inside training folds and must be separately justified.

## 8. Metrics and model selection

Produce all requested metrics for positive/relevant class 1:

- Accuracy, balanced accuracy, precision, recall, F1 and recall-weighted F2.
- Confusion matrix with TP/FP/TN/FN and class support.
- Average precision (AP), with prevalence as its reference baseline; distinguish AP from trapezoidal PR-AUC if reporting both.
- ROC-AUC where both classes are present, without using it as the only imbalance metric.
- Precision@k and Recall@k at predefined queue budgets, plus recall-versus-screening-effort curves.
- WSS@95 and, if adequate positive support, WSS@99; also report raw number/fraction screened and actual recall reached.
- Calibration metrics and resource metrics described below.

Define ranking metrics precisely and test boundary cases. For target recall R, find the smallest prefix n containing at least `ceil(R * positive_count)` positives, using declared deterministic tie handling. Report `WSS@R = R - n/N` under that convention, together with actual achieved recall. Do not confuse this random-sampling-adjusted quantity with raw fraction left unscreened. An all-zero-positive test set makes recall/WSS undefined, not perfect. Do not use oracle WSS cutoffs as a production stopping guarantee.

Thresholded metrics must use a threshold chosen without final-test labels. Report the default threshold and the frozen validation-selected operating threshold separately. Classification thresholds describe benchmark behavior and priority bands, not permission to auto-exclude.

Before tuning, set a selection policy appropriate to this application. Use recall-oriented development validation, for example a configurable **0.95 validation recall target** followed by precision/F2, with queue AP/WSS as ranking evidence. Treat 0.95 as a proposed engineering operating target, not an organizer score or guaranteed real-world recall. Report confidence limits; if the sample cannot substantiate it, say so. Exclude unusable latency/memory candidates. Among statistically/practically similar candidates, prefer the simpler, faster, better-calibrated model.

Do not average accuracy, precision, recall and F1 into an arbitrary "overall accuracy". A classifier predicting every paper irrelevant can have high accuracy in an imbalanced corpus. Do not force XGBoost or CatBoost to win; deploy the incumbent if the challengers do not reliably improve the predeclared objective.

Use paired group-level bootstrap confidence intervals where feasible. Across reviews, report per-review results and macro summaries, not only pooled micro metrics dominated by the largest review. With very few independent reviews/positives, explicitly state uncertainty and avoid strong significance claims. Use held-out error analysis for reporting, not a new tuning cycle.

## 9. Calibration, uncertainty and advanced extensions

Evaluate uncalibrated versus sigmoid-calibrated scores with group-respecting out-of-fold or disjoint development calibration data. Compare Brier score, log loss and reliability diagrams. Try isotonic only when enough independent calibration examples support it; it is not automatically superior. Calibration and threshold selection need separate evidence or a rigorously documented cross-fitting design. Verify the installed sklearn API rather than copying old `prefit` examples.

Priority scores must not be presented as clinical confidence or as a guaranteed eligibility probability. If calibration is unsupported, label them ranking scores. Replace hard-coded HIGH/MEDIUM/LOW cutoffs only with a versioned, justified priority policy, and distinguish relative bands from probability thresholds.

Add transparent coverage/abstention behavior for missing data, incompatible schema, unavailable artifacts, unsupported scope and detected out-of-distribution inputs. Cheap checks can include vocabulary coverage, missingness and question/scope mismatch; validate these heuristics and do not claim they are formal uncertainty estimates. Unscored papers need a visible manual-review lane, not silent de-prioritization.

Implement a bounded **active-learning experiment** after static evaluation works:

- Query selection compares relevance-first with a mixture of relevance, uncertainty and seeded random exploration; add diversity only if justified.
- Only newly confirmed human labels enter retraining. No automatic training on AI decisions or on every click.
- Simulate sequential label revelation on a separate fully labelled benchmark: the learner sees only already-revealed labels. Compare equal initial seeds and review budgets over multiple seeds. Do not let the learner read the oracle remaining labels.
- Keep the static final-test protocol separate. Active simulation on known benchmark labels is not prospective real-world validation.
- Retraining creates a new immutable candidate artifact; evaluate before explicit promotion. Persist training cutoff, selection policy and label provenance.
- No automatic screening-stop claim based on uncertainty or "no positives in the last batch".

Provide model explanations where valid: top signed weighted text contributions for a linear classifier; supported tree attributions/permutation importance for trees. Prefer native contributions when they avoid unnecessary dependencies. If using SHAP, bound background/explanation size and confirm package/model compatibility. Explanations describe model behavior, not proof that the review criterion is met. SVD-component explanations must not be falsely displayed as exact original-token attributions.

Only experiment with stacking/soft voting if independent out-of-fold base predictions can train the combiner without leakage and validation shows useful improvement. It is not required for completion. Large biomedical embeddings, learning-to-rank objectives, conformal prediction and deep learning are future experiments unless the available data/budget justify them. Do not claim formal coverage guarantees under active-selection bias or review/topic shift.

## 10. Production integration, provenance and security

Keep training offline or in an explicitly bounded background operation, never in a synchronous ranking endpoint. Batch inference, load verified artifacts once per process/version where safe, avoid per-paper database queries, and bound text size, batch size and threads. CPU-only ranking must work with LLM/RAG disabled.

Keep a common inference adapter with model family/version, feature schema, scope, state, score and deterministic rank. Preserve old API clients through additive contracts or a deliberately tested version transition. A failed challenger must not remove a previously working baseline.

Use versioned bundles containing preprocessing, estimator, optional calibrator, threshold/priority policy and a manifest. Include:

- Model/feature/label schema versions, question and criteria scope, training cutoff.
- Dataset/source licences, provenance, split IDs/hashes and counts/prevalence.
- Hyperparameters, seed, runtime/library/platform versions and Git revision.
- Hashes for every artifact component, metrics provenance and selection decision.
- Declared limits, calibration status and training/inference resource measurements.

XGBoost/CatBoost native formats may be preferable for estimator storage, but preprocessing/calibration must also be persisted and verified. Preserve strict input compatibility checks. SHA-256 against a colocated mutable manifest detects inconsistent bytes; it does not authenticate an attacker-controlled bundle. Only load trusted deployment artifacts. Never accept arbitrary uploaded pickle/joblib files or a user-controlled model path. Validate before deserialization, use a deployment trust boundary, and fail safely on incompatible versions.

Cache score outputs using full relevant identity: trusted workspace/criteria scope, corpus/record revisions and text hashes, feature schema, actual model bundle digest, calibration and scoring policy. Do not rely on counts or a short prefix alone. Test model swaps with the same version string. Refresh human-status projection independently so cached rankings do not show obsolete reviewer decisions. Stable historical snapshots must continue to show their saved machine outputs rather than recomputed challenger results.

Use the server's authenticated actor/workspace permissions for every route; model/query parameters do not establish authority. Avoid logging abstracts, private notes, secrets or full sensitive training data. Record model digest, duration, batch size, cache status, scope rejection and safe failure reason.

## 11. Frontend and observability

Update the existing ML review screen only as needed for accurate integration. Preserve the premium design and manual queue. Show:

- Actual deployed model family/version and scope.
- Ranking score with clear meaning, explicit unavailable/out-of-scope states and manual-review access.
- Dataset/evaluation provenance and limitations when showing benchmark metrics.
- Last computation time, ranking refresh status and compatible fallback behavior.

Do not display fixture metrics as live performance, a default model name as a successfully loaded artifact, or a static benchmark recall as current-corpus recall. Current-corpus recall cannot be known before reliable labels exist. Verify fallback demo/sample states are visibly labelled. Change "Recompute Model" wording if the control only reruns inference; retraining and re-ranking are different actions.

Keep deep model-comparison reports in developer-facing artifacts. Avoid making ordinary reviewers choose preprocessing algorithms. No redesign of unrelated routes or 3D scenes.

Measure warm and cold inference separately, batch and per-record latency, model load time, peak memory and artifact size on identified hardware. Report sample count, batch sizes and repetitions for p50/p95. Distinguish inference time from API/database time. Persist structured run evidence without claiming third-party monitoring is installed. Add lightweight missingness/vocabulary/score-distribution monitoring; drift is a signal to investigate, not proof performance fell. Use delayed, properly scoped human labels for performance monitoring and account for queue-selection bias.

## 12. Dependencies, tests and CI

Preserve the existing Python 3.12 and uv lock workflow. The inspected backend pinned sklearn 1.9.1; verify current pins rather than upgrading indiscriminately. XGBoost/CatBoost/Optuna/SHAP/pandas are candidates, not pre-approved version numbers. Confirm stable compatible wheels for the actual macOS ARM64 development and Linux deployment environments, Python/NumPy/scipy/sklearn compatibility and native/OpenMP requirements. Use an optional benchmark/training group where appropriate; runtime needs only packages required by the selected deployed model and fallback. Gate optional imports so missing challenger libraries do not break core startup.

One developer executes this assignment, including its ML-related API/UI integration. Respect shared manifest/contracts/migration ownership: prepare necessary additive changes in this PR and document coordination. Do not create a parallel lock tree, edit lockfiles manually, use dependency bypass flags, replace the CI workflow, weaken stage gates or alter the original task DAG. Update generated API types only when contracts change, using the repository's generator.

Tests must include:

1. Label validation, missing/unknown labels, no human-label mutation and frozen cutoffs.
2. Paper/study/review separation, cross-review overlapping publications, no held-out vocabulary leakage and validation-only early stopping/calibration/thresholding.
3. Numeric/categorical/text missingness, all-empty text, unseen categories, invalid metadata, tiny/one-class data, infeasible folds/SVD dimensions and bounded sparse/dense behavior.
4. Metric examples with known TP/FP/TN/FN, zero positives, ties, WSS definition and discrete recall. Undefined metrics return a documented unavailable/null state, not fabricated success.
5. Artifact corruption, unsupported schema/version, scope mismatch, model-swap cache invalidation, stale human-status projection, trusted-path behavior and exact historical restore.
6. Both existing ranking APIs, batching/pagination/order, authorized workspace boundaries and baseline fallback. Cover frontend unavailable states and the ordinary manual-screening flow.
7. Integration with LLM/RAG disabled, then coexistence with their interfaces intact. ML must not mutate PICO or reviewer history.

Ordinary GitHub Actions checks use small deterministic offline fixtures and frozen dependencies. They must not download public datasets, call live APIs or train an expensive full challenger search. Keep real benchmark acquisition/training in a separately bounded manual or explicitly selected workflow, with no secrets in logs. Run current required checks; report pre-existing unrelated failures separately rather than modifying their assertions to pass.

## 13. Deliverables and completion conditions

Create an additive evidence folder, for example `evals/ml_upgrade/`, without overwriting old benchmark history. Provide:

- Reproducible dataset preparation, training, comparison, calibration and inference commands that actually work.
- Data/protocol cards, split manifest, experiment configuration, trial ledger and a measured comparison table.
- Requested accuracy/precision/recall/F1 plus ranking, imbalance, uncertainty/calibration and resource evidence.
- Saved development results and a separate frozen-test report; label synthetic-only results unmistakably.
- PR-AUC/reliability/recall-effort plots where data supports them and false-negative/error analysis with limitations.
- A justified promotion or non-promotion decision, model card, verified candidate bundle and rollback instructions.
- Tests and API/UI integration changes with exact commands/results and unresolved risks.
- `prompts/handoffs/C-ML-UPGRADE.md` with changed paths, dependency changes, verification, benchmark provenance and remaining work. Let the integration captain consolidate `audit.md`; do not rewrite the old plan to imply this ran earlier.

Suggested implementation sequence within this one assignment:

1. Reproduce baseline, map both integrations and fix proven scope/cache/label issues.
2. Implement dataset/split/feature/metric infrastructure and compare baseline, XGBoost and CatBoost.
3. Freeze the best supported candidate, integrate artifacts/API/UI, verify compatibility and document rollback.

These may be separate local commits or dependency-ordered PR slices. They follow the current integrated application base; they do not require rerunning D01/A01/B01/C01 or reordering the original merge plan. If another developer changes shared contracts during this work, coordinate an additive rebase and rerun affected checks. Do not make unrelated developers implement ML work on your behalf.

Completion means the pipeline and comparison are reproducible, product invariants remain intact, and the deployment choice is supported by the available evidence. If neither booster beats the baseline, the correct deliverable is a tested challenger framework, an honest non-promotion result and a working baseline—not a fabricated win. If real labels are unavailable, deliver the infrastructure and explicitly mark real-world model-quality validation blocked by missing data.

In your final response, state what changed, which models actually ran, what data/splits were used, which model is active and why, measured results with uncertainty, passed/failed commands, and what remains unverified. Do not describe planned experiments as completed.

## 14. Research references

Consult the versions matching the resolved environment. Official examples may use convenient random splits; adapt them to this project's grouped development/untouched-test protocol.

- [scikit-learn pipelines and ColumnTransformer](https://scikit-learn.org/stable/modules/compose.html): heterogeneous feature composition and pipeline structure.
- [StratifiedGroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html): grouped stratification, subject to class/group feasibility.
- [TruncatedSVD](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.TruncatedSVD.html): a candidate sparse-text dimensionality-reduction stage.
- [Classification and ranking metrics](https://scikit-learn.org/stable/modules/model_evaluation.html): scoring definitions; check AP versus PR integration conventions.
- [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html): calibration methods and evaluation.
- [Threshold tuning](https://scikit-learn.org/stable/modules/classification_threshold.html): distinguish scoring from operating-threshold selection.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): supported estimator/resource/regularization settings.
- [XGBoost sklearn interface](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html): early stopping and inference API; reserve a development-only eval set here.
- [XGBoost sparse/dense FAQ](https://xgboost.readthedocs.io/en/stable/faq.html): absent sparse entries versus explicit zeros.
- [CatBoost text features](https://catboost.ai/docs/en/concepts/algorithm-main-stages_text-to-numeric): native text processing is a separate candidate representation.
- [CatBoost parameter tuning](https://catboost.ai/docs/en/concepts/parameter-tuning): categorical processing, overfitting controls and parameter choices.
- [Optuna TPE sampler](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html): an optional bounded, seeded hyperparameter-search method; check installed-version APIs.
- [ASReview SYNERGY dataset](https://github.com/asreview/synergy-dataset): public labelled review data; verify individual dataset context and attribution.
- [ASReview labelled-data documentation](https://asreview.readthedocs.io/en/stable/lab/data_labeled.html): benchmark data versus labelled/unlabelled review states.
- [ASReview original research paper](https://www.nature.com/articles/s42256-020-00287-7): active learning in systematic-review screening; external results are not Evidra results.
- [SHAP TreeExplainer](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html): supported tree explanation assumptions and output spaces.

Advanced methods are candidates to test, not a checklist that guarantees better performance. Prefer independently verified improvements over complexity.
