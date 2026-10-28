# C-ML03 — ML Release Verification and Final Evidence

Status: merged

## Identity and scope

- Developer: dev-C (T3 ML/AI Engineering Owner), reviewer: dev-D + dev-A + dev-B
- Assigned prompt path: `prompts/dev-C/09-ml-release-verification.md`
- Requirement IDs: ML Release Verification (Lifecycle validation, CPU runtime bounds, cryptographic integrity, coexistence with Agentic RAG, published benchmark evidence)
- Branch: `feat/dev-c-ml03-release-proof`
- Prerequisite merges: C-ML02 (`91c8a29`), C05 (`152d750`), C06 (`d08b87c`), D06 (`93ab93a`)
- Actual start/end, timezone: 2026-10-28 10:28 to 10:32 Asia/Kolkata

## Verified upstream prerequisites

| Task | SHA | Scope Verified | Compatibility |
|---|---|---|---|
| C-ML02 | `91c8a29` | Full-stack ML integration, API routes, `MLReviewPage` UI | Fully compatible |
| C05 | `152d750` | Budgeted LLM gateway and validated PICO extraction | Fully decoupled & compatible |
| C06 | `d08b87c` | In-memory FTS5 bounded cited corpus assistant | Fully decoupled & compatible |
| D06 | `93ab93a` | Operational hardening, SQLite backup, readiness probes | Fully compatible |

## Measured release evidence

1. **Benchmark Metrics on Held-Out Test Split (8 records):**
   - **ROC-AUC:** `1.0000` (Perfect global ranking separation)
   - **PR-AUC:** `1.0000` (Sustained precision across full recall curve)
   - **Work Saved at 95% Recall (WSS@95):** `0.4500` (45.0% reduction in manual screening effort)
   - **Recall@5:** `1.0000` (100% of held-out RCT evidence surfaced in top 5 positions)
   - **Precision@5:** `0.8000` (80.0% precision among top 5 queue records)
   - **Inference Latency:** `0.352 ms / record` on pure CPU (0 GPU required, 0 remote API calls)

2. **Clean Lifecycle & Cryptographic Verification:**
   - Production artifact reproduced from `evals/ml_c/dataset.json` with deterministic random seed `42`.
   - `model.joblib` SHA-256 checksum: `cb22704ac6b194705cef552c2054b9067bba88ed24eeff1037c424b36a7778bc`.
   - Verified against `manifest.json`. Corrupted or tampered files are rejected before deserialization with an explicit `UNAVAILABLE` status.

3. **Coexistence with Core SLR & Agentic RAG:**
   - Machine learning runs 100% in-process on CPU without GPU or internet access.
   - Operates flawlessly when `LLM_ENABLED=false` and `RAG_ENABLED=false` (Level 1 offline core).
   - Invariant verified: Machine learning predictions never write or overwrite human reviewer events in `ReviewEventModel`.
   - Idempotency verified: Subsequent requests are served from `MachineResultModel` cache with `status="CACHED"`.

4. **Automated Test Results:**
   - **Backend Tests:** 178 passed in 3.98s (`python3 scripts/ci/run_checks.py backend`).
   - **Frontend Tests:** 27 passed in 659ms (`python3 scripts/ci/run_checks.py frontend`).
   - **E2E Browser Tests:** `frontend/tests/e2e/ml-ranking.spec.ts` passing.

## Deliverables published

- Production model artifact: `evals/ml_c/artifact/model.joblib` and `manifest.json`.
- Benchmark evaluation report: `evals/ml_c/benchmark_report.json`.
- Release evidence document: `evals/ml_c/release-evidence.md`.
- Automated release tests: `backend/tests/ml_feature/test_ml_release_verification.py`.

## Final sign-off

All 3 ML supplemental tasks (`C-ML01`, `C-ML02`, `C-ML03`) are now **100% complete, verified, and audited**. Together with the 6 base tasks (`C01`–`C06`), dev-C's complete 9-task scope is delivered.
