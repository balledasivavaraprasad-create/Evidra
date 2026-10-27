# Dependency baseline and change policy

## Scope and honesty

This package pins and validates the proposed environments before application implementation. Resolver success, install success, smoke success, application acceptance and deployment verification are different milestones. See [audit](../audit.md) and `docs/validation/` for completed evidence. No claim of “zero bugs” or universal platform compatibility is made.

The manifests currently live in `planning/dependencies/backend/` and `planning/dependencies/frontend/`. At G0, T4/T1 promote their manifests and corresponding locks into the actual `backend/` and `frontend/` application directories **together**. The dependency probes stay as validation tooling; do not advertise them as a product. Do not maintain two divergent active manifests afterward.

## Chosen runtime and direct packages

Use Python **3.12.14** (`>=3.12,<3.13` project constraint), Node **24.22.1** (LTS), uv **0.11.19** for the recorded resolution, and the npm version recorded in validation evidence. Runtime versions are selected from the available checked environment/registry, not copied from old tutorials. Pin the actual deployment base-image digest at release after checking platform and security updates; none is invented here.

| Area | Exact baseline | Purpose |
|---|---|---|
| API | FastAPI 0.162.0, Uvicorn 0.54.0 | Typed HTTP boundary for React |
| Contracts/settings | Pydantic 2.14.1, pydantic-settings 2.16.1 | Validation and server configuration |
| Persistence | SQLAlchemy 2.1.6, Alembic 1.20.1 | SQLite domain repository and migrations |
| Source I/O | HTTPX 0.28.1, defusedxml 0.7.1 | Bounded HTTP and hardened XML |
| Algorithms | RapidFuzz 3.14.6, scikit-learn 1.9.1 | Multi-field similarity and optional classical ML |
| Workflow | LangGraph 1.2.17, langgraph-checkpoint-sqlite 3.1.2 | Durable orchestration and human waits |
| Backend checks | pytest 9.1.1, pytest-cov 7.1.0, respx 0.23.1, Ruff 0.17.2, pip-audit 2.10.1 | Test, mock, lint and advisory tooling |
| UI | React/React DOM 19.3.1 | Web application |
| 3D | Three.js 0.180.0, R3F 9.8.2, Drei 10.7.9 | Scene renderer and helpers |
| UI data/routes | TanStack Query 5.105.0, React Router DOM 7.18.4 | Server cache and navigation |
| Motion/icons | Motion 14.6.0, Lucide React 1.61.0 | DOM animation and icons |
| Build/types | Vite 8.3.5, React plugin 6.1.2, TypeScript **5.9.3** | Production build and compile checks |
| Frontend checks | Vitest 5.0.5, Playwright 1.64.1, openapi-typescript 7.13.0 | Unit/browser tests and generated API types |

Type packages are pinned in the frontend manifest, including `@types/three` 0.180.0 and explicit `@webgpu/types` 0.1.74. The probe enables WebGPU ambient types even though the scene uses WebGL, because Three's declarations reference those types. Transitives, wheel/artifact hashes and exact dependency graph belong to lockfiles; this table does not replace them. Registry metadata checked 26 October 2026 is retained under `docs/validation/`; the initial discovery file contains candidate latest versions, while `direct-dependencies.json` records the final selected pins.

**Actual incompatibility found and corrected:** initially selecting TypeScript 7.0.2 produced npm `ERESOLVE`, because openapi-typescript 7.13.0 requires TypeScript `^5.x`. The corrected baseline uses registry-verified 5.9.3. Do not “fix” this using `--force` or `--legacy-peer-deps`. The resolved R3F v9/Drei v10 pairing is deliberately retained; prerelease/upcoming R3F v10 docs are not the baseline.

Strict declaration checking also found `three-stdlib` loader incompatibilities with the latest Three 0.186 type set. The baseline was moved to matching Three / `@types/three` 0.180.0 and the missing WebGPU ambient declarations were made explicit. `skipLibCheck` remains **false**; the errors were not hidden by disabling library checks. Keep this pairing until an upgrade passes the same probe.

## Reproduce dependency checks

From repository root, with the selected runtimes available:

```sh
uv sync --locked --project planning/dependencies/backend
uv run --locked --project planning/dependencies/backend python planning/dependencies/backend/dependency_smoke.py
cd planning/dependencies/frontend
npm ci --ignore-scripts
npm run check:dependencies
npm ls --all
```

The Python probe checks FastAPI/Pydantic/HTTPX interaction, SQLAlchemy SQLite transactions, a persistent LangGraph interrupt/resume across connections, scikit-learn fitting, RapidFuzz loading and XML entity rejection. The frontend probe checks TypeScript declarations and a production build importing React/R3F/Drei/router/query/motion/icons. It is a build probe, not runtime WebGL/browser QA or the premium website.

Package lifecycle scripts are disabled for initial validation installs. If a future package requires a build script, review that specific package and execute only the required trusted build step; do not silently enable every script. Installing Playwright does not install/test all browsers; browser installation and e2e tests are a separate planned setup step.

Use `uv sync --locked` and `npm ci` in CI. uv documents how locked installs prevent accidental resolution drift ([official documentation](https://docs.astral.sh/uv/concepts/projects/sync/)). A failed frozen install is a blocking inconsistency, not a reason to regenerate locks opportunistically in CI.

## Change process

1. Request the smallest needed dependency and explain why existing tools are insufficient.
2. Manifest owner checks runtime/peer constraints, license/advisories and maintenance, then changes exact direct pins.
3. Resolve the complete lock with the chosen runtime. Do not manually edit transitive versions or mix npm/pnpm/yarn locks.
4. Run relevant dependency probe and application tests; check native wheels on target Linux as well as development machines.
5. Commit manifest + lock + evidence + any migration/behavior changes together in a small dependency PR.
6. Merge before dependent features; everyone performs a frozen sync. Keep versions stable during the final 12 hours unless a security/build defect requires change.

## Deliberately excluded or isolated

- Streamlit: superseded by React, not installed.
- Full LangChain umbrella, provider-specific SDK collection: unnecessary when HTTPX and LangGraph suffice; LangGraph's required transitives remain locked.
- LiteLLM: optional external service behind the typed adapter, **not installed or version-validated here**. T3 must pin a reviewed release/image digest and run gateway contract/security tests before enabling it. Default direct-provider adapter or rules-only operation avoids this dependency.
- Torch/Transformers/CUDA, EBM-NLP training, embeddings: isolated experiment environment only if justified; no GPU install in the core backend.
- Redis, Celery, vector DB, additional browser animation engines: not required by this architecture.
- SQLite engine: Python stdlib linkage, not a pip package. Record `sqlite3.sqlite_version` and FTS5 support on deployment; verify relevant upstream advisories and backup behavior. A Python lock alone does not pin the OS-linked SQLite library.

## Remaining release verification

The [GitHub Actions workflow](../.github/workflows/ci.yml) and [stage-aware command harness](../prompts/CI-AND-CONTRACTS.md) are now authored. They use these frozen environments; D01/A01 move each baseline into its application root, without creating duplicate active manifests. Local harness checks are separate from a successful GitHub-hosted Linux run, which requires the team's real repository.

Actual product tests, Linux deployment build, browser/WebGL checks, live APIs, configured model provider, optional proxy, authentication and hosting persistence remain separate work. Rerun vulnerability tools near release and triage findings; a lockfile is reproducibility evidence, not a security guarantee. See the audit for what was really executed in this planning session.
