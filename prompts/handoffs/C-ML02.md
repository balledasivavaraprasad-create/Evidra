# C-ML02 — Full-Stack ML Review Prioritization Integration

Status: implemented, verified, ready for merge

## Identity and scope

- Developer and reviewer: dev-C (T3 ML/AI owner), reviewer: dev-D + dev-A
- Assigned prompt path: `prompts/dev-C/08-ml-full-stack-integration.md`
- Requirement IDs and selected features: ML Full-Stack Integration (Dedicated ML review interface in `frontend/src/features/ml-review/`, authorized ML ranking route, MachineResultModel caching, runtime telemetry, Playwright E2E browser tests)
- Branch: `feat/dev-c-ml02-full-stack`
- Prerequisite merges: C-ML01 (`68e4715`), D04 (`6dbd8cb`), B03 (`8704cbc`), C03 (`b3329be`), A04 (`a3d03fd`)
- Actual start/end, timezone: 2026-10-28 10:06 to 10:28 Asia/Kolkata

## Reachable paths and contracts

1. **Backend REST API:**
   - `POST /api/v1/workspaces/{workspace_id}/revisions/{revision_id}/ml-ranking`
     - Computes or retrieves cached ML ranking using verified scikit-learn model.
     - Supports optional query override, criteria scoping, pagination (`limit`, `offset`), and `force_recompute` flag.
   - `GET /api/v1/workspaces/{workspace_id}/revisions/{revision_id}/ml-ranking`
     - Read-only paginated access to computed ranking for a corpus revision.

2. **Frontend UI Routes:**
   - `/reviews/:id/ml-ranking` — Dedicated ML Prioritization screen for active workspace review.
   - `/ml-ranking` — Direct link with fallback to active workspace.
   - Global navigation header entry: "ML Prioritization" with `Brain` icon.

3. **Domain Contracts & Schemas:**
   - `MLRankedItem`: `{ record_id, group_id, title, abstract_text, score, rank, state, reason, priority_label, effective_status }`
   - `MLRankingRequest`: `{ review_question, criteria_version_id, force_recompute, limit, offset }`
   - `MLRankingResponse`: `{ workspace_id, revision_id, criteria_version_id, model_version, scope, status, reason, total_records, scored_count, items, computed_at, duration_ms }`
   - Contracts validated via `contracts/openapi.json` and generated `frontend/src/api/schema.d.ts`.

## Implemented behavior

1. **Domain Service (`backend/app/ml_feature/service.py`):**
   - Resolves workspace and corpus revision; raises 404 on invalid or mismatched workspace.
   - Bounds corpus size to 50,000 records; raises 413 on oversized sets.
   - Enforces tamper-checked model loading via `load_ranker()`. Rejects corrupted or modified binary files with graceful `UNAVAILABLE` status, ensuring literature review workflow is never blocked.
   - Caches results idempotently in `MachineResultModel` with per-record SHA-256 fingerprinting.
   - Logs runtime metrics into `RunLogModel` with duration, trace ID, and status.
   - Preserves human decision sovereignty: model scores are strictly assistive; no reviewer events are ever written or modified by inference.

2. **Frontend UI Experience (`frontend/src/features/ml-review/MLReviewPage.tsx`):**
   - Luxury frosted glass design system matching Evidence Observatory aesthetics.
   - Priority tier cards: `#1, #2, #3` with probability score gauge and color-coded labels (`HIGH`, `MEDIUM`, `LOW`, `UNSCORED`).
   - Baseline literature ordering toggle: switch effortlessly between ML probability order and canonical corpus order.
   - Priority filter tabs: `All Papers`, `High Priority`, `Medium`, `Low`, `Unavailable`.
   - Reader panel with model rationale callout, abstract viewer, and preserved human decision controls (`Include`, `Maybe`, `Exclude`).
   - Graceful fallback for missing abstracts (`UNAVAILABLE` with `MISSING_ABSTRACT` reason and 0.0 score).

3. **Automated Verification:**
   - Backend unit and service tests in `backend/tests/ml_feature/test_ml_service.py` (13 tests total in `tests/ml_feature/`):
     - Valid ranking order and tie breaking
     - Missing abstract handling
     - Cache hits on subsequent calls (`status: "CACHED"`)
     - `force_recompute` cache bypass
     - Unauthorized/unknown workspace rejection (404)
     - Empty corpus revision handling (`status: "EMPTY"`)
     - Tamper/corruption resilience (`status: "UNAVAILABLE"`)
     - REST API route integration via FastAPI test client
   - Frontend unit tests in `frontend/src/tests/ml_review.test.ts` (6 tests, 27 total frontend unit tests).
   - Playwright E2E browser test in `frontend/tests/e2e/ml-ranking.spec.ts` verifying rendering, score badges, ordering toggle, priority filtering, and decision recording.

## Shared files touched

- `backend/app/contracts/models.py`: Added `MLRankedItem`, `MLRankingRequest`, `MLRankingResponse`.
- `backend/app/main.py`: Registered `POST` and `GET` `/ml-ranking` endpoints.
- `contracts/openapi.json`: Updated OpenAPI spec via deterministic export.
- `frontend/src/api/schema.d.ts`: Regenerated TypeScript types via `openapi-typescript`.
- `frontend/src/api/client.ts`: Added typed `api.ml` client methods and exported ML interfaces.
- `frontend/src/api/fixtures.ts`: Added `MOCK_ML_RANKING` test fixture.
- `frontend/src/App.tsx`: Registered `/reviews/:id/ml-ranking` and `/ml-ranking` routes.
- `frontend/src/components/Header.tsx`: Added "ML Prioritization" navigation link.

## Note for teammates

Dev-A and Dev-D have **no ML coding handoff to implement**. Full-stack ML integration is completed by Dev-C. Remaining ML scope transitions to C-ML03 for final release verification and benchmark reporting.
