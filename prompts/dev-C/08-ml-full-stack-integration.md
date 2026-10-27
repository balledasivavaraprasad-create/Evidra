# C-ML02 - Required ML backend and frontend integration, owned by C

You are **dev-C**. Deliver the full ML feature from the trained model to the actual React interface. Read [the ML addendum](ML-ADDENDUM-EXECUTION.md) and C-ML01's handoff first. The user explicitly assigns the ML-specific backend and frontend implementation to you; do not turn this task into work tickets for A, B or D.

**Branch:** `feat/dev-c-ml02-full-stack`  
**Priority:** required  
**Prerequisite merges:** C-ML01, D04, B03, C03, A04  
**Placement:** after A04 and the other listed prerequisites; before final release integration. C05/C06 do not depend on the ML model.  
**Expected effort:** 3-5 focused hours.

## Preparation and limited ownership exception

Read `AGENTS.md`, `docs/architecture.md`, `docs/frontend-design.md`, `prompts/CI-AND-CONTRACTS.md`, and the literature, premium UI and integration skills. Inspect the real authenticated API, worker, result-storage, review UI and test configuration on latest main. Reconcile C-ML01's evaluation with B03's published criteria/split protocol yourself, without asking B to redo evaluation.

Own `backend/app/ml_feature/`, `backend/tests/ml_feature/`, `frontend/src/features/ml-review/`, `frontend/tests/ml_feature/`, `frontend/tests/e2e/ml-ranking.spec.ts`, `evals/ml_c/` and your handoff. You may make the minimum additive edits to API/router registration, worker registration if needed, existing result-service adapters, frontend route/navigation, deterministic OpenAPI and generated TypeScript so this feature actually works. This exception covers ML connection points only. Do not rewrite A's workbench, D's authentication/jobs, B's rules, dependencies, migrations, the old plan or prompts.

Update from main before each shared-file change. If another PR changes a connection point, let it merge first where practical, then rebase and resolve the ML patch yourself. Existing developers continue their other work. No lock or schema change is expected; if a real architectural mismatch requires one, document and resolve the smallest compatible approach within your task rather than silently bypassing constraints.

## Backend implementation

1. **Use the real domain services.** Read only the selected authorized workspace/corpus revision and its records through existing repositories. Verify membership server-side; a browser-supplied workspace ID is not authority. Derive actor/context on the server and load the configured trusted model, never a path or provider URL from the request.

2. **Add a narrow ML route contract.** Prefer isolated `/api/v1/workspaces/{workspace_id}/revisions/{revision_id}/ml-ranking` operations, adapting naming to the merged app. Support an authorized ranking request and paginated readback/status using existing job conventions for nontrivial work. Document 401/403, stale revision/criteria, model missing/incompatible, oversized corpus and unavailable-result responses. Do not hold a database transaction while computing inference. Bound records, text size, queue/concurrency and time using the existing worker rather than an unbounded task spawn.

3. **Persist versioned results without a parallel database.** Reuse existing machine-result/run storage, adding ML payloads through an adapter. Fingerprints include workspace, corpus/text revision, criteria/question and model/feature versions. Repeated requests reuse or safely update the same computation under the established idempotency contract. A version mismatch invalidates reuse; no silent scoring from another workspace or model. No model result writes a reviewer event.

4. **Keep inference observable.** Record trace/job ID, method/model version, counts, duration, success/unavailable/failure and safe error reason through existing run logging. Distinguish inference time from queue wait where the existing system exposes it. Do not log private notes, secrets or full text unnecessarily. Record local ML cost as not an external token charge; do not invent token accounting for scikit-learn.

5. **Make the contract real.** Register routes and any worker handler; run the deterministic OpenAPI export and regenerate the shared TypeScript types yourself. Preserve existing generated types and endpoints. Test the route is reachable from the actual application, not only from an isolated test router.

## Frontend implementation

6. **Build an isolated ML review screen.** Use `frontend/src/features/ml-review/` with a small navigation entry from the existing review workspace. Render actual records ranked by the backend score, a baseline-order toggle, model version/scope and score explanation. Link to the already-existing paper/review detail screen. Keep model suggestions visibly distinct from inclusion/exclusion decisions. Do not add another animation library or redesign the website.

7. **Handle the entire state model.** Implement loading/queued/running, empty, scored, partial/unscored, expired/stale, model unavailable, incompatible criteria and request-error states. Cache by workspace, corpus, criteria and model identity. Cancel/ignore old responses after navigation. Disable unavailable actions with an explanation; do not display placeholder scores. Keep keyboard use, narrow screens, readable contrast and reduced motion consistent with A's design.

8. **Preserve workflow behavior.** Ranking changes order only. Existing reviewer controls, PICO edits, saved decisions and exports retain their semantics. If ML fails, users can still open baseline ordering and review papers; do not label this fallback as successful ML delivery. Handle restored snapshots using stored result provenance if Level 2 exists; do not make bonus snapshots a prerequisite for ML.

## Tests that must run in existing CI

- Backend: cross-workspace access rejected; stale corpus/criteria rejected or explicitly unavailable; model incompatibility/corruption handled; repeat requests idempotent; text limits enforced; result provenance preserved; no reviewer-decision changes.
- Inference: compare route output to the real C-ML01 pipeline on the same inputs; use a trusted tiny synthetic fitted artifact in CI, never hardcoded scores pretending to be inference.
- Frontend unit: loading/error/unavailable views, score-versus-decision labels, cache identity, stable tie order and baseline toggle.
- Browser: `frontend/tests/e2e/ml-ranking.spec.ts` uses the real fixture-backed backend and actual ML inference. Open the screen, rank papers, switch ordering, follow a paper link, and verify existing decisions survive. Include missing-artifact and unauthorized cases where appropriate.
- Contract/build: actual OpenAPI/type drift checks, strict TypeScript, nonempty unit suite, real production build and the existing integration browser command.

Add tests to the existing collected paths and verify discovery. Do not create a manual-only script while the normal CI suite skips ML. Do not enable all integration stages before their actual prerequisites or rewrite today's workflow to hide failures. Live data/provider access is not required in ordinary ML CI.

## Handoff

Write `prompts/handoffs/C-ML02.md`: upstream SHAs; reachable API and screen paths; example requests/results/errors; artifact setup; actual shared files touched; generated-schema evidence; backend/frontend/browser results; telemetry examples without sensitive data; known limits; and precise release checks remaining for C-ML03. State that A and D have no ML coding handoff to implement.

Do a separate second-pass review of permissions, artifact trust, stale caches and decision preservation. Submit one small integration PR under existing review policy. Do not merge automatically, publish a service, or report a real-provider/model-quality test from fixture results. Keep the original plans and prompts unchanged.
