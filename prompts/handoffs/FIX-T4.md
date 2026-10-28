# FIX-T4 — Group Row Version Contract & In-Process Import Worker

Status: ready for review

## Identity and scope

- **Developer and reviewer:** dev-D (T4 contracts, database, jobs, and deployment owner)
- **Branches:**
  1. `contract/group-row-version` (PR 1 — merge FIRST; T2 is waiting on it)
  2. `fix/import-worker` (PR 2 — fixes queued import jobs on Render and Docker)
- **Reviewer:** dev-A (T1 frontend owner) for generated types; dev-B (T2 screening owner) & dev-C (T3 bounded research agent)

---

## Deliverable 1: PR 1 (`contract/group-row-version`)

### Objective
Provide optimistic concurrency control on `PaperGroupSummary` so the screening workbench (T2) can detect concurrent modifications.

### Changes Implemented
1. **Domain Contract (`backend/app/contracts/models.py`):**
   - Added `row_version: int = Field(default=1, description="Optimistic locking row version")` to `PaperGroupSummary`.
   - Additive change preserving backwards compatibility.
2. **Corpus Queries (`backend/app/services/corpus.py`):**
   - In `list_paper_groups_in_revision`: Added `PaperGroupModel.row_version` to the query tuple and assigned `row_version=group_row_version` when instantiating `PaperGroupSummary`.
   - In `get_paper_group_detail`: Populated `row_version=group.row_version if group and group.row_version is not None else 1`.
3. **OpenAPI & TypeScript Code Generation:**
   - Updated `frontend/src/api/fixtures.ts` to include `row_version: 1` on mock groups.
   - Regenerated `contracts/openapi.json` (`python scripts/export_openapi.py`).
   - Regenerated `frontend/src/api/schema.d.ts` (`npm run api:generate`).
   - Verified strict compliance via `python scripts/export_openapi.py --check` and `npm run api:check`.
4. **Contract Tests (`backend/tests/contracts/test_contracts.py`):**
   - Added `test_paper_group_summary_contract_has_row_version`: Validates that `PaperGroupSummary` includes `row_version: int`.
   - Added `test_group_row_version_increments_after_decision`: Validates that `row_version` starts at 1 and increments after recording a screening decision.
5. **Notice for T1 (Frontend Owner):**
   - Please review `frontend/src/api/schema.d.ts` where `PaperGroupSummary` now includes `row_version: number`. All frontend tests and typechecks pass (`npm run test:unit`, `npm run typecheck`).

---

## Deliverable 2: PR 2 (`fix/import-worker`)

### Objective
Fix bug on Render where literature imports remain in the "queued" state forever. In `infra/entrypoint.sh`, only Uvicorn was started, leaving background jobs unprocessed.

### Changes Implemented
1. **Configuration (`backend/app/settings.py`):**
   - Added `run_worker_in_process: bool | None = Field(default=None, description="Run background job worker in-process inside FastAPI lifespan")`.
   - In `validate_production_security`: If `self.run_worker_in_process is None`, defaults to `True` when `APP_ENV=production` and `False` in test/development environments.
   - Supports explicit override via `RUN_WORKER_IN_PROCESS=true|false`.
2. **Safe Daemon Loop & Clean Shutdown (`backend/app/worker.py`):**
   - Updated `run_worker_daemon(poll_interval, max_iterations, stop_event)` to accept a `threading.Event`.
   - Polling loop checks `while not (stop_event and stop_event.is_set()):` and uses `stop_event.wait(poll_interval)` for instant wake-up upon shutdown.
   - Decoupled `from app.main import app` to prevent circular imports during application lifespan initialization.
3. **Stuck Job Recovery & Durable Claiming (`backend/app/services/jobs.py`):**
   - Added `recover_stuck_jobs(db: Session) -> int` to reset any abandoned `JobModel.state == "running"` jobs back to `"queued"` with cleared leases (`lease_owner=None`, `lease_until=None`, `stage="queued"`).
   - In `acquire_next_job`: Extended lease filter to handle null or expired leases safely: `(JobModel.lease_until < now) | JobModel.lease_until.is_(None)`.
4. **FastAPI Lifespan Management (`backend/app/main.py`):**
   - Added `@asynccontextmanager async def lifespan(app: FastAPI)`:
     - On startup (when `settings.run_worker_in_process` is True):
       - Verifies `WORKERS` environment variable. If `WORKERS > 1`, logs a warning that in-process mode requires `WORKERS=1` for single-worker execution.
       - Runs `recover_stuck_jobs` to clean up jobs interrupted by previous process restarts.
       - Starts `run_worker_daemon` in a background daemon thread (`name="evidra-in-process-worker"`).
     - On shutdown:
       - Sets `_worker_stop_event`.
       - Joins worker thread with a 5.0-second timeout for clean termination.
5. **Deployment & Infrastructure Updates:**
   - `render.yaml`: Added `RUN_WORKER_IN_PROCESS: "true"` (Render blueprint already sets `WORKERS: "1"`).
   - `infra/entrypoint.sh`: Updated Uvicorn workers fallback from `${WORKERS:-2}` to `${WORKERS:-1}`.
   - `infra/docker-compose.yml`: Added `WORKERS=1` and `RUN_WORKER_IN_PROCESS=true`.
   - `docs/deploy-render.md`: Documented `RUN_WORKER_IN_PROCESS` and requirement for `WORKERS=1`.
6. **Integration & Lifecycle Tests (`backend/tests/operations/test_in_process_worker.py`):**
   - `test_settings_run_worker_in_process_defaults`: Environment defaults and overrides.
   - `test_recover_stuck_jobs`: Stuck running jobs reset to queued.
   - `test_acquire_next_job_reclaims_expired_lease`: Re-acquires abandoned jobs safely.
   - `test_in_process_worker_executes_queued_import`: Complete end-to-end import run using `TestClient` and `SOURCE_MODE=fixture` (no live network), verifying asynchronous transition from `queued` to `succeeded` and database record persistence.
   - `test_in_process_worker_warns_when_workers_gt_one`: Logs warning when `WORKERS > 1`.

---

## Contract Review: T3 `/capabilities` Endpoint

We have reviewed Developer C's (T3) PR on branch `origin/fix/assistant-disabled`:
- **Model:** `CapabilitiesResponse(llm_enabled: bool, rag_enabled: bool)` with `extra="forbid"`.
- **Route:** `GET /api/v1/capabilities` protected behind `PasswordGateMiddleware`.
- **Security:** Zero leakage of secret keys, spend limits, or AI provider internals.
- **Contract Integrity:** Fully compatible, properly exported to OpenAPI and TypeScript client types.
- **Verdict:** **APPROVED**.

---

## Verification Evidence

| Test Suite | Command | Result |
|---|---|---|
| Contract tests | `uv run pytest tests/contracts` | 12 passed in 1.95s |
| In-process worker tests | `uv run pytest tests/operations/test_in_process_worker.py` | 5 passed in 2.43s |
| Full backend suite | `uv run pytest` | 257 passed in 19.34s |
| OpenAPI schema drift | `uv run python scripts/export_openapi.py --check` | Passed (strictly up to date) |
| Frontend API drift | `npm run api:check` | Passed (schema types strictly up to date) |
| Frontend unit tests | `npm run test:unit` | 11 test files passed (51 passed in 1.22s) |
| Frontend typecheck | `npm run typecheck` | Passed (0 errors) |

### Manual Verification Instructions (Docker Compose)
To test locally using the production Docker container:
```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export SITE_PASSWORD='testpassword123'
docker compose -f infra/docker-compose.yml up --build
```
1. Open http://localhost:8000 and enter `testpassword123`.
2. Create a new review workspace.
3. Save question & criteria.
4. Run search count.
5. Click **Import Records** — verify that the import job transitions from "Queued" to "Importing" to "Completed" automatically within seconds.
6. Open **Screening Workbench** — verify all imported papers appear ready for screening.
