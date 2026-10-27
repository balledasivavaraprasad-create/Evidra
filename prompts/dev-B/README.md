# dev-B — Deduplication, screening and ML evaluation (T2)

Execute one assigned prompt at a time. Read the [shared guide](../README.md) and [master merge order](../EXECUTION-AND-MERGE-ORDER.md) first. Folder order is your personal sequence; cross-developer prerequisite merges still apply. Required release work can bypass explicitly deferred optional/bonus prompts.

| Prompt | Task | Must already be merged | Scope |
|---|---|---|---|
| [B01](01-deduplication.md) | Deterministic deduplication engine | D01 | required |
| [B02](02-screening-rules.md) | Explainable screening criteria and rules | B01 | required |
| [B03](03-baseline-evaluation.md) | Baseline evaluation and adversarial algorithm regression | B02, D04 | required |
| [B04](04-group-regression.md) | Group merge/split and cross-version regression suite | B03, D05 | bonus |
| [B05](05-ml-ranking.md) | Optional classical ML ranking with leakage-safe evaluation | B03, A04, C03 | optional |
| [B06](06-final-evaluation.md) | Final evaluation evidence and report contribution | B03, D06 | required |

For each assignment, supply the entire prompt file or ask your coding agent to execute that exact file after reading repository instructions. Do not paste all six at once and allow the agent to ignore dependency gates. Record a separate `prompts/handoffs/<ID>.md` per completed slice; the integration captain consolidates the root audit.
