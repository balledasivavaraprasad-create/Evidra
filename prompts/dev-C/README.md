# dev-C — PICO, LangGraph, bounded AI and security (T3)

Execute one assigned prompt at a time. Read the [shared guide](../README.md) and [master merge order](../EXECUTION-AND-MERGE-ORDER.md) first. Folder order is your personal sequence; cross-developer prerequisite merges still apply. Required release work can bypass explicitly deferred optional/bonus prompts.

| Prompt | Task | Must already be merged | Scope |
|---|---|---|---|
| [C01](01-pico-baseline.md) | Exact-span PICO baseline | D01 | required |
| [C02](02-langgraph-pipeline.md) | Durable LangGraph pipeline and human review subgraph | C01, D03 | required |
| [C03](03-agent-security.md) | Agent boundaries, replay safety and baseline security | C02, D04 | required |
| [C04](04-incremental-graph.md) | Incremental graph execution and snapshot-aware replay | C03, D05, B04 | bonus |
| [C05](05-llm-assistance.md) | Optional budgeted LLM gateway and validated extraction | C03, B03, A04 | optional |
| [C06](06-bounded-rag.md) | Optional bounded, cited corpus RAG assistant | C05 | optional |

For each assignment, supply the entire prompt file or ask your coding agent to execute that exact file after reading repository instructions. Do not paste all six at once and allow the agent to ignore dependency gates. Record a separate `prompts/handoffs/<ID>.md` per completed slice; the integration captain consolidates the root audit.
