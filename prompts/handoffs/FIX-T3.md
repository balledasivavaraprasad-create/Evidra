# FIX-T3 — Assistant Disabled Preemptive Handling & Capabilities Contract

Status: ready for review

## Identity and scope

- **Developer and reviewer:** dev-C (T3 bounded research agent / PICO owner); Reviewer: dev-D (T4 contracts owner) & dev-A (T1 frontend owner)
- **Branch:** `fix/assistant-disabled`
- **Issue:** On the live site `LLM_ENABLED=false` and `RAG_ENABLED=false` by design (`render.yaml`). Calling `POST /api/v1/workspaces/{id}/assistant` returns HTTP 501 (`NOT_IMPLEMENTED`). The Assistant panel previously still prompted the user to submit inquiries and failed with an error.
- **Assigned scope:**
  1. Backend: Add small read-only `GET /api/v1/capabilities` returning `{"llm_enabled": bool, "rag_enabled": bool}` from settings. Sits behind the shared password gate like other `/api` routes. No secrets, provider names, or API keys exposed.
  2. Contracts: Define `CapabilitiesResponse` with strict `extra="forbid"`. Regenerate `contracts/openapi.json` and `frontend/src/api/schema.d.ts`. Add contract tests. Request T4 review as contract owner.
  3. Frontend: Edit only `frontend/src/features/review-queue/AssistantPanel.tsx` (plus `frontend/src/api/client.ts` for the API method). When both flags are false, display a calm note: *"AI assistant is turned off in this demo. Rules-based screening and manual review work as normal."* Disable the input (textarea, task selectors, and submit button). Retain friendly message resilience if a 501 is returned.
  4. AGENTS.md rule invariant: Rules-based screening and manual review continue to work completely unimpeded when AI is turned off.

---

## Prerequisite evidence

| Item | Status | Notes |
|---|---|---|
| Latest `main` (`6dc1b8a`) | Inspected & branched | Branched to `fix/assistant-disabled` without pushing to main |
| `render.yaml` | Inspected | Confirmed `LLM_ENABLED=false`, `RAG_ENABLED=false` on free tier blueprint |
| `PasswordGateMiddleware` | Inspected | Gating applies to `/api/*` prefix except `/api/v1/auth/` |
| `AGENTS.md` | Inspected | Rule: "If AI policy validation fails [or is disabled], disable that AI request and keep rules/manual review available." |

---

## Implemented behavior

1. **Backend Endpoint (`backend/app/main.py`):**
   - Implemented `GET /api/v1/capabilities` returning `CapabilitiesResponse(llm_enabled=bool(settings.llm_enabled), rag_enabled=bool(settings.rag_enabled))`.
   - Sits behind `PasswordGateMiddleware` (when `AUTH_MODE=password`, unauthenticated requests receive 401 `AUTH_REQUIRED`).
   - Zero sensitive information: response is strictly limited to two boolean feature flags; provider names, spend limits, and secrets are forbidden.

2. **Domain Contracts & Schema (`backend/app/contracts/models.py`, `contracts/openapi.json`, `frontend/src/api/schema.d.ts`):**
   - Added `CapabilitiesResponse` with `model_config = ConfigDict(extra="forbid")`.
   - Exported OpenAPI via `python backend/scripts/export_openapi.py`.
   - Regenerated TypeScript client types via `npm run api:generate`.
   - Verified zero schema drift via `npm run api:check` and `python backend/scripts/export_openapi.py --check`.

3. **Frontend Resilience (`frontend/src/features/review-queue/AssistantPanel.tsx` & `frontend/src/api/client.ts`):**
   - Exported `CapabilitiesResponse` and added `api.capabilities.get()` in `client.ts`.
   - In `AssistantPanel.tsx`:
     - Checks `api.capabilities.get()` on mount (supports `initialCapabilities` prop for unit testing).
     - When `bothFlagsDisabled` (`!capabilities.llm_enabled && !capabilities.rag_enabled`):
       - Displays calm note: *"AI assistant is turned off in this demo. Rules-based screening and manual review work as normal."*
       - Disables the textarea prompt, inquiry task buttons, and submit button with disabled styling.
     - When a 501 or 503 is returned reactively from `api.assistant.query`:
       - Catches `ApiError` and sets friendly message *"AI assistant is turned off in this demo. Rules-based screening and manual review work as normal."*
       - Disables the input to prevent repeated failed requests.
   - Preserves core AGENTS.md invariant: Level 1 deterministic rules-based screening and human review actions are completely unaffected.

---

## Cross-Owner Request for T4 (Contracts Owner)

> **Notice for T4:**
> T4 owns contracts, schemas, and API migrations. We have added an additive schema change:
> - Model: `CapabilitiesResponse` in `backend/app/contracts/models.py`
> - Route: `GET /api/v1/capabilities` in `backend/app/main.py`
> - Deterministic OpenAPI: Regenerated `contracts/openapi.json` via `backend/scripts/export_openapi.py`
> - Frontend API types: Regenerated `frontend/src/api/schema.d.ts` via `npm run api:generate`
> Please review this additive change. `npm run api:check` and contract checks pass without drift.

---

## Verification evidence

| Check | Command | Environment | Result |
|---|---|---|---|
| Capabilities API & Flag Tests | `python -m pytest tests/capabilities` | Python 3.12, SQLite | 3 passed (flags off, flags on, password gate) |
| Contract Schema Tests | `python -m pytest tests/contracts` | Python 3.12, SQLite | 11 passed (including `test_openapi_json_is_up_to_date` and `test_capabilities_response_contract`) |
| Full Backend Test Suite | `uv run pytest` / `python -m pytest` | Python 3.12, SQLite | 256 passed in 9.16s |
| OpenAPI Schema Drift Check | `python scripts/export_openapi.py --check` | Python 3.12 | Passed: `contracts/openapi.json is strictly up to date.` |
| Frontend Typecheck | `npm run typecheck` | TypeScript 5.9.3 | Passed (0 errors) |
| Frontend Unit Tests | `npm run test:unit` | Vitest 5.0.5 | 12 test files passed (55 passed tests, including 4 in `assistant_panel.test.tsx`) |
| Frontend API Drift Check | `npm run api:check` | Node.js | Passed: `OpenAPI schema types are up to date.` |
| Frontend Production Build | `npm run build` | Vite 8.3.5 / Rolldown | Built in 316ms (0 errors) |

---

## Release & Review Checklist

- [x] Branch `fix/assistant-disabled` checked out from latest `main`.
- [x] Changes kept local; no commits pushed to `main`.
- [x] Only `AssistantPanel.tsx` and `client.ts` modified in frontend feature code.
- [x] Calm note displayed and inputs disabled when both flags are false.
- [x] Friendly 501 error recovery retained.
- [x] AGENTS.md invariant upheld: rules and manual review unaffected.
- [x] Contract owner (T4) notified for review.
