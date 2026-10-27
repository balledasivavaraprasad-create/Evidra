# dev-A — Frontend / full stack (T1)

Execute one assigned prompt at a time. Read the [shared guide](../README.md) and [master merge order](../EXECUTION-AND-MERGE-ORDER.md) first. Folder order is your personal sequence; cross-developer prerequisite merges still apply. Required release work can bypass explicitly deferred optional/bonus prompts.

| Prompt | Task | Must already be merged | Scope |
|---|---|---|---|
| [A01](01-react-foundation.md) | React foundation and premium design system | D01 | required |
| [A02](02-query-import-ui.md) | Query builder and approved import experience | A01, D02 | required |
| [A03](03-review-workbench.md) | Review workbench, duplicate controls and PICO editor | A02, D03 | required |
| [A04](04-premium-3d.md) | Premium 3D experience and Level 1 usability gate | A03, D04 | required |
| [A05](05-history-ui.md) | Version history, conflicts, diff and restore UI | A04, D05, B04, C04 | bonus |
| [A06](06-release-handoff.md) | Deployment packaging, browser acceptance and final handoff | A04, D06, B06, C03 | required |

For each assignment, supply the entire prompt file or ask your coding agent to execute that exact file after reading repository instructions. Do not paste all six at once and allow the agent to ignore dependency gates. Record a separate `prompts/handoffs/<ID>.md` per completed slice; the integration captain consolidates the root audit.
