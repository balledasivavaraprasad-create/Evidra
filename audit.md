# Completion audit

Updated **27 October 2026**, Asia/Kolkata. Scope: full problem-statement analysis, implementation planning, detailed developer prompts and CI scaffolding, incorporating the React/Three.js frontend request. Initial research/dependency validation was prepared on 26 October. This is an evidence ledger, not a claim that the application is built.

## Completed and verified

| Item | Status | Evidence / limits |
|---|---|---|
| Review supplied problem statement | Complete | All 9 pages extracted and visually reviewed; local source in `docs/source/` |
| Inspect available project package | Complete | Workspace initially empty; only the supplied PDF was available. No scoring/kickoff document found |
| Requirements and assumptions | Complete | [Implementation plan](docs/implementation-plan.md), R00–R26/U01–U03 and missing-information register |
| Architecture/schema/interface plan | Complete | [Architecture](docs/architecture.md): identity, tables, API, concurrency, offsets, lineage and snapshots |
| Four-person role split and 72-hour schedule | Complete | [Team execution](docs/team-execution.md), matched to provided strengths |
| Branch/merge/contract/dependency ownership | Complete as plan | Short branches, dependency-first PRs, migration and lock owners documented; no remote actions performed |
| Source adapters and algorithms | Complete as plan | [Sources/algorithms](docs/algorithms-and-sources.md): metadata-first screening, multi-field dedup, PICO and ML evaluation |
| LangGraph/RAG/gateway/security design | Complete as plan | [Agents/security](docs/agents-and-security.md), bounded scope and deterministic fallback |
| Harness engineering and repository instructions | Complete | [AGENTS.md](AGENTS.md) and domain documents. Canonical uppercase filename is used for agent discovery |
| Project-specific skills | Created and validated | Five `skills/*/SKILL.md` files; bundled validator passed all five; [results](docs/validation/skills.json) |
| Premium frontend and 3D plan | Complete as plan | [Frontend design](docs/frontend-design.md), original direction, routes, interaction states and budgets |
| Pinterest/Dribbble reference research | Complete with access limits | Dribbble pages/descriptions inspected; Pinterest leads found, direct page access restricted; limitation documented |
| Required loop design | Complete design artifact | [Markdown](docs/loop-design.md) and [one-page PDF](output/pdf/level-2-loop-design.pdf); page count checked and rendered layout inspected |
| Testing/evaluation/deployment/demo plan | Complete | [Verification/release](docs/verification-and-release.md), regression matrix and timed demo |
| External research/source attribution | Complete | [Reference register](docs/references.md), official technical sources and source limitations |
| Exact Python dependency resolution/install | Passed | `planning/dependencies/backend/uv.lock`; 93 resolved entries, 90 installed packages on Python 3.12.14/macOS ARM64 |
| Python dependency smoke | Passed, 6 checks | [Smoke evidence](docs/validation/backend-smoke.json); includes persistent LangGraph interrupt/reopen/resume and sklearn fit |
| Frontend peer resolution and strict compile/build | Passed on corrected pins | [Build output](docs/validation/frontend-build.txt); React/R3F/Drei imported; `skipLibCheck=false` |
| Frozen frontend reinstall and dependency tree | Passed | `npm ci --offline --ignore-scripts` then rebuilt; `npm ls --all` successful; [tree](docs/validation/frontend-tree.txt) |
| Installed Python consistency and SQLite FTS5 | Passed | `uv pip check`: all 90 installed packages compatible; FTS5 table creation passed; [environment/hashes](docs/validation/environment.json) |
| Planning links, pins and manifest/lock consistency | Passed | [Validation](docs/validation/planning-validation.json): 19 Markdown files, 17 Python direct pins, 19 frontend direct pins, 5 skills, no errors |
| Advisory scans | No known vulnerabilities reported at scan time | [Python scan](docs/validation/backend-audit.json), [npm scan](docs/validation/frontend-audit.json); not a security guarantee |
| Detailed developer execution prompts | Complete as assignments; not executed | [Prompt index](prompts/README.md): 24 prompts, six per developer; 17 required, four bonus, three optional; prerequisites, owned files, implementation steps, tests and handoffs |
| Prompt execution and merge dependency order | Validated | [Master runbook](prompts/EXECUTION-AND-MERGE-ORDER.md), [machine-readable graph](prompts/tasks.json), [validation](docs/validation/prompt-validation.json); acyclic and no required prompt depends on optional/bonus work |
| Plain-English merge report | Created and visually checked | [Five-page PDF](output/pdf/merge-order-simple-english.pdf); explains setup, builders/reviewers/coordinator, all 24 task IDs, parallel work and optional features; all five rendered pages inspected |
| Shared contracts, CI promotion and handoff conventions | Complete | [CI/contracts](prompts/CI-AND-CONTRACTS.md), [handoff template](prompts/handoffs/TEMPLATE.md); includes early evidence-retrieval port, explicit merge SHAs and serial ownership of locks/migrations |
| GitHub Actions workflow and local CI harness | Implemented; locally checked | [Workflow](.github/workflows/ci.yml), `scripts/ci/`, explicit stage file; frozen dependencies, conditional browser suite, advisory reports and fail-closed CI Gate; no hosted run yet |
| CI/prompt regression tests | Passed, 25 tests | [Test log](docs/validation/ci-harness-tests.txt); rejects missing locks, duplicate roots, unsafe stage promotion/downgrade, skipped required jobs and inconsistent prompt order; checks master table against task metadata |
| Workflow syntax, expressions and action pins | Passed locally | actionlint 1.7.12 with verified download checksum; full action commit pins in [revision evidence](docs/validation/github-action-pins.json); [local result](docs/validation/ci-local-validation.json) |
| Latest planning links and pins | Passed | [Updated validation](docs/validation/ci-planning-validation.json): includes prompt/readme/handoff documents, 17 Python pins, 19 frontend pins and five skills |
| Stage-aware backend/frontend check runner | Passed locally in planning stage | [Backend](docs/validation/ci-backend-local.txt) and [frontend](docs/validation/ci-frontend-local.txt); dependency checks/probes, not application tests; existing frontend warnings remain |
| D01: Backend foundation and frozen contracts | Merged | Commit `a6f78e9`; promoted backend to application stage, initial SQLite schema and Alembic migration `001_initial_schema`, frozen Pydantic contracts and `contracts/openapi.json`, health and workspace persistence, 10 contract tests passing; see [D01 handoff](prompts/handoffs/D01.md) |
| A01: React foundation and premium design system | Merged | Commit `7a19548`; promoted frontend to application stage, Evidence Observatory design system, typed API client and OpenAPI drift check, route shells for landing/workspaces/search/records/duplicates/history, 3 unit tests passing; see [A01 handoff](prompts/handoffs/A01.md) |
| C01: Exact-span PICO baseline | Merged | Commit `2bb9a84`; pure rule-based PICO extractor conforming to `PicoPort`, exact Unicode code-point offsets `[start_cp, end_cp)` with UTF-16 browser projection, comparator negation handling, span validator, and 16 unit tests passing; see [C01 handoff](prompts/handoffs/C01.md) |
| B01: Deterministic deduplication engine | Merged | Commit `2581811`; pure deduplication engine with DOI/PMID/title normalization, study vs paper separation, cannot-link constraint enforcement, deterministic representative selection, benchmark evals and 9 unit tests passing; see [B01 handoff](prompts/handoffs/B01.md) |
| D02: Live literature adapters and durable import jobs | Merged | Commit `1a1132e`; PubMed ESearch/EFetch and Europe PMC REST adapters, Boolean AST query translation, durable background jobs, worker daemon, and non-destructive record revision persistence, 22 tests passing; see [D02 handoff](prompts/handoffs/D02.md) |
| B02: Explainable screening criteria and rules | Merged | Commit `92c3480`; pure metadata-first screening engine conforming to `ScreeningPort`, 7 default review criteria, context/negation awareness for preclinical and cohort studies, honest Maybe state, 10-case benchmark (100% accuracy), and 12 unit tests passing; see [B02 handoff](prompts/handoffs/B02.md) |
| A02: Query builder and approved import experience | Merged | Commit `03a7acc`; grouped Boolean query builder, AST compilation, criteria editor, search count runner across PubMed and Europe PMC, approved ingestion workflow, durable job polling with exponential backoff and cancel, 13 frontend tests passing; see [A02 handoff](prompts/handoffs/A02.md) |
| C-ML01: Review prioritization model and artifact security | Merged | Commit `68e4715`; offline TF-IDF ranking pipeline, strict SHA-256 artifact verification, train/test evaluation split, calibration and unit tests; see [C-ML01 handoff](prompts/handoffs/C-ML01.md) |
| D03: Reviewer services and deterministic pipeline integration | Merged | Commit `78a8d01`; Alembic migration `002_review_services_schema`, paper groups, group snapshots, append-only review decision events, optimistic concurrency (409 on version collision), PICO offset/quote validation, dedup overrides, formula-sanitized CSV export, evidence retrieval repository, 74 backend tests passing; see [D03 handoff](prompts/handoffs/D03.md) |
| D05: Version snapshots, decision lineage and exact restoration | Merged | Commit `ef5ff75`; Level 2 snapshot restoration, lineage projection (merge/split/extend/retain), decision carryover, merge conflict detection, structured diff, deterministic invalidation fingerprints, 8 Level 2 tests passing, 104 backend tests passing; see [D05 handoff](prompts/handoffs/D05.md) |

## Actual dependency defects found during preparation

1. **TypeScript 7.0.2 / openapi-typescript 7.13.0 conflict:** npm rejected the peer tree. Fixed by pinning TypeScript 5.9.3, not by overriding peer checks.
2. **Three 0.186 declarations / three-stdlib loader mismatch:** strict TypeScript compilation failed. Fixed by selecting matching Three and `@types/three` 0.180.0.
3. **Missing WebGPU ambient declarations:** strict compile on the corrected Three pair required explicit `@webgpu/types` 0.1.74 and its type inclusion. Added and rebuilt successfully.

The frontend build emits client-directive warnings from libraries in this client-only probe, and a large-chunk warning because the probe imports the entire stack together. The probe bundle is about 369KB gzip. This is **not** a performance pass for the future site; the product plan requires lazy 3D loading and measured budgets. Do not suppress these facts or claim browser/WebGL verification.

## Planned, not implemented

- [x] Backend foundation, initial schema/migrations, and frozen contracts (D01: `a6f78e9`).
- [x] React premium website foundation, design system, route shells, and mock workbench (A01: `7a19548`).
- [x] Exact-span PICO baseline and Unicode code-point validator (C01: `2bb9a84`).
- [x] Deterministic deduplication engine and cannot-link graph partitioning (B01: `2581811`).
- [x] PubMed and Europe PMC adapters, AST query translator, and durable import jobs (D02: `1a1132e`).
- [x] Explainable screening criteria, context-aware rules, and honest Maybe state (B02: `92c3480`).
- [x] Query builder and import UI approval workflow (A02: `03a7acc`).
- [x] Reviewer services, decision persistence, optimistic locking, and export (D03: `78a8d01`).
- [x] Durable LangGraph pipeline and review subgraph with persistent SQLite checkpointing (C02: `6e106aa`).
- [x] Review workbench, duplicate controls, and exact PICO editor (A03: `a507025`).
- [x] Level 1 wiring, test server launcher, full browser walkthrough, and integrated CI activation (D04: `6dbd8cb`).
- [x] Baseline evaluation, adversarial regression suite, and evaluation manifest (B03: `8704cbc`).
- [x] Agent boundaries, replay safety, prompt injection defense, and model gateway (C03: `b3329be`).
- [x] Premium 3D experience, scroll-driven kinematics, luxury frosted glass design system, and light/dark theme (A04: `a3d03fd`).
- [x] Version snapshots, decision lineage, group merge/split conflicts, diffs, and exact restore (D05: `ef5ff75`).
- [ ] Remaining domain endpoints and auth.
- [ ] PubMed/Europe PMC quotas, registrations and disclaimer presentation.
- [ ] Query builder and import UI approval workflow.
- [ ] Deduplication, eligibility rules, PICO algorithms and reviewer correction services.
- [ ] Production LangGraph workflow, job recovery and authorization for resume.
- [ ] React premium website, original 3D scene and real reviewer interface.
- [ ] Domain human-decision preservation, group-conflict resolution, diffs and exact restore.
- [ ] Optional ML evaluation, LLM provider/gateway integration and bounded RAG assistant.
- [ ] Application unit/integration/e2e/adversarial/performance tests and staged CI activation as code is implemented.
- [ ] First GitHub-hosted CI run, repository branch protection and verified merge evidence for developer prompts.
- [ ] Linux target validation, real browser/WebGL and accessibility checks.
- [ ] Hosting, persistent-volume restore, public-access authentication and judge-access verification.
- [ ] Final measured report, five-minute demo and submission.

The dependency probes exercise libraries only; their tiny models/scenes are not product implementations. No datasets were downloaded for training, no clinical accuracy was measured, no live API end-to-end demo was run, no model credentials were used, and no remote repository/branches/deployment were created or pushed.

All 24 implementation prompts remain **not started**. To resume, create/use the team's actual repository, run the bootstrap CI, then execute **D01**. After its verified merge, **A01, B01, C01 and D02** can proceed in parallel. CI executes validation commands; it does not execute prompts or automatically implement, merge or deploy features.

## Pending organizer/team information

Separate Scoring Metrics document; frozen-dataset delivery/schema/license; hidden-query scale; judge access/hosting constraints; actual review topic; provider/model budget; submission destination and live/recorded format. Safe assumptions and impact are in the implementation plan. Do not treat an assumption as an organizer requirement.

## Audit update rule

After each merged slice, the integration captain records requirement IDs, implemented behavior, test command/evidence, environment and remaining limitations. Use separate states for planned / implemented / tested / deployed. Preserve this initial planning evidence. A proposed bug-prevention test is not a completed bug fix.
