# CI stages, contracts and developer commands

## Current bootstrap and promotion rules

The workflow is implemented now; the application is not. `.ci/stages.json` explicitly selects the active dependency roots and required checks. CI will not quietly skip an application because a folder is missing.

| Milestone / owner | Stage change | Required deliverables |
|---|---|---|
| Current bootstrap | backend=planning, frontend=planning, integration/level2/ai=false | Existing locked environments, dependency probes, planning/prompt validators |
| D01 | backend=application | Move whole backend baseline to `backend/`; app/main, contracts test, Alembic, OpenAPI export/check, dependency probe retained |
| A01 | frontend=application | Move whole frontend baseline to `frontend/`; app entry, generated API types, real typecheck/unit/build/type-drift scripts, dependency probe retained |
| D04 | integration=true | Real fixture-backed API/worker server launcher and Playwright Level 1 tests |
| D06, only if selected bonus complete | level2=true | Backend exact snapshot tests and browser restore suite from A05 |
| D06, only if assistant integrated | ai=true | Authorized endpoint wiring and deterministic adversarial assistant tests; runtime models still default-off |

Move each baseline, do not copy it into a second independently active tree. `dependency_smoke.py` stays in the active backend root; `probe/` stays in the active frontend root. The historic validation evidence remains as a dated planning record. Update the selected-version metadata if direct pins change. The Python manifest stays pinned and `package=false` is acceptable while modules run from the backend working directory.

`validate_stage.py` rejects dual roots, missing files/scripts and stage regression relative to the PR base. A new feature's tests join the normal collected suites even before the global milestone flag is enabled. Stage files do not authorize weakening coverage. Reviewers must still verify tests exercise real behavior; file existence alone is not behavioral proof.

## Exact local check commands

Run from the repository root with Python 3.12.14, Node 24.22.1, npm 11.14.1 and uv 0.11.19 available. Choose the active root printed by the first command; the examples below use the current planning roots until D01/A01 move them.

```sh
python scripts/ci/validate_stage.py
python scripts/validate_planning.py
python scripts/validate_prompts.py
python -m unittest discover -s tests/planning -v
uv sync --locked --project planning/dependencies/backend
npm ci --prefix planning/dependencies/frontend --ignore-scripts --no-audit --no-fund
python scripts/ci/run_checks.py backend
python scripts/ci/run_checks.py frontend
```

After promotion, use `uv sync --locked --project backend` and `npm ci --prefix frontend --ignore-scripts --no-audit --no-fund`; the check runner chooses active roots itself. Do not regenerate a lock just because CI disagrees. Never use `npm --force`, `--legacy-peer-deps`, `skipLibCheck=true`, empty-test success flags or broad test skips to hide a failure.

Once D04 activates integration:

```sh
# Install the locked Playwright browser once; run this from frontend/.
npm exec --no -- playwright install chromium
# Return to repository root.
python scripts/ci/run_checks.py e2e
```

GitHub-hosted Linux also installs Chromium OS dependencies. The workflow installs packages/tools and consults vulnerability databases over the network; **application tests** use fixtures and no live literature/model services. `CI_OFFLINE=1` and `SOURCE_MODE=fixture` must be enforced by D01/D02 test adapters, not merely treated as decorative environment variables.

## Required backend commands and files

- `uv run --locked ruff check app tests scripts` from backend: check actual application/test/support code.
- `uv run --locked alembic heads`: exactly one head; `alembic upgrade head` must succeed on a fresh temporary SQLite DB.
- `uv run --locked python scripts/export_openapi.py --check`: compare deterministic app schema to root `contracts/openapi.json`, do not silently rewrite it.
- `uv run --locked pytest -q`: collects nonempty tests, including new domain/security suites and enabled features. Default fixtures deny external I/O.
- `backend/app/testing/serve.py` (D04): CI-only disposable DB migration/seed and loopback API/worker launcher. It refuses non-test mode, uses synthetic source transport, cleans up child processes and never creates a public reset/seed endpoint.

Keep callable ports in `backend/app/contracts/ports.py`. D01 must define algorithm inputs/outputs plus the read-only authorized snapshot evidence port and optional proposal/gateway envelope, so optional modules do not need to invent authority or table writes. D03 implements persistence services; C02 wraps those services; D04 wires the worker. This prevents a circular dependency where each developer waits for another to implement the same orchestration layer.

## Required frontend npm scripts

| Script | Owner implementation / failure behavior |
|---|---|
| `check:dependencies` | Preserve the strict existing type/build probe; it remains separate from the product |
| `typecheck` | Compile application types strictly; library declarations are not globally ignored |
| `test:unit` | Nonwatch Vitest run with real tests; zero tests fails |
| `build` | Build the actual React site, not only probe/index.html |
| `api:generate` | Generate `src/api/schema.d.ts` from root `contracts/openapi.json` |
| `api:check` | Generate to a temporary file, compare to committed types, fail on mismatch |
| `test:e2e` | Nonwatch Playwright Chromium suite; configured webServer startup/health; no permanent skip of required workflow |

A03 provides `frontend/playwright.config.ts` and `frontend/tests/e2e/level1.spec.ts`; full execution begins with D04. Configure backend API at loopback 8000 and frontend preview at 4173, waiting for health/readiness and cleaning up. The launcher command, relative to frontend, is `uv run --locked --project ../backend python -m app.testing.serve`; set its working directory/module path correctly (for example run it with backend as cwd via the webServer configuration). Do not rely on app imports from the wrong working directory. Prefer command `uv run --locked python -m app.testing.serve` with `cwd` explicitly set to `../backend`.

Use `reuseExistingServer: !process.env.CI`, bounded startup timeout, isolated test DB, screenshots/traces on failure and no live service credentials. Browser tests exercise real routes/services; mocking all browser API calls does not satisfy integrated acceptance. A05 adds `tests/e2e/level2/restore.spec.ts`; D06 adds/activates optional assistant endpoints only when safe.

## Workflow behavior and limits

The jobs are **validation**, **backend**, **frontend**, **e2e** when activated, **security**, and the stable **CI Gate**. Backend/frontend run in parallel after validation. Gate runs even when a dependency fails/cancels and rejects required jobs that were unexpectedly skipped. Select `CI Gate` as the required branch-protection check after the first remote run.

Actions are pinned to verified commit SHAs; actionlint is pinned with SHA-256 checksums. Checkout credentials are not persisted, permissions are read-only, no production secrets are injected, and the workflow does not use `pull_request_target`. No deployment step exists. Artifacts contain only test/advisory evidence with short retention, not DBs, `.env`, arbitrary logs or provider keys.

Python advisories fail the security job for reported vulnerabilities; npm high/critical findings block it and lower-severity findings remain in the report for review. Network/advisory outages fail visibly; rerun or fix the service issue rather than adding `continue-on-error`. A clean scan is not proof of no vulnerabilities. Account-specific Actions policies/quotas and chosen-host compatibility remain to be confirmed in the first real remote run.

This pipeline does not itself enforce human PR ordering, install a GitHub repository, set branch protection, perform clinical evaluation or deploy. The captain checks predecessor merge SHAs and selected optional features. Actual hosted-run evidence must be recorded after pushing to the team's real repository.

Reference checks used to author the workflow: [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), and [actionlint](https://github.com/rhysd/actionlint). See `docs/validation/github-action-pins.json` for the checked action revisions.
