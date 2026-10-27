---
name: review-data-integrity
description: Implement or review Mini-Rayyan record identity, duplicate groups, reviewer decisions, query versions, conflicts and exact snapshot restoration.
---

Read `../../docs/architecture.md` before changing persistence or grouping. Use `../../docs/verification-and-release.md` for relevant regression scenarios.

Trace source record → immutable text revision → paper group → corpus snapshot before editing. Repeated source IDs upsert; cross-source copies remain attributable. Different reports of the same study are not automatically duplicates. Missing identifiers are never positive matching evidence.

Keep human events separate from machine outputs. A changed group gets explicit lineage; contradictory inherited decisions become a conflict. On split, preserve history and flag ambiguous inherited merged decisions. A changed representative never silently transfers PICO offsets to new text.

Implement snapshot reopen without live fetch or regrouping. Verify historical membership, partitions and representatives remain unchanged after new records bridge old groups. Include idempotent replay and stale-reviewer-write checks when touching mutation logic. Coordinate migrations/contracts with T4; return evidence/proposals from algorithms rather than writing tables there.

Report the exact invariant and tests affected. A planned regression case is not a passed test.
