# FIX-T2 — Group Screening Decision Concurrency & Row Version Sync

Status: implemented, verified locally with full backend regression tests, Vitest unit tests, and interactive browser verification.

## Identity and scope

- **Developer:** dev-B (T2 deduplication, screening, and ML evaluation owner)
- **Assigned Prompt:** FIX-T2
- **Prerequisite Dependencies:** T4's `contract/group-row-version` (PR #9 / commit `2aeab9d`), merged into `main`.
- **Branches:**
  - Work branch: `fix/screening-version` (branched from latest `main` at `598216f`).
  - Merge branch: `screening-decision`.
- **Target Component:** `frontend/src/features/review-queue/ReviewQueuePage.tsx` (strictly edited ONLY `ReviewQueuePage.tsx` in that folder; `AssistantPanel.tsx` untouched as owned by T3).

---

## Bug Description & Root Cause

### Bug
On the live review workbench, consecutive screening decisions (`POST /api/v1/groups/{group_id}/decisions`) or PICO extraction saves failed repeatedly with HTTP 409 `STALE_VERSION_CONFLICT`. Reviewers were stuck unable to record multiple decisions or update PICO without manual hard refreshes.

### Root Cause
In `frontend/src/features/review-queue/ReviewQueuePage.tsx`, the optimistic versioning used a local state dictionary:
```tsx
const [groupVersions, setGroupVersions] = useState<Record<string, number>>({});
const getVersion = (id: string) => groupVersions[id] || 1;
```
This local map was completely decoupled from the database record:
1. It defaulted to `1` regardless of the actual server `row_version`.
2. It was only bumped locally upon action success.
3. If any previous decision, PICO extraction save, candidate merge, or other reviewer action occurred, the server's `group.row_version` incremented (e.g., to 2 or 3), but the frontend kept guessing `expected_version: 1`, triggering repeated 409 rejections.
4. On 409 error, the UI showed an error banner but never refreshed the record detail or list entry from the server, permanently deadlocking the view.

---

## Fix Implementation

1. **Server-Authoritative Version Sync (`ReviewQueuePage.tsx`):**
   - Removed `groupVersions` state and `getVersion` helper function entirely.
   - Both `handleDecision` and `handleSavePico` now resolve `currentVersion` directly from server state:
     ```tsx
     const currentVersion =
       (groupDetail?.group?.id === selectedGroup.id ? groupDetail.group.row_version : selectedGroup.row_version) ?? 1;
     ```
   - Updated the header version indicator from guessed `v{getVersion(id)}` to server-backed `v{group.row_version}`.

2. **Immediate Detail Refetch & List State Update:**
   - After every successful screening decision (`api.groups.recordDecision`) or PICO save (`api.groups.savePico`):
     - Automatically calls `api.groups.getDetail(selectedGroup.id, revisionId)` to retrieve the newly incremented `row_version`.
     - Updates `groupDetail` and maps over the `groups` list state so the selected group's `row_version` and decision status are immediately synchronized for subsequent actions.

3. **Self-Healing 409 Recovery:**
   - On an HTTP 409 `ApiError`, the component intercepts the conflict, automatically fetches the fresh group detail via `api.groups.getDetail`, updates both `groupDetail` and the `groups` list item with the latest `row_version`, clears the blocking modal conflict flag, and displays:
     > *"This paper was updated. Your view has been refreshed — please choose again."*
   - The user is never left stuck in an unrecoverable state.

---

## Tests & Verification

### 1. Backend Regressions (`backend/tests/regressions/test_screening_version.py`)
- `test_two_consecutive_decisions_succeed_with_updated_version`: Validates that on a single paper group, the initial decision with `expected_version=1` increments `row_version` to 2; the subsequent decision with `expected_version=2` succeeds and increments `row_version` to 3.
- `test_stale_expected_version_raises_409`: Confirms that sending a stale `expected_version=1` against a group at version 2 raises `HTTPException(409, STALE_VERSION_CONFLICT)`.
- `test_consecutive_decisions_via_api_endpoints`: End-to-end FastAPI `TestClient` verification testing `POST /api/v1/groups/{id}/decisions` -> `GET /api/v1/groups/{id}` -> second `POST /api/v1/groups/{id}/decisions` -> 409 rejection on stale version.

### 2. Frontend Vitest Suite (`frontend/src/tests/screening_version.test.ts`)
- `decision -> refetch -> second decision sends the new row_version`: Simulates two consecutive reviewer decisions via mocked API calls, asserting that the first sends `expected_version: 1`, detail refetch returns `row_version: 2`, and the second decision correctly delivers `expected_version: 2`.
- `handles 409 conflict by refetching group and offering user-friendly message`: Asserts that when a 409 is encountered, group detail is refetched to synchronize the state and the exact error notification is presented.
- `source guard`: Asserts `ReviewQueuePage.tsx` contains no references to `groupVersions`, `setGroupVersions`, or `currentVersion + 1`, and enforces presence of `row_version` and the required user-facing notification string.

### 3. Test Results Summary

| Suite | Command | Result |
|---|---|---|
| Backend Pytest | `cd backend && uv run pytest` | **265 passed** in 6.95s (all test suites passing) |
| Frontend Typecheck | `cd frontend && npm run typecheck` | **0 errors** (clean `tsc --noEmit`) |
| Frontend Vitest | `cd frontend && npm run test:unit` | **73 passed** (13 test files, 100% passing) |
| OpenAPI Drift Check | `cd frontend && npm run api:check` | **Up to date** (contracts match schema) |

### 4. Interactive Browser Verification on Demo Review
Tested on the live running application (`http://localhost:5180/reviews/ws-synth-001/records`) using headless Chromium automation:
1. Paper group `grp-8746fabbe02b` started at `row_version: 1`.
2. Action 1: Clicked **"Include Study"** -> HTTP 200 OK -> UI banner `"Decision 'INCLUDE' successfully saved for group grp-8746fabbe02b."` -> Version badge updated to `v2`.
3. Action 2: Clicked **"Exclude (Select Reason...)"** -> Selected reason *"Preclinical animal model without human participants"* -> Clicked **"Confirm Exclude"** -> HTTP 200 OK -> UI banner `"Decision 'EXCLUDE' successfully saved for group grp-8746fabbe02b."` -> Version badge updated to `v3`.
4. Action 3: Clicked **"Maybe"** -> HTTP 200 OK -> UI banner `"Decision 'MAYBE' successfully saved for group grp-8746fabbe02b."` -> Version badge updated to `v4`.
5. No 409 conflict errors encountered throughout the full multi-decision workflow.

---

## Handoff & Merge Details

- **Files Modified:**
  - `frontend/src/features/review-queue/ReviewQueuePage.tsx`
- **Files Added:**
  - `backend/tests/regressions/test_screening_version.py`
  - `frontend/src/tests/screening_version.test.ts`
  - `prompts/handoffs/FIX-T2.md`
- **Branch and Merge:**
  - Work committed to `fix/screening-version`.
  - Merged into branch `screening-decision` and rebased/merged to `main`.
