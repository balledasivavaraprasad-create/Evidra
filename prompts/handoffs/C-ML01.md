# C-ML01 — Required ML foundation, training and inference

Status: ready for review

## Identity and scope

- Developer and reviewer: dev-C (T3 ML/AI owner), reviewer: dev-D + dev-B
- Assigned prompt path: `prompts/dev-C/07-ml-foundation.md`
- Requirement IDs and selected features: ML Foundation (Bounded review prioritization model, leakage-free group splits, tamper-protected artifact, queue ranking)
- Branch and PR: `feat/dev-c-ml01-foundation`
- Tested commit SHA: `ee0d070`
- Merge SHA (captain fills after merge): Pending captain merge
- Actual start/end, timezone: 2026-10-27 12:35 to 12:47 Asia/Kolkata

## Prerequisite evidence

| Prompt | Actual merged SHA | Interface/examples inspected | Compatible with this commit? |
|---|---|---|---|
| D01 | `a6f78e9` | Backend foundation contracts and frozen ports | Yes |
| C01 | `2bb9a84` / `210990d` | PICO baseline, offsets, and synthetic records | Yes |
| B02 | `92c3480` | Explainable screening criteria, rules engine, defaults | Yes |

## Implemented behavior

1. **Domain Types & Config Schema (`backend/app/ml_feature/types.py`):**
   - Declared Pydantic models: `RecordInput`, `TrainConfig` (bounded 500 features, class-weighted, deterministic seed), `ArtifactManifest` (cryptographic SHA-256 provenance), `RankingItem`, `RankingBatch`, `RankingContext`.
   - Bounded resources: pure CPU in-memory scikit-learn without GPU requirements or live API dependencies.

2. **Leakage-Free Group Partitioning & Preprocessing (`backend/app/ml_feature/dataset.py`):**
   - Preprocesses text combining title and abstract into a single canonical representation.
   - Computes deterministic SHA-256 fingerprint for dataset splits (`train_hash`, `val_hash`, `test_hash`).
   - `create_leakage_free_split()` ensures records belonging to the same clinical study or duplicate publication group (`group_id`) strictly stay in the exact same split, preventing cross-split data leakage.
   - Validates multi-class presence and minimum sample size; raises informative errors on single-class datasets.

3. **Scikit-Learn Prioritization Pipeline (`backend/app/ml_feature/pipeline.py`):**
   - Combines `TfidfVectorizer(max_features=500, ngram_range=(1,2), sublinear_tf=True)` with `LogisticRegression(class_weight='balanced', C=1.5, random_state=42, solver='lbfgs')`.
   - Feature weights and vocabulary are fitted exclusively on the training split.

4. **Cryptographic Artifact Serialization (`backend/app/ml_feature/trainer.py`):**
   - Offline training command saves `model.joblib` and `manifest.json`.
   - Computes and records exact SHA-256 checksum of `model.joblib` into `manifest.json` for tamper prevention.
   - Binds artifact version (`ml_ranker:v1.0.0`) to specific review question scope.

5. **Verified Runtime Inference Engine (`backend/app/ml_feature/ranker.py`):**
   - `load_ranker(artifact_dir, expected_scope)` strictly validates scope and verifies SHA-256 checksum against manifest before deserialization, rejecting tampered or corrupt files.
   - `rank_records(records, context)`:
     - Missing abstracts (<10 chars or None) yield `state="UNAVAILABLE"` and `score=0.0` with `reason="MISSING_ABSTRACT"`.
     - Out-of-scope queries yield `state="OUT_OF_SCOPE"`.
     - Deterministic tie-breaking by `(-score, record_id)` guarantees stable queue ordering.
     - Never mutates literature records in place.

6. **Reproducible Evaluation Benchmark (`evals/ml_c/`):**
   - Curated clinical dataset `evals/ml_c/dataset.json` (40 records: 20 RCTs/clinical trials, 20 animal/simulation/case reports).
   - Training runner `run_training.py` produces production artifact in `evals/ml_c/artifact/`.
   - Benchmark runner `run_eval.py` evaluates held-out test split:
     - **ROC-AUC:** 1.0000
     - **PR-AUC:** 1.0000
     - **WSS@95 (Work Saved):** 0.4500 (45.0% work saved over random sampling)
     - **Precision@5:** 0.8000
     - **Inference Latency:** 1.544 ms / record

## Interfaces for downstream owners

- **Exported Module (`backend/app/ml_feature`):**
  - `load_ranker(artifact_dir, expected_scope) -> MLRanker`
  - `train_ranker(records, config, output_dir, scope) -> ArtifactManifest`
  - `rank_records(ranker, records, context) -> RankingBatch`
  - `MLRanker`, `RecordInput`, `TrainConfig`, `ArtifactManifest`, `RankingBatch`, `RankingContext`
- **Consuming Downstream Owner:**
  - **dev-C (C-ML02):** Wrap `MLRanker` in authorized FastAPI endpoints (`POST /api/v1/workspaces/{id}/ml/rank`) and build React review workbench integration.
  - **dev-B (B06):** Incorporate ML benchmark metrics (ROC-AUC 1.0, WSS@95 45%) into final evaluation evidence report.
- **Next Prompts Unblocked:**
  - Unblocks `C-ML02` (ML Full-Stack Integration, after D04 + B03 + C03 + A04).

## Verification evidence

| Check | Exact command | Environment/fixture | Exit/result | Evidence path or real CI run |
|---|---|---|---|---|
| ML unit & regression tests (6 tests) | `uv run --locked pytest tests/ml_feature/ -v` | Local Python 3.12 | Code 0, 6 passed in 1.31s | `backend/tests/ml_feature/` |
| Full backend test suite (66 tests) | `uv run --locked pytest -v` | In-memory SQLite + contracts | Code 0, 66 passed in 4.23s | `backend/tests/` |
| Code quality & linter | `uv run --locked ruff check app tests scripts` | Ruff 0.17.2 | Code 0, all checks passed | Local backend codebase |
| Full backend CI stage runner | `python scripts/ci/run_checks.py backend` | All 6 stage gates | Code 0, all passed in 4.52s | `scripts/ci/run_checks.py` |
| ML benchmark evaluation | `uv run --project backend python evals/ml_c/run_eval.py` | 8 held-out records | Code 0, ROC-AUC=1.0, WSS@95=0.45 | `evals/ml_c/benchmark_report.json` |
| Planning validation & CI tests | `python scripts/validate_planning.py; python -m unittest discover -s tests/planning` | Planning test suite | Code 0, 63 MD files, 32 unit tests OK | `tests/planning/` |

## Cross-owner requests and release decision

| Request | Owning developer | Consuming prompt | Smallest upstream change/test | Blocking? |
|---|---|---|---|---|
| None | dev-C | C-ML02 | Consume pure `MLRanker` in C-ML02 | No |

- Implemented: Complete scikit-learn review prioritization pipeline, leakage-free group partitioner, tamper-verified artifact serialization, and queue ranker.
- Tested: 6 new unit tests, all 66 backend tests passing, 40-record benchmark evaluated with zero errors.
- Deployed: Local feature branch `feat/dev-c-ml01-foundation`.
- Known risks/limitations: Prioritization model is trained for the specific T2D/Metformin review question; out-of-scope topics require training a separate scoped artifact.
- Reviewer decision and reason: Ready for review and merge into `main` by dev-D and dev-B.
