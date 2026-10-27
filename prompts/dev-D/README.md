# dev-D — Backend, sources, persistence and integrity (T4)

Execute one assigned prompt at a time. Read the [shared guide](../README.md) and [master merge order](../EXECUTION-AND-MERGE-ORDER.md) first. Folder order is your personal sequence; cross-developer prerequisite merges still apply. Required release work can bypass explicitly deferred optional/bonus prompts.

| Prompt | Task | Must already be merged | Scope |
|---|---|---|---|
| [D01](01-foundation-contracts.md) | Backend foundation and frozen contracts | Bootstrap only | required |
| [D02](02-source-import.md) | Live literature adapters and durable import jobs | D01 | required |
| [D03](03-review-services.md) | Reviewer services and deterministic pipeline integration | D02, B02, C01 | required |
| [D04](04-level1-integration.md) | Level 1 wiring, authorization and integrated CI activation | D03, C02, A03 | required |
| [D05](05-snapshot-services.md) | Version snapshots, decision lineage and exact restoration | D04, B03, C03, A04 | bonus |
| [D06](06-operations-release.md) | Operational hardening and release configuration | D04, B03, C03, A04 | required |

For each assignment, supply the entire prompt file or ask your coding agent to execute that exact file after reading repository instructions. Do not paste all six at once and allow the agent to ignore dependency gates. Record a separate `prompts/handoffs/<ID>.md` per completed slice; the integration captain consolidates the root audit.
