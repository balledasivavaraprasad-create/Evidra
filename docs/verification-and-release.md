# Verification, evaluation, deployment and five-minute demo

## Test layers and evidence

| Layer | Tests to implement | Owner |
|---|---|---|
| Unit | DOI/title normalization, pair constraints, criterion aggregation, negation, exact PICO offsets, fingerprints | T2/T3 |
| Contract | Pydantic request/output validation; exported OpenAPI and generated TS agreement; status/error enums | T4/T1 |
| DB | Migration from empty/previous release; foreign keys; replay/upsert; event projection; transaction rollback; backup restore | T4 |
| Adapter | Recorded synthetic XML/JSON: missing abstracts, namespaces, 429, partial pages, cursor stalls, malformed payload | T4 |
| Graph | Durable checkpoint interruption/resume, repeated resume, crash after domain commit, unauthorized resume, budget cap | T3 |
| Browser | Search → import → decisions → PICO correction → CSV; stale edits, reload, keyboard controls | T1 |
| Security | Cross-workspace access, prompt injection, XSS, CSV injection, dangerous source URLs, forged citations | T3 coordinates; owners implement |
| Performance | Import 200/1,000 synthetic records; candidate-pair count; review latency; memory; 3D frame time and bundle sizes | All |
| Live smoke | Small PubMed + Europe PMC requests within limits; optional configured model request | T4/T3; separate from offline CI |

The planning package's dependency smoke checks do **not** constitute any of the above application acceptance tests. The audit distinguishes them.

## Must-pass Level 1 scenario

Create a review and criteria; save two queries with counts; approve a small live import; show stored provenance; discover an exact duplicate and an uncertain fuzzy pair; reject one incorrect duplicate; screen an animal-only synthetic record with a reason; include a previously Maybe paper; annotate/correct P/I/C/O; export included representatives; restart the application and confirm records and human changes remain. Repeat with LLM disabled. Use synthetic cases only where labeled as such, and live APIs for the required demo search.

## Level 2 regression scenarios

| Test | Expected invariant |
|---|---|
| Excluded paper appears in query B | Same retained human decision and provenance |
| Included A and excluded B become one duplicate group | Visible conflict; no silent resolution or export inclusion |
| A new record bridges two groups | New snapshot/lineage; historical partition untouched |
| Reviewer rejects A–B duplicate, later rerun | Cannot-link respected until explicit reviewer change |
| Group split after prior merged decision | Preserve event; require review of ambiguous inheritance |
| Criteria toggle/change | Version increments, affected machine results invalidated; human events retained/flagged |
| Same query refreshed after remote data changes | New execution, original snapshot remains available |
| Restore initial snapshot after several edits | Exact saved IDs, metadata revisions, group partition and representative choices |
| Worker killed after DB write, before checkpoint | Replay produces no duplicate domain effect |
| API retry/double click | Same idempotent command result; changed payload with reused key rejected |
| Two reviewers update same group version | One succeeds; stale request gets 409 and is recoverable |
| Representative abstract changes | Old PICO edits retained with old text; no silent offset transfer |

Make group/record identity comparisons set-based and deterministic; timestamps and random IDs must not mask a changed partition. These are our proposed tests derived from the pre-read, not the unavailable official Scoring Metrics test suite.

## Bug prevention register

| Failure | Prevention / targeted check |
|---|---|
| Zero hit count presented as API failure | Separate successful empty results from failed requests |
| Hit count shown as imported count | Store/display total, fetched, unique, excluded and cap separately |
| DOI missing on both → false exact duplicate | Never compare nulls as positive identity |
| Fuzzy transitivity merges incompatible papers | Component-level constraints and reviewer bridge approval |
| Conference and journal article collapsed | Same-study negative fixture, separate report identities |
| Truncated import looks complete | `partial` and `truncated` fields persisted and visible |
| English language metadata disagrees with abstract | Record discrepancy; abstain when uncertain |
| Adult/animal rule triggered by background sentence | Context/negation examples and conservative fallback |
| “Control” hallucinated as comparator | Exact quoted evidence and absent-label state |
| Emoji causes PICO highlight drift | Code-point/UTF-16 round-trip test |
| Repeated quote resolves to wrong location | Require exact span and text hash |
| Human edit lost after retraining | Separate result/event stores; projection regression |
| Prompt/model changes reuse stale result | Include versions in fingerprint |
| SQLite locked during model call | No network I/O inside write transaction; short transactions |
| Incorrect restore from current API | Reopen immutable snapshot, no fetch |
| React Strict Mode causes duplicate commands | Mutations only on explicit actions plus server idempotency |
| Old fetch response replaces new selection | Abort requests; scope cache by revision |
| CORS/auth works locally but fails remotely | Same-origin production path and deployment smoke |
| WebGL failure yields blank application | Scene error boundary/static fallback; semantic UI independent |
| Model outage hangs baseline | Timeouts, circuit/budget control, deterministic fallback |

These are planned preventions. No unimplemented bug is recorded as “fixed.”

## Evaluation protocol

**Dedup:** labeled duplicate and nonduplicate pairs, pair precision/recall/F1, false-merge examples and cluster consistency. Evaluate blocking recall separately from scoring. Show uncertain-review workload; high auto-merge precision matters more than making every fuzzy pair automatic.

**Screening:** confusion matrix, include recall, exclude precision, macro-F1/balanced accuracy, Maybe/abstention rate, reviewer overrides and review-time estimates. Handle class imbalance; ordinary accuracy alone is misleading. Report counts and confidence intervals only if actually calculated. Distinguish rule quality from ML prioritization quality; use ranking recall-at-k/work-saved only with a declared stopping rule and held-out labels.

**PICO:** exact span F1 and overlap/token F1 for each P/I/C/O, invalid offset rate, missing-label correctness, manual correction time. Evaluate C on independently labeled examples because EBM-NLP does not provide a separate C label. Avoid scoring only “nonempty output.”

**RAG/LLM:** evidence citation validity, answer support, abstention on unanswerable queries, retrieval recall@k on labeled evidence, prompt-injection behavior, cost/query and latency percentiles. Compare baseline versus single retrieval versus bounded agent loop. Human time savings must be measured with a specified task or explicitly labeled estimates with assumptions.

**System:** exact restoration success, decisions retained, crash recovery, export integrity, request/record failure rates. These are binary integrity gates before model quality improvements.

Freeze evaluation split, dataset/revision/hash, label provenance, random seed, method version and machine specification. Do not train on the held-out set, duplicates of it or organizer hidden-test labels. For the report, label figures as estimates as requested by the pre-read, list assumptions, and identify directly observed measurements separately in captions.

## Deployment topology

Default reproducible target: a single host with a persistent local disk. Build React to static assets; serve them and `/api` from the same origin (FastAPI static fallback carefully ordered after API routes, or a small reverse proxy). Run one API process and one Python worker, sharing a local `data/` volume with business DB, checkpoint DB and controlled source artifacts. Store secrets in environment/runtime secret storage. API `/health/live` and `/health/ready` should distinguish process status from database readiness; model-provider availability is not core readiness.

Use Docker Compose during implementation if the team has Docker, with pinned base images/digests verified before release; lockfiles drive installs. A development setup can run Vite, API and worker directly. CI should test Linux x86_64 in addition to the current development machine; Python wheel compatibility on one Mac does not prove the deployment build works.

The actual host/provider remains unchosen. A free-tier static frontend alone cannot run Python or persist SQLite. An ephemeral/serverless backend is not durable storage for reviewer work. Do not claim free persistent hosting is available without checking the chosen provider's current limits. If no suitable free persistent host exists, use the approved local demo arrangement and ask organizers about judge access; preserve a durable backup/export. Colab may support optional experiments but is not the always-on application database/server.

Release checklist: production secrets configured; auth mode appropriate for public access; persistent-volume restart verified; backup restored to a fresh directory; migration upgrade tested; no raw private/copyrighted dataset dump committed; query quotas configured; browser/API paths correct; dependency audit triaged; README tested by a teammate who did not write setup; judged URL/access confirmed.

## Five-minute demo script

| Time | Show | Narrative |
|---|---|---|
| 0:00–0:25 | Premium hero → review workspace | Research question and human control; brief 3D introduction |
| 0:25–1:10 | Saved queries + one small live API count/import | Boolean/date search, researcher selection, provenance and counts |
| 1:10–1:55 | Duplicate group and uncertain pair | Same paper vs same study; confirm/reject without deleting records |
| 1:55–2:40 | Eligibility evidence and override | Explain reason, change Maybe to Include, show audit event |
| 2:40–3:20 | PICO highlights and a corrected comparator | Exact spans, missing evidence and human correction |
| 3:20–4:15 | Query change/conflict/diff/revert if implemented | Prove preserved work and restoration. If bonus absent, show required loop design honestly |
| 4:15–4:45 | CSV export and run log | Reproducible included set and traceable decisions |
| 4:45–5:00 | Measured result/limitation slide | Simplest baseline, one justified improvement, next step |

Optional RAG explanation replaces part of the bonus section only if stable and measured; never sacrifice required controls to show a chatbot. Keep a prepared saved corpus for speed, label it, and still perform the live API step. Have offline fixtures for diagnosing an outage, clearly identified as fallback rather than passing them off as live.

## Final report, maximum three pages

Page 1: problem understanding, question/criteria, pipeline, simplest baseline and design choices. Page 2: data/source handling, methods and evidence, human decisions and loop semantics. Page 3: evaluation and cost/reviewer-time tradeoffs, security/deployment limits, what was kept/replaced/deferred and references. Required one-page loop design is a separate artifact; confirm submission packaging with organizers. Do not pre-fill report metrics with fabricated results.
