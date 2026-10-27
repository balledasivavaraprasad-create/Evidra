# C-ML03 - Required ML release verification and final evidence

You are **dev-C**, accountable for finishing ML through backend, frontend and release configuration. Read [the ML addendum](ML-ADDENDUM-EXECUTION.md) and both previous ML handoffs. Complete remaining ML integration yourself; no new ML implementation task goes to A, B or D.

**Branch:** `feat/dev-c-ml03-release-proof`  
**Priority:** required  
**Prerequisite merges:** C-ML02, C05, C06, D06  
**Placement:** after D06, before final acceptance/merge of B06 and A06. Their report/demo preparation can continue while you work.  
**Expected effort:** 2-4 focused hours if data/artifacts and earlier integration are ready.

## Scope and existing work

Use current main, D06's real operations interfaces, the integrated ML screen/API, and the existing C05/C06 gateway/RAG code. Read `prompts/CI-AND-CONTRACTS.md`, `docs/verification-and-release.md` and the integration/security skills. Required ML and Agentic RAG must coexist; they must not depend on each other for ordinary ranking or manual review. No hidden feature cut is permitted by the old optional language.

Own ML backend/frontend/test/evaluation paths from C-ML02, `evals/ml_c/release-evidence.md`, ML-specific setup notes and `prompts/handoffs/C-ML03.md`. Make only necessary ML connection/configuration/packaging fixes within the already-merged application. Do not edit the old planning documents, original prompts, other developers' business logic or unrelated release infrastructure. If final A06 packaging does not yet exist, provide the tested ML startup/artifact procedure and have C verify it again against the final package; that final smoke check remains C's follow-through, not an additional numbered prompt or A's ML implementation assignment.

## Implementation and verification

1. **Verify actual merged dependencies.** Inspect their SHAs and behavior, not only labels or PR titles. C05/C06 are required under this addendum and D06 must expose their selected backend path. If an existing required feature is absent, record an explicit release blocker; do not manufacture success by dropping the assertion. Resolve ML-specific defects in your branch and keep unrelated work moving.

2. **Run a clean model lifecycle.** From a clean environment, reproduce the ML artifact from the documented permitted data/config or restore the trusted release artifact with its verified metadata. Exercise actual inference using the selected review/criteria. Freeze artifact hash, runtime/version, feature settings, training and split identities. A synthetic CI artifact is separate and must never be presented as the production evaluation model.

3. **Verify production-style startup and restart.** Use D06 settings and persistent paths. Load the trusted model from a read-only approved location, avoid repeated training/downloads at startup, and expose clear readiness/applicability status. Restart API/worker and confirm the model/results/provenance survive or regenerate safely through the documented job path. Test missing, corrupt, incompatible and wrong-topic model cases with an honest unavailable state and working manual/rules review.

4. **Measure and bound runtime behavior.** Benchmark the actual supported batch sizes with recorded machine details, queue wait where available, inference duration, memory and failure counts. Test repeated/concurrent requests within configured limits. Avoid blocking UI/API responsiveness or holding SQLite writes during compute. Report actual measurements and limits; do not invent performance thresholds or an organizer score.

5. **Test coexistence with gateway/RAG.** ML ranking remains local and works without model-provider credentials. RAG has its own authorized evidence retrieval, model budgets and validation. Neither path can read another workspace or overwrite human decisions. Check cache identity and safe logs for both; a provider outage must not prevent ML/manual review. Mock provider calls in ordinary CI. Record a separate approved live-provider check when available; if absent, label required live validation pending.

6. **Repeat the real browser journey.** From the workspace, open ML ranking, inspect model/score provenance, switch to baseline order, open a paper, record a manual decision and reload. Verify the decision is unchanged when ranking runs again. Check stale/empty/error states and that current A04 styles/navigation still work. If Level 2 exists, confirm old snapshot provenance is not overwritten by new inference. Resolve ML UI/backend defects yourself.

7. **Publish evaluation ready for the final report.** Run the frozen held-out comparison using the actual release model. Include dataset/label provenance, sample counts, split protection, baseline comparison, quality metrics, unscored cases, runtime and limitations. Include a short plain-English result paragraph and a demo example for B06/A06 to reuse without new ML analysis. Weak performance must remain visible; delivering the model does not justify misleading quality claims.

8. **Close the release gate with evidence.** Run the complete active backend/frontend/browser suites and confirm ML tests were collected and passed. Check that there is a real scored result for an applicable review and a usable screen, not a permanently disabled flag. Verify required C05/C06 status and list any remaining provider or end-user RAG acceptance item under the existing D06/A06 work. Missing ML artifacts or missing required RAG functionality means the whole release is not complete, even if unrelated CI checks are green.

## Acceptance checklist

- A reproducible trained artifact and real local ML inference are available for the declared review scope.
- Frontend controls are fully connected, accessible and tested against the actual API/worker/results path.
- Scores never become automatic exclusions or replace review events.
- Artifact/version mismatch, unavailable data, restarts, stale revisions and repeated requests have tested behavior.
- Backend/unit/browser tests run in the existing CI suite; no skips, fake scores or broad error swallowing.
- Required RAG/gateway and ML can coexist with separate authority, budget and failure boundaries.
- Final quality/performance evidence is measured and reproducible; mocks are labeled as mocks.
- B06/A06 receive finished ML evidence/setup, not new ML coding requests. C completes the final ML smoke against A06 packaging when it becomes available, and fixes ML packaging issues without assigning them to A.

## Final handoff

Write `prompts/handoffs/C-ML03.md` with tested commit and prerequisite SHAs, artifact identity, exact setup/training/inference/test commands, actual results, API/UI locations, clean-start/restart evidence, selected-topic scope, known limits and the remaining final-package smoke status. Keep implementation, local tests, hosted CI, live-model evidence and deployment distinct.

Only mark this task ready for merge when its ML checks pass. B06/A06 final acceptance must include this handoff; a later packaging-only ML check is completed by C before final release sign-off. Normal human PR approval remains in effect, but no other developer receives an ML implementation assignment. Do not auto-merge or deploy without the team's existing release authorization. All existing planning files remain unchanged.
