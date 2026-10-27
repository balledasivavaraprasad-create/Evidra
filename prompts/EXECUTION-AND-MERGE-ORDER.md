# Prompt execution and merge order

This is the integration captain's runbook. Developer mapping is fixed: **A=T1 full stack**, **B=T2 dedup/screen/ML**, **C=T3 PICO/agents**, **D=T4 backend**. The machine-readable dependency graph is [tasks.json](tasks.json); CI validates IDs, dependency order, acyclicity and required-path independence from optional work.

## Bootstrap before implementation

Commit this planning/prompt/CI package to the team's chosen repository after it is created. No remote is configured in this workspace yet. Enable GitHub Actions and run the supplied workflow on the bootstrap commit. This first run validates planning, dependency probes, workflow syntax and advisory reports; it does not certify a working product. Choose an integration captain and map A–D to actual repository identities.

Protect `main` with **CI Gate**, a reviewer approval and up-to-date branch/merge-queue checks where available. Configure actual reviewer permissions in GitHub; a YAML file cannot grant repository branch protection by itself. Do not add fake CODEOWNERS usernames. CI checks changes; it does not execute developer prompts, call coding agents, auto-merge PRs or deploy the product.

## Canonical merge queue (one valid total order)

Read each row as “merge this developer's prompt after all prerequisites and checks pass.” This order is deliberately conservative and gives the requested explicit sequence. Independent ready rows may swap; prerequisites may never be bypassed. Optional rows may be omitted with an explicit cut recorded by the captain; required rows never depend on them.

| Merge | Prompt / developer | Deliverable | Hard prerequisite merges | Scope | Reviewer |
|---|---|---|---|---|---|
| 1 | [D01 — dev-D](dev-D/01-foundation-contracts.md) | Backend foundation and frozen contracts | Bootstrap | required | A + B + C (contracts) |
| 2 | [A01 — dev-A](dev-A/01-react-foundation.md) | React foundation and premium design system | D01 | required | D |
| 3 | [B01 — dev-B](dev-B/01-deduplication.md) | Deterministic deduplication engine | D01 | required | D + C |
| 4 | [C01 — dev-C](dev-C/01-pico-baseline.md) | Exact-span PICO baseline | D01 | required | A + B |
| 5 | [D02 — dev-D](dev-D/02-source-import.md) | Live literature adapters and durable import jobs | D01 | required | A |
| 6 | [B02 — dev-B](dev-B/02-screening-rules.md) | Explainable screening criteria and rules | B01 | required | D + C |
| 7 | [A02 — dev-A](dev-A/02-query-import-ui.md) | Query builder and approved import experience | A01, D02 | required | D |
| 8 | [D03 — dev-D](dev-D/03-review-services.md) | Reviewer services and deterministic pipeline integration | D02, B02, C01 | required | A + C |
| 9 | [C02 — dev-C](dev-C/02-langgraph-pipeline.md) | Durable LangGraph pipeline and human review subgraph | C01, D03 | required | D |
| 10 | [A03 — dev-A](dev-A/03-review-workbench.md) | Review workbench, duplicate controls and PICO editor | A02, D03 | required | C + D |
| 11 | [D04 — dev-D](dev-D/04-level1-integration.md) | Level 1 wiring, authorization and integrated CI activation | D03, C02, A03 | required | A + C |
| 12 | [B03 — dev-B](dev-B/03-baseline-evaluation.md) | Baseline evaluation and adversarial algorithm regression | B02, D04 | required | C + D |
| 13 | [C03 — dev-C](dev-C/03-agent-security.md) | Agent boundaries, replay safety and baseline security | C02, D04 | required | D + A |
| 14 | [A04 — dev-A](dev-A/04-premium-3d.md) | Premium 3D experience and Level 1 usability gate | A03, D04 | required | D + C |
| 15 | [D05 — dev-D](dev-D/05-snapshot-services.md) | Version snapshots, decision lineage and exact restoration | D04, B03, C03, A04 | bonus | B + C + A |
| 16 | [B04 — dev-B](dev-B/04-group-regression.md) | Group merge/split and cross-version regression suite | B03, D05 | bonus | D + C |
| 17 | [C04 — dev-C](dev-C/04-incremental-graph.md) | Incremental graph execution and snapshot-aware replay | C03, D05, B04 | bonus | D + B |
| 18 | [A05 — dev-A](dev-A/05-history-ui.md) | Version history, conflicts, diff and restore UI | A04, D05, B04, C04 | bonus | D + B |
| 19 | [B05 — dev-B](dev-B/05-ml-ranking.md) | Optional classical ML ranking with leakage-safe evaluation | B03, A04, C03 | optional | C + D |
| 20 | [C05 — dev-C](dev-C/05-llm-assistance.md) | Optional budgeted LLM gateway and validated extraction | C03, B03, A04 | optional | D + B |
| 21 | [C06 — dev-C](dev-C/06-bounded-rag.md) | Optional bounded, cited corpus RAG assistant | C05 | optional | D + B |
| 22 | [D06 — dev-D](dev-D/06-operations-release.md) | Operational hardening and release configuration | D04, B03, C03, A04 | required | A + C |
| 23 | [B06 — dev-B](dev-B/06-final-evaluation.md) | Final evaluation evidence and report contribution | B03, D06 | required | C + D |
| 24 | [A06 — dev-A](dev-A/06-release-handoff.md) | Deployment packaging, browser acceptance and final handoff | A04, D06, B06, C03 | required | D + B + C |

## Ready-to-start parallel waves

These are work/merge dependency waves, not a demand to keep idle teammates waiting for unrelated branches. The precise hour windows remain in each prompt and the earlier team timeline.

| Wave | Work that can proceed together | Required gate before final merge |
|---|---|---|
| 0 | D01 foundation; A sketches visual tokens, B/C draft fixtures without shared-file edits | Bootstrap CI exists; only D01 merges first |
| 1 | A01, B01, C01, D02 | D01 merged; all use its same contract commit |
| 2 | A02 after A01+D02; B02 after B01; C prepares graph tests against frozen ports | Each prompt's actual prerequisites |
| 3 | D03 integration services; A/C prepare work against its published contract proposal | D02+B02+C01 merged before D03 |
| 4 | A03 review workbench and C02 LangGraph | D03 merged; no circular worker/API changes |
| 5 | D04 wires API/worker/graph/browser; B/C/A fix owner-scoped integration bugs | A03+C02 merged; required e2e becomes active |
| 6 | A04 premium UI, B03 baseline evaluation, C03 security; D reviews/fixes services | D04 merged; all three finish **G3 / Level 1** |
| 7 | D05 bonus snapshots, B05 optional ML, C05 optional LLM; A prepares history layouts | G3 complete. Cut optional work if baseline is unstable |
| 8 | B04 after D05; C06 after C05; D prepares operations | Persisted contracts actually merged, not just promised |
| 9 | C04 after B04; A prepares history tests | D05+B04+C03 merged |
| 10 | A05 bonus history/restore UI; B prepares report evidence | C04 + A04 + D05 + B04 merged |
| 11 | D06 operations and selected optional wiring; then B06 final evidence; then A06 release | Follow final release conditions below |

The optional branch sequence in the canonical table is **not** an added dependency: B05 and C05 may merge while the D05→B04→C04→A05 bonus chain proceeds. Dev-A may prototype the 3D scene earlier in an isolated component, but A04 integration waits for the working review flow. Dev-D should draft runbooks during quieter windows; D06's final merge uses the selected feature set.

## Named checkpoints

- **Hour 4 / foundation:** D01 merged; A/B/C verify examples and signatures, not just read them.
- **Hour 12 / steps 1–3:** D02 and A02 integrated, with D01/A01 in place; a small live query approved/imported/persisted. B01/C01 baseline functions are progressing; documents/criteria/loop design exist.
- **Hour 24–30 / integration:** D03+C02+A03+D04 merged. Real fixture-backed browser/API/DB/worker flow passes. `integration=true` makes browser CI mandatory.
- **Hour 36 / G3:** A04+B03+C03 merged on top of D04; Level 1 works with LLM disabled. Only now start optional implementation in earnest.
- **Hour 60 / release candidate:** selected extras completed or explicitly cut; D06 runbook/security prepared; report evidence available. Freeze features.
- **Hour 72 / submission:** B06+A06 finalize tested evidence, setup/report/demo and actual access arrangement. Do not equate green CI with a hosted service.

## Conditional release prerequisites

| Claimed release feature | Extra merge requirements before release | CI/runtime consequence |
|---|---|---|
| Level 1 only | All required prompts; skip D05/B04/C04/A05/B05/C05/C06 if necessary | integration=true; level2=false; ai=false; LLM/RAG off |
| Full Level 2 experience | D05 → B04 → C04 → A05 all merged before D06 finalizes | D06 enables level2=true; backend and browser restore tests required |
| Classical ML ranking | B05 accepted by evaluation, then D06 integration | Runtime ranking optional; baseline rules continue; actual tests included |
| LLM module experiment only | C05 with honest scope | Do not advertise an assistant UI or set ai=true merely for module-only work |
| Delivered bounded assistant | C05 → C06 → D06 authorized endpoint wiring → A06 UI and acceptance | D06 enables ai CI; provider runtime still default-off until configured; all AI tests mocked in ordinary CI |

If D06 already merged before a later selected optional feature, create a small dev-D **D06 follow-up integration PR**, merge it before B06/A06 final acceptance, and record the additional SHA. Do not sneak new endpoint/schema work into dev-A's release PR. If the follow-up cannot fit, defer the optional feature. A06 may omit the optional panel and label AI as an experiment rather than claiming user delivery.

## Per-prompt branch/merge protocol

1. Verify prerequisite handoffs and actual merged commit SHAs on `main`. Draft PR links alone do not satisfy a dependency.
2. Branch from current `main` using the prompt's branch name. One branch per prompt; do not keep four long-lived divergent developer branches.
3. Make small owner-scoped commits. Share additive contract changes early through dev-D, and frontend lock changes through dev-A. Consumers wait for the real contract merge, not hand-copied types.
4. Run the declared checks and write your own `prompts/handoffs/<ID>.md`. Open the team's reviewable PR using its established authorized Git workflow. Never invent a repository URL or reviewer username.
5. Captain verifies dependencies, requested reviewer, CI stage, migration head, lockfile ownership and handoff evidence. Update branch from `main` and rerun affected checks after conflict resolution.
6. Squash/merge through the team's configured policy; capture the merge SHA in the handoff. Shared audit updates happen through the captain. Never force-push `main` or auto-merge unreviewed application code.
7. Notify dependent owners through the team's agreed channel. These prompt files do not send messages on their own.

Do not cherry-pick a shared dependency into several branches and then merge it again. If using stacked PRs, state the base explicitly and retarget only after the parent merges. Prefer dependency-first small PRs over complex stacks during the event.

## Hot files and collision rules

- `.ci/stages.json`: D01 edits backend; A01 edits frontend **after D01**; D04 edits integration **after A03/C02**; D06 edits selected bonus/AI flags. No other prompt edits it.
- `.github/workflows/ci.yml`, `scripts/ci/`: dev-D is maintainer after bootstrap. Dev-A proposes frontend changes through a reviewed dev-D integration patch; routine UI features do not rewrite CI.
- `contracts/openapi.json`, `backend/app/contracts/`, Alembic migration chain, backend lock: dev-D only. Dev-B/dev-C return pure values and contract requests.
- `frontend/src/api/schema.d.ts`, frontend lock and npm scripts: dev-A only; regenerate types from merged OpenAPI.
- `audit.md`: captain consolidates in D04, D06 and A06's serialized release update. Everyone else writes their own prompt handoff.
- `docs/review-question.md`: B02 owns proposed criteria; team approval is recorded. Do not modify a clinical question silently from a model branch.

## Blockers and resuming later

A missing dependency stops dependent integration/merge, not independent fixture/design work. Write a precise blocker: required symbol/field, owner, consuming prompt, smallest upstream patch and test. Preserve current changes; do not copy another developer's subsystem into your branch to appear unblocked.

On returning later, read `audit.md`, inspect merged handoffs/PRs, run the current CI stage locally, then choose the earliest unfinished ready prompt. The metadata order is a plan, not a completion record. No implementation prompt has been executed by creating this package.
