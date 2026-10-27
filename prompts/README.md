# Developer execution prompts

This folder turns the agreed architecture into **24 implementation prompts**, six per developer. They are ready to assign later; creating them did not execute the application work.

For a simpler explanation, start with the [plain-English merge guide PDF](../output/pdf/merge-order-simple-english.pdf). It explains initial setup, reviewers, who clicks Merge, the required route and optional work.

| Developer | Existing teammate | Responsibility | Prompt folder |
|---|---|---|---|
| dev-A | T1: full stack | Premium React/R3F frontend, browser integration, deployment handoff | [dev-A](dev-A/README.md) |
| dev-B | T2: AI/ML | Deduplication, screening, optional ML and evaluation | [dev-B](dev-B/README.md) |
| dev-C | T3: AI/agentic RAG | PICO, LangGraph, bounded LLM/RAG and model security | [dev-C](dev-C/README.md) |
| dev-D | T4: backend | Contracts, sources, SQLite, reviewer services, snapshots and operations | [dev-D](dev-D/README.md) |

## Start sequence

1. Read the [master execution and merge order](EXECUTION-AND-MERGE-ORDER.md).
2. Read [CI and contract conventions](CI-AND-CONTRACTS.md).
3. Commit this planning/CI bootstrap to the team's chosen repository and run its initial checks. Configure branch protection and real teammate identities separately; no remote exists here yet.
4. Assign **D01 first**. After it merges, A01, B01, C01 and D02 can proceed in parallel.
5. Assign one prompt at a time. Use the exact prompt file as the developer/agent task; it includes prerequisite checks, scope, implementation steps, failure cases, tests and handoff requirements.

Example assignment: “Execute `prompts/dev-B/01-deduplication.md` in this repository. Read its prerequisites and referenced instructions, implement the scoped work, run its checks, and deliver the handoff. Do not execute later prompts automatically.” Use the appropriate file for the developer; the master order determines readiness.

## What each prompt delivers

A reviewable code slice on a short named branch, observable tests, concrete exported interfaces and its own `prompts/handoffs/<ID>.md`. The handoff records upstream merge SHAs, verification evidence, limits and newly unblocked work. Avoid four developers editing the root audit simultaneously. The captain consolidates it at integration/release gates.

Use the [handoff template](handoffs/TEMPLATE.md) for each slice. No completed handoffs exist yet.

All application prompts preserve: LLM-off Level 1; source and reviewer history; paper/study distinction; immutable snapshots; exact PICO text offsets; typed contracts; explicit model proposals; bounded calls and authorization. The existing [plan](../docs/implementation-plan.md), [architecture](../docs/architecture.md), [security](../docs/agents-and-security.md) and [UI direction](../docs/frontend-design.md) remain the domain reference.

## Optional work and priorities

The graph has **17 required**, **4 bonus**, and **3 optional** prompts. Required release work has no hard dependency on bonus/optional work. D05/B04/C04/A05 form the coherent Level 2 bonus chain; B05 is optional ML; C05/C06 are optional model/RAG modules. If those are selected for release, the conditional integration rules in the master order apply.

An assigned optional prompt can be executed without another preference question. If time is insufficient, the captain records an explicit cut; an agent must not mark the missing feature complete. The required one-page Level 2 design exists regardless of bonus implementation.

## GitHub Actions scope

The [workflow](../.github/workflows/ci.yml) executes checks on pull requests, pushes to `main`, merge-queue groups, manual dispatch and a weekly advisory refresh. It does **not** run these natural-language prompts, create application code, merge PRs or deploy automatically. No LLM/provider secret is required for ordinary CI. Live-source and live-model checks remain separately configured manual evidence.

The [task manifest](tasks.json) supports consistency checks. It is not a progress tracker and does not prove predecessor PRs merged. The captain verifies actual SHAs and review/check status before accepting a dependent PR.
