# Level 2 loop design — submission text

**Question → versioned query → approved fetch → stored corpus → deduplicate → screen → PICO → human review/export → query or criteria edit.** Human events are stored separately from machine results. This is the required design; implementation of the loop is bonus work.

| Step | What a person can change | Recompute / preserve |
|---|---|---|
| 0 Question/criteria | PICO question, active rules, reasons | New criteria version; re-screen affected records; preserve and flag prior human decisions for reaffirmation |
| 1 Query | Keyphrases, Boolean grouping, dates, sources | New immutable query version and search execution; retain old counts, selections and snapshots |
| 2 Fetch | Which searches to import, cap, retry partial import | Fetch unseen source IDs; add memberships for known IDs; preserve saved metadata revisions and source provenance |
| 3 Database | Active set of approved searches | New corpus revision; removals affect the active view only; no deletion of records or review history |
| 4 Duplicates | Confirm/reject pair, merge/split, representative | Recompute affected combined-corpus groups; store group snapshot and lineage; preserve all records and decisions |
| 5 Screening | Include/Exclude/Maybe, reason | Append group-level human event; never overwrite machine output; downstream PICO only for newly included/changed abstracts |
| 6 PICO | Correct label or exact span | Append annotation tied to text revision/hash; unchanged text retains edits; changed text flags stale annotations |
| 7 Review/export | Resolve conflict, undo, export, revisit old version | Append corrective event; export a named revision and decision cutoff; keep older exports traceable |

**Decision preservation:** an excluded paper found again retains its decision through stable identity/group lineage. If groups with incompatible human decisions merge, the new group is a visible conflict; no automatic choice, and no inclusion in export until resolved. On split, inherited merged decisions require review. Annotations never silently move to different text.

**Incremental work:** each result keys off content, criteria, grouping, method/model/prompt and input version. Reuse only exact matches. A failed job resumes from committed stages; unique keys prevent duplicate writes. Logs record revision, stage, attempt, time, outcome and provenance.

**Diff and exact revert:** compare saved snapshots for added/removed records and changed groups. Reopen an old snapshot's saved membership, text, groups, representatives and outputs, with decisions at its recorded cutoff. Do not query live servers or regroup on revert. Offer a separately labeled latest-decisions view if implemented.

**Acceptance examples:** excluded record reappears → still excluded; included/excluded groups merge → conflict; new bridge changes groups → prior snapshot unchanged; revert v1 → same saved record set and partition; crash/resume → no lost human event or duplicate effect.

**Submission note:** a one-page PDF is provided at `../output/pdf/level-2-loop-design.pdf`. Re-render and verify its page count after changing this source. Organizer scoring details and frozen-dataset format remain unknown.
