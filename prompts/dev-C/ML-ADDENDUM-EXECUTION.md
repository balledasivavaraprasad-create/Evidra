# ML addendum: three assignments, all owned by dev-C

This addendum records the user's latest instruction: **classical ML and Agentic RAG are required project deliverables**. This is a team requirement, not a newly discovered organizer scoring rule. Existing plans, prompts, task metadata, CI configuration and the earlier PDF remain unchanged at the user's request. Read this addendum with those files; their older wording that ML/LLM/RAG can be omitted does not describe the latest release scope.

## What changes, in plain English

- C builds the ML model, connects it to the backend, builds its frontend controls, and tests the entire feature.
- A, B and D keep their existing coding assignments. There is no extra ML implementation assignment for them.
- The old B05 experiment is **not selected**. Do not execute it separately or create a second ML implementation. Its file is preserved, not deleted or edited.
- Existing C05 and C06 must be executed for the required gateway/LLM/RAG path. Their old optional labels do not permit omitting them from this release. D06 and A06 must use their already-written integration paths for those features, rather than their optional cut paths. This adds no ML coding to D06 or A06.
- Keeping a rules/manual fallback is required resilience. It does not replace delivery of the working ML and Agentic RAG features.
- Unrelated Level 2 bonus tasks keep their existing scope. The three new prompts are only for ML; they do not expand into a new agent platform.

## Exactly where to run the three prompts

| New prompt | Owner | Earliest safe point | What C completes | Who can continue meanwhile? |
|---|---|---|---|---|
| [C-ML01](07-ml-foundation.md) | C | After D01, C01 and B02 have merged | Training, inference, artifact format, evaluation and pure ML interfaces | A continues A02/A03; D continues D03; B continues baseline evaluation when ready |
| [C-ML02](08-ml-full-stack-integration.md) | C | After C-ML01, D04, B03, C03 and A04 have merged | Authorized ML API, saved results, ML review screen, integration tests | A can work on other UI/release preparation; B on existing evaluation/bonus tasks; D on snapshots/operations |
| [C-ML03](09-ml-release-verification.md) | C | After C-ML02, C05, C06 and D06 have merged | Release-configuration verification, ML compatibility fixes, frontend/browser checks and final ML evidence | A and B can prepare their final report/demo tasks; their final acceptance waits for this result |

**C-ML03 must merge before B06 and A06 are finally accepted.** Their existing prompts are not rewritten. This is the additional release prerequisite carried by this addendum. B does not retrain or implement ML for B06; C supplies a finished evaluation report and verified output. A does not add ML UI in A06; C supplies the finished screen and its browser tests.

### One simple extended merge sequence

Keep the old order for the selected original tasks and insert the new work at these points:

```text
D01 -> A01 -> B01 -> C01 -> D02 -> B02 -> A02
     -> C-ML01
     -> D03 -> C02 -> A03 -> D04 -> B03 -> C03 -> A04
     -> C-ML02
     -> [D05 -> B04 -> C04 -> A05, only if Level 2 is selected]
     -> C05 -> C06 -> D06
     -> C-ML03
     -> B06 -> A06
```

This is a conservative example, **not a new barrier on D03 or other unrelated merges**. If C-ML01 is still being built, D03/C02/A03 may proceed as soon as their existing prerequisites are met. Likewise, unrelated bonus work need not wait for C-ML02. Only the explicit prerequisite lists and final release prerequisite are hard dependencies. A developer can prepare work earlier; final integration uses the actual merged interfaces.

C's suggested personal priority is C01, C-ML01 when B02 is ready, C02, C03, C-ML02, C05, C06, then C-ML03 after D06. If B02 is delayed, do independent ML fixtures and continue ready core work; do not delay C02 just to preserve the displayed personal sequence. C04 remains a bonus and is lower priority than the required ML/RAG work.

## How C can own both backend and frontend without disrupting others

The user explicitly gives C ownership of **the ML feature across layers**. This is a narrow exception to the older A/D ownership rules, not permission to rewrite their subsystems.

C uses isolated paths: `backend/app/ml_feature/`, `backend/tests/ml_feature/`, `frontend/src/features/ml-review/`, `frontend/tests/ml_feature/`, `frontend/tests/e2e/ml-ranking.spec.ts`, and `evals/ml_c/`. C also owns the small registration changes needed to connect that feature to the already-merged app.

C-ML01 must not edit API startup, shared models, frontend routes or other developers' algorithms. C-ML02 waits until D04 and A04 are merged before touching the few connection points. C then handles route registration, generated OpenAPI/TypeScript updates and navigation locally in one scoped integration PR. Use existing authentication, jobs, result storage and UI components. No new dependency or migration should be necessary for the initial feature.

Do not reserve entire files or stop another developer's work. Before a shared-file edit, update from main and inspect the current diff. Keep the change additive and small. If another PR changes the same connection point, serialize those merges, let C resolve the overlap and rerun affected tests. A, B and D continue their unrelated files. There is no promise of zero merge conflicts, but there is no planned transfer of ML implementation work to them.

Normal repository approval still applies. A teammate may approve a PR under existing team policy; that is not a new coding assignment. C performs an explicit second-pass review and all ML tests, but an agent's self-review is not an independent human approval. Nothing here launches review agents or merges automatically.

## Required result, not just an experiment

The release must contain a reproducible scikit-learn training pipeline, a trusted versioned trained artifact, an actual local inference path, a usable ML ranking screen, authorization and failure handling, and measured evaluation on permitted held-out labels. A tiny synthetic test fit proves plumbing only. A notebook, dependency import, hardcoded scores, a permanently unavailable model or an unconnected endpoint does not satisfy this requirement.

ML prioritizes papers for a human reviewer. It must not silently exclude records or replace reviewer decisions. If measured quality is weak, report it honestly and keep the feature clearly marked experimental with baseline ordering available. Do not invent a winning result. If real labels, a valid artifact or applicable review topic are unavailable, record the ML delivery blocker; do not mark required ML complete through the fallback alone. C owns resolving the ML data/evaluation work within permitted sources, not B.

Required Agentic RAG similarly needs C05/C06 plus the existing D06/A06 integration and actual evidence. A missing provider key can leave live-model validation pending; mocks alone do not prove live quality. If A06 takes its old "omit the panel" route, the latest required RAG scope is unfinished. This addendum does not claim those existing tasks are already implemented.

## CI and release checks without rewriting today's workflow

The existing backend CI collects `backend/tests/`; frontend unit tests and browser tests are already assigned to the existing application workflow. C adds real ML tests to those collected suites and verifies collection, rather than creating a disconnected optional test command. C-ML02 makes the ML browser test run under the existing integration stage. C-ML03 checks the full release setup and records actual results.

Current planning CI also discovers the new `tests/planning/test_ml_addendum.py`. It checks the supplemental dependency graph and mandatory ML/RAG release path without changing the original 24-task manifest or workflow. The new graph is recorded separately in [ml-supplement.tasks.json](ml-supplement.tasks.json). Graph checks do not prove implementation, training quality or actual merged commit SHAs.

## Capacity and handoff

Allow approximately 3-5 focused hours for C-ML01, 3-5 for C-ML02, and 2-4 for C-ML03, with additional time if usable labeled data is missing. These are estimates, not guaranteed completion times. The ML time is added to C's existing PICO/LangGraph/RAG workload. Do not pretend all of it is simultaneous work by one person. Prioritize required work over C04 and cosmetic extras; adjust elapsed deadlines if necessary rather than quietly dropping ML or RAG.

Each prompt produces its own `prompts/handoffs/C-MLxx.md`. C's final handoff includes ML setup, artifact identity, tested commit, metrics, screen/API locations and limitations ready for the existing release report. Creating these instructions has not executed any of the three tasks. Existing `audit.md` and the earlier PDF are left untouched; this file is the latest supplemental scope and execution record.

To assign a task, say: **"Read prompts/dev-C/ML-ADDENDUM-EXECUTION.md, then execute prompts/dev-C/07-ml-foundation.md. Implement only that assignment and deliver its tested handoff."** Substitute 08 or 09 only when its prerequisites are actually merged.
