# Search Evolution Time Machine — Evidra

The **Search Evolution Time Machine** provides a systematic literature review (SLR) versioning and comparison engine. It tracks the longitudinal development of literature search strategies, retrieved citations, metadata revisions, and screening decisions across the lifetime of a systematic review.

---

## 1. Core Systematic Review Invariants

1. **Absence Without Deletion (`missing_from_newer`)**:
   - In systematic literature reviews, if an earlier search query returned a record, but a later modified query does not return it, the record must **never** be silently deleted or marked as excluded.
   - It is categorized as `missing_from_newer` (no longer returned by the updated search strategy).
   - Any prior human screening decisions (e.g. Include / Exclude / Maybe) on that paper are preserved intact in the systematic review corpus.

2. **Screening Decision Preservation Across Runs**:
   - As new search iterations are executed, human screening decisions made on earlier runs are carried forward automatically.
   - The system attributes the original screening decision and records the version where it was screened.

3. **Metadata Evolution & Re-verification Alerts**:
   - Published literature metadata can update between runs (e.g., preprints converting to peer-reviewed articles, title changes, corrected author lists, or errata).
   - The Search Evolution Time Machine performs deterministic field-level diffs (`title`, `abstract`, `authors`, `year`, `journal`, `doi`, `pmid`).
   - If a paper has already been screened and its metadata changes in a subsequent search run, the system flags `metadata_changed_since_screening = true` to alert reviewers that the paper's metadata has evolved since their initial judgment.

4. **Non-Destructive Rollback & Configuration Restore**:
   - Restoring an earlier search configuration does **not** erase, truncate, or overwrite any historical query versions, search executions, or imported records.
   - Restoring creates a brand new query version (e.g., $v_{new} = v_{max} + 1$) containing the exact restored Boolean AST and filter settings, marked with `restored_from_version_id` and audit rationale notes.

---

## 2. Six-Way Longitudinal Diff Categories

| Category | Description | Reviewer Action |
| :--- | :--- | :--- |
| `newly_discovered` | Present in target search version but not in baseline. | Needs initial human or AI screening. |
| `repeated` | Present in both baseline and target versions with identical metadata. | Retains preserved screening status. |
| `missing_from_newer` | Present in baseline version, but not returned by target query. | Retained in project; absence without deletion. |
| `metadata_changed` | Present in both versions, but field values or content hashes differ. | Reviewer inspects field-level diff before/after. |
| `conflict` | Records with unresolved merge, split, or decision divergence. | Requires conflict resolution in History panel. |

---

## 3. Architecture & Data Flow

```
[ QueryBuilder / AST Editor ]
            │
            ▼
   [ QueryVersionModel ] ──(restored_from_version_id, change_description)
            │
            ├─► [ SearchExecutionModel ] (Hit counts, Provider API stats)
            │           │
            │           ▼
            │   [ QueryMembershipModel ]
            │           │
            ▼           ▼
   [ SourceRecordModel ] ──► [ RecordRevisionModel ] (Immutable snapshots)
            │
            ▼
    [ PaperGroupModel ] ──► [ ReviewEventModel ] (Preserved human decisions)
            │
            ▼
 [ Search Evolution Service ]
   ├── list_search_versions()
   ├── compute_search_evolution_diff()
   └── restore_search_configuration()
```

---

## 4. REST API Specification

### List Search Versions
- **Endpoint**: `GET /api/v1/workspaces/{workspace_id}/search-versions`
- **Response**: `list[SearchEvolutionVersionSummary]`
- **Description**: Returns all search versions ordered by sequence descending, with counts for total records, new records, repeated records, screened count, unscreened count, and execution metrics.

### Get Search Version Detail
- **Endpoint**: `GET /api/v1/workspaces/{workspace_id}/search-versions/{version_id}`
- **Response**: `SearchEvolutionVersionSummary`

### Compare Search Versions (Diff)
- **Endpoint**: `GET /api/v1/workspaces/{workspace_id}/search-versions/{target_version_id}/diff?base_version_id={base_version_id}`
- **Response**: `SearchEvolutionDiffResponse`
- **Description**: Generates 6-way diff summary and record-level breakdowns with field-level before/after diffs and preserved screening decisions.

### Restore Search Configuration
- **Endpoint**: `POST /api/v1/workspaces/{workspace_id}/search-versions/{version_id}/restore`
- **Request Body**:
  ```json
  {
    "reason": "Reverting to broad sensitivity query after overly restrictive filter",
    "actor_id": "lead-reviewer"
  }
  ```
- **Response**: `SearchRestoreResponse` (HTTP 201 Created)

---

## 5. UI Features

1. **Version History Timeline**:
   - Visual sequence cards displaying search execution dates, target providers, total records, new papers (+N), and repeated papers (=N).
2. **Side-by-Side Version Diff Selector**:
   - Select baseline version and target version to inspect longitudinal evolution.
3. **Diff Metric Cards**:
   - Summaries for Newly Discovered, Previously Known, No Longer Returned, Metadata Changed, and Screening Progress.
4. **Interactive Category Filtering**:
   - Filter records by category (`All`, `Newly Discovered`, `Previously Known`, `No Longer Returned`, `Metadata Changed`, `Conflicts`).
5. **Field-Level Diff Inspector**:
   - Expandable side-by-side comparison highlighting changes in `title`, `abstract`, `authors`, `year`, `journal`, `doi`, or `pmid`.
6. **Non-Destructive Restore Modal**:
   - Confirmation dialog explaining the safety invariant and recording the restore rationale.
