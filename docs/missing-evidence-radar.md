# Missing-Evidence Radar: PICO Coverage & Review-Prioritization System

## 1. Overview and Problem Statement

In systematic literature reviews, automated AI models extract PICO elements (Population, Intervention, Comparator, Outcome) and propose screening decisions. However, a major reliability risk occurs when systems conflate:
1. An unpopulated field vs evidence that does not exist in the examined text.
2. Quoted text existing in an abstract vs text actually semantically supporting the claimed element.
3. Absence of an element in an abstract vs absence in the full paper.
4. Missing evidence vs paper exclusion.

**Missing-Evidence Radar** provides a rigorous, transparent PICO coverage and prioritization system that operates at both the **Article Level** (workbench inspection) and the **Review Level** (corpus-wide coverage matrix and triage queue).

---

## 2. Evidence Classification Hierarchy

Every PICO dimension (Population, Intervention, Comparator, Outcome) is deterministically classified into one of six mutually exclusive evidence states:

| Status | Code | Color / Indicator | Classification Criterion |
|---|---|---|---|
| **Supported** | `supported` | Green / Solid Check | Stored quote exists in source text, matches character offsets, and semantically supports the extracted claim. |
| **Uncertain** | `uncertain` | Amber / Warning | Ambiguous phrasing, low semantic extraction confidence, or manually flagged by a reviewer for ambiguity. |
| **Not Found** | `not_found` | Gray / Empty Circle | Source text was examined (e.g. abstract), but no supporting passage for this PICO dimension was located. Displayed explicitly as `"Not found in examined text (abstract)"`. |
| **Conflicting** | `conflicting` | Rose / Alert Triangle | Extracted claim or quote contradicts other reported sections or was manually flagged as conflicting evidence. |
| **Stale** | `stale` | Purple / Refresh | Source text fingerprint has updated since extraction, invalidating stored character code-point offsets. |
| **Not Assessed** | `not_assessed` | Muted Outline | Source text was empty, unexamined, or processing was skipped. |

---

## 3. Core Architectural Invariants

1. **Absence Does Not Mean Rejection:**
   Missing evidence for a PICO field (e.g., no active comparator in a single-arm trial) **never** automatically marks a paper as Excluded. Screening decisions remain completely decoupled from radar status.
2. **Quote Existence $\neq$ Semantic Support:**
   The verification engine checks both deterministic verbatim substring / offset matching and semantic alignment (`supports`, `contradicts`, `insufficient`). A matched string that contradicts the claim is classified as `conflicting`, not `supported`.
3. **Abstract vs. Full-Text Boundary:**
   When only an abstract is available, the system reports `"Not found in examined text (abstract)"`. It strictly refrains from stating or implying that the study itself did not test or report the element.
4. **Human Review Overrides with Full Audit Trail:**
   Reviewers can Confirm, Correct (with mandatory rationale), Flag Uncertain, or Flag Conflicting. Every action appends an immutable record in `review_events`, updates the Evidence Passport, and preserves original machine extractions without overwriting historical provenance.
5. **Zero N+1 Query Review Matrix:**
   The review-level dashboard loads all workspace records and active passports in optimized batch queries, ensuring sub-second response times even on large systematic reviews.

---

## 4. API Endpoints

Missing-Evidence Radar is exposed under the OpenAPI tag `Missing-Evidence Radar`:

- `GET /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar`:
  Returns article-level radar status for all 4 PICO dimensions, effective screening decision, stored quotes, offsets, validation messages, and human review status.
- `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/confirm`:
  Human confirmation of an extracted PICO field.
- `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/correct`:
  Submits reviewer correction with mandatory rationale, creating a new passport version and preserving original claims.
- `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/flag-uncertain`:
  Marks a field as uncertain with reviewer explanation, routing it to the triage queue.
- `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/flag-conflict`:
  Marks conflicting evidence between paper sections or reviewer assessments.
- `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/revalidate`:
  Re-runs quote matching and fingerprint checks against current source text.
- `GET /api/v1/workspaces/{workspace_id}/pico-radar`:
  Corpus-wide review matrix, dimension-by-dimension summary statistics, coverage percentage, and prioritized triage queue (Stale $\to$ Conflicting $\to$ Uncertain $\to$ Pending).

---

## 5. Frontend Components

- **`ArticleRadarWidget` (`frontend/src/features/pico-radar/ArticleRadarWidget.tsx`):**
  Embedded directly inside `ReviewQueuePage.tsx` under the "PICO Radar" sub-tab. Features a 4-field status grid, source quote preview, in-context abstract passage highlighting, and reviewer action buttons (Confirm, Correct, Flag Uncertain, Flag Conflict, Revalidate).
- **`ReviewRadarDashboard` (`frontend/src/features/pico-radar/ReviewRadarDashboard.tsx`):**
  Full review-level coverage dashboard accessible at `/reviews/:id/radar` and `/radar`. Includes:
  - Metric ribbon displaying assessed count, supported percentage, and review queue counts.
  - Dimension coverage cards for Population, Intervention, Comparator, and Outcome.
  - Full-text search and filtering by dimension, status, and review prioritization.
  - Interactive matrix table with direct inspection modal.

---

## 6. Database Migration

- **Migration:** `005_missing_evidence_radar.py`
- **Linear Alembic Head:** `005_missing_evidence_radar (head)`
- **Columns Added to `evidence_passports`:**
  - `radar_status`: `VARCHAR(32)`, default `'not_assessed'`, indexed.
  - `human_review_status`: `VARCHAR(32)`, default `'unreviewed'`, indexed.
  - `reviewer_notes`: `TEXT`, nullable.
