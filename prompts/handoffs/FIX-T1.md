# FIX-T1 — Search save 400 and 404s after a Render restart

Status: implemented and tested locally; not deployed, not verified on the live Render site

## Identity and scope

- Branch: `fix/frontend-flow`, created from `origin/main` at `6dc1b8a`. Pushed for review via PR to `main`; not merged.
- Owner area: T1 frontend. One additive backend route was needed (see "Decision for the captain").

## Bug 1 — "Save query" returned HTTP 400

Cause: `QueryBuilderPage` passed `criteriaVersion?.id || "crit-ver-default"`. Before the review question was saved, the placeholder was posted and the API replied 400 `Associated criteria version ... not found in workspace`.

Changed:
- `QueryBuilderPage.tsx`: passes `criteriaVersion?.id ?? null`. Removed the old paragraph above the builder (the hint now sits by the buttons).
- `QueryBuilder.tsx`: the `"crit-ver-default"` default is gone. "Save Query Version" and the "Count on …" buttons are disabled until a criteria version exists, with the hint "Save the review question first." (`aria-describedby` links the buttons to it). The handlers also refuse to run without one.
- Every review (demo and others): the page loads the latest saved criteria via `GET /api/v1/workspaces/{id}/criteria` (new `api.criteria.latest`, `features/search/savedCriteria.ts`) before showing the editor, so reloading the setup page keeps the question and the search buttons unlocked. A review with nothing saved gets the empty form (the lookup returns 404, which is expected and handled). The demo seed stores PICO as `P/I/C/O`; the loader maps these to `population/intervention/comparator/outcome`, which is what the editor reads, so the demo form is not blank.

## Bug 2 — pages 404 after the database is wiped

Changed:
- `context/currentWorkspace.ts`: `reconcileRememberedWorkspace(ids)` clears a remembered review the server no longer lists and falls back to `DEMO_WORKSPACE_ID`; `forgetWorkspaceId(onlyIf?)`. `Header` calls it once on load with `api.workspaces.list()`. If the list cannot be fetched (service down) the remembered review is kept.
- `components/WorkspaceGuard.tsx` (new) wraps all `/reviews/:id/...` routes (`App.tsx`, now nested). It looks the review up once; if missing it shows `ErrorState` ("This review doesn't exist") with a "Go to your reviews" button and does not mount the page, so no per-section 404s are requested. If the list call itself fails, the page renders as before (offline/sample-data behaviour is unchanged).
- The guard now remembers a review only after the server confirms it (`Header` used to remember any URL, including a dead one). It also keys the page by review id so state such as a saved question cannot carry over between reviews.
- `Feedback.tsx`: `ErrorState` gained optional `actionLabel` / `onAction`.

## Decision for the captain: new backend route

The task said to use `GET /api/v1/workspaces/{id}/criteria`, but only `POST` existed. I added an additive, read-only `GET` at that path in `backend/app/main.py` (returns the newest version; 404 for an unknown workspace or when nothing is saved) and regenerated `contracts/openapi.json` and `frontend/src/api/schema.d.ts`. T4 owns contracts: please review or reject this. If rejected, the demo can only get its saved question another way.

## Verification (all run locally on Windows)

| Check | Result |
|---|---|
| `npm run typecheck` (frontend) | pass |
| `npm run test:unit` | 70 passed (12 files); 19 are new in `src/tests/workspace_flow.test.tsx` |
| `npm run build` | pass |
| `npm run api:check` | up to date |
| `uv run --locked pytest -q` (backend) | 255 passed; 3 new in `tests/workspaces/test_latest_criteria.py` |
| Browser flow (headless Chromium via Playwright library, real local servers) | 19/19 checks, plus 4/4 for reloading a non-demo review's setup page |

Browser flow covered: new review → Query page shows Save/Count disabled plus the hint; saving the question enables Save; saving the query works with no 4xx; the demo review loads its saved question and PICO and saves a query without a 400; a stale remembered ID is cleared and the menu links point at the demo; `/reviews/ws-ghost/records` shows the error state and the button returns to `/reviews`.

The new tests were checked to fail on the old behaviour (forcing the gate open makes the disabled-button tests fail).

## Limits and known issues

- Not tested on Render. The deployed demo only exists when `SEED_DEMO=true`; without it, opening the demo URL shows the "doesn't exist" state, which is correct but worth knowing.
- The page's effect-driven load of saved criteria is covered by the browser run plus unit tests of the loader and the unlocked builder, not by a rendered-page unit test (no jsdom).
- The vitest setup is node-only (no jsdom / Testing Library, none added). UI behaviour is covered by server-rendering the components plus the manual browser run above; the guard's effect-driven redirect itself is covered only by the browser run.
- `python scripts/ci/run_checks.py frontend` crashes on this Windows machine (`FileNotFoundError` starting `npm`), unrelated to this change; the same npm commands were run directly. Hosted CI has not run.
- `ruff check app/main.py` reports one import-order error that is identical on `origin/main` before this change.
- Local database was behind (new migrations 003–007 on main), so `alembic upgrade head` was needed before seeding.
