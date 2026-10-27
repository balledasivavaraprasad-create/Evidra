---
name: bounded-research-agent
description: Implement or review Mini-Rayyan LangGraph orchestration, human resume flows, scoped evidence retrieval, LLM gateway policies and agent evaluations.
---

Read `../../docs/agents-and-security.md`; consult `../../docs/architecture.md` for domain transactions and provenance.

Start with the existing deterministic service function. Put orchestration around it, not hidden business logic in prompts. Persist identifiers/fingerprints in checkpoints and keep the business database authoritative. Replayed nodes need idempotent effects; approval nodes validate saved human events before continuing. Never expose graph thread IDs as sufficient authorization.

Give retrieval only the selected workspace/revision and a bounded set of read-only tools. Exact citations and spans must resolve to authorized saved text. Limit retrieval rounds, calls, time, tokens and cost in code. Prefer an abstention over unsupported evidence. Models propose; authenticated reviewer commands decide.

Keep the optional gateway behind the typed adapter. Provider fallback must retain the same policy/privacy contract. A policy/checker outage blocks the AI request while rules remain usable. No arbitrary URL, shell or SQL tools; no secrets in prompts/client bundles/logs.

When adding an agent loop, compare it with rules and one-pass retrieval on the same evaluation cases. Preserve the simpler path unless the extra loop demonstrates a benefit. Test injection, stale citations, budget exhaustion and checkpoint restart. Distinguish dependency smoke from application behavior.
