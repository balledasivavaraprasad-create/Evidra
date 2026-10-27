# <ID> — <deliverable>

Status: not started / in progress / ready for review / merged / deferred. Select the actual state; never infer it from a planned date.

## Identity and scope

- Developer and reviewer:
- Assigned prompt path:
- Requirement IDs and selected optional features:
- Branch and PR (only if they exist):
- Tested commit SHA:
- Merge SHA (captain fills after merge):
- Actual start/end, timezone:

## Prerequisite evidence

| Prompt | Actual merged SHA | Interface/examples inspected | Compatible with this commit? |
|---|---|---|---|
| Fill each hard prerequisite; D01 uses the bootstrap SHA | | | |

List additional conditional prerequisites if delivering Level 2, ML, LLM or RAG. A draft PR is not a merged prerequisite.

## Implemented behavior

Describe the observable result, affected paths and limits. Distinguish complete behavior from an explicit contract stub, fixture, dependency probe or nonexposed module. List any scope intentionally deferred.

## Interfaces for downstream owners

- Exported module/function signatures or HTTP method/path:
- Input/output example, errors and version/idempotency rules:
- Schema/OpenAPI/generated-type changes:
- Persistence/migration changes, head, upgrade and rollback/restore implications:
- Direct pins/lock changes and owner approval, or none:
- Next prompt IDs unblocked and the exact stable interface they can consume:

Use synthetic data only. Do not paste credentials, private notes, raw external datasets or unrestricted abstracts into the handoff.

## Verification evidence

| Check | Exact command | Environment/fixture | Exit/result | Evidence path or real CI run |
|---|---|---|---|---|
| Relevant unit/contract checks | | | | |
| Integration/browser/security checks in scope | | | | |
| Frozen install and active CI stage | | | | |

Record meaningful failure/regression cases. Separate local, GitHub-hosted, live-source, live-model, browser and deployed evidence. List anything not run and why. Do not report mock results as measured model quality or fixture imports as live API success.

## Cross-owner requests and release decision

| Request | Owning developer | Consuming prompt | Smallest upstream change/test | Blocking? |
|---|---|---|---|---|
| None if no requests remain | | | | |

- Implemented:
- Tested:
- Deployed:
- Known risks/limitations:
- Remaining organizer unknowns affecting this slice:
- Reviewer decision and reason:
- Captain audit update/checkpoint:
