# Duplicate Genealogy & Decision Reconciliation System

## 1. Overview and Architecture

The **Duplicate Genealogy & Decision Reconciliation** system in Evidra provides an auditable, transparent, and reversible mechanism for managing multi-source duplicate publications across systematic literature reviews.

When systematic reviews ingest papers from heterogeneous bibliographical providers (PubMed, Europe PMC, CrossRef), duplicates commonly arise. However, automated deduplication passes or uncoordinated multi-reviewer workflows can introduce:
1. **Decision Divergence**: One duplicate copy is included while another is excluded.
2. **Provenance Obscurity**: Reviewers cannot inspect which source record provided canonical metadata (e.g., PubMed vs Europe PMC title/abstract variations).
3. **Irreversible or Opaque Merges**: Automated passes merge papers without leaving a reversible audit trail.

Evidra solves this through a dedicated persistence layer, matching evidence engine, conflict detection service, and interactive UI.

---

## 2. Core Domain Invariants

1. **No Silent Overrides**: Automated merge passes never overwrite existing human decisions. Conflicting screening decisions between merged copies are surfaced as explicit, blocking review conflicts.
2. **Multi-Source Lineage**: Every merged paper group retains references to all its individual source records, including their provider-specific external IDs (PMID, PMC ID, DOI), original metadata, and individual screening history.
3. **Deterministic Match Signals**: Pairwise edges persist exact match tokens (e.g. `exact_doi`, `exact_pmid`, `title_similarity`, `author_token_overlap`) instead of ungrounded probabilistic scores.
4. **Permanent Cannot-Link Protection**: When a reviewer splits records from a merged group, an explicit `cannot-link` constraint is recorded in `dedup_edges`, permanently preventing future automated deduplication passes from re-merging them without human override.
5. **Audited Reversibility**: All merge, split, and reconciliation actions append an immutable `DuplicateMergeEventModel` entry with full pre-operation state, allowing safe reversals.

---

## 3. Data Models and Schema

### 3.1 Migration: `007_duplicate_genealogy`

The migration introduces the `duplicate_merge_events` table:

```sql
CREATE TABLE duplicate_merge_events (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    group_id VARCHAR(64) NOT NULL REFERENCES paper_groups(id) ON DELETE CASCADE,
    canonical_record_id VARCHAR(64) REFERENCES source_records(id),
    operation VARCHAR(32) NOT NULL,
    affected_source_ids_json TEXT NOT NULL,
    match_evidence_json TEXT NOT NULL,
    field_provenance_json TEXT,
    pre_operation_state_json TEXT,
    actor_id VARCHAR(128) NOT NULL,
    reason TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    reversal_event_id VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);
```

### 3.2 Supported Operations (`DuplicateMergeOperation`)

- `initial`: Initial automated deduplication pass linking records.
- `merge`: Manual or automated merge adding records to an existing group.
- `split`: Reviewer separation of false-positive duplicates into an independent group.
- `reversal`: Reversal of a previous merge event.
- `reconciliation`: Authoritative human resolution of competing decisions.

---

## 4. Conflict Classification

The system classifies conflicts into five categories:

| Classification | Meaning | Resolution Mechanism |
|---|---|---|
| `decision_divergence` | Two duplicate records have contradictory screening decisions (`include` vs `exclude`). | Authoritative human reconciliation via modal |
| `rationale_divergence` | Decisions agree (e.g. both `exclude`) but scientific rationales differ significantly. | Rationale consolidation |
| `automated_vs_human` | Automated screening model suggested one status while human reviewer chose another. | Human decision strictly supersedes machine suggestion |
| `missing_decision` | One copy was screened but companion copy arrived unscreened. | Inherit existing screening decision with provenance note |
| `stale_merge` | Merged records have diverged since initial deduplication. | Re-evaluation and split review |

---

## 5. REST API Specification

### 5.1 `GET /api/v1/workspaces/{workspace_id}/duplicates`
Returns workspace overview of duplicate groups, active conflicts, and member record counts.
- **Query Parameters**:
  - `conflict_only` (bool, optional): Filter groups with unresolved conflicts.
  - `limit` (int, default 50)
  - `offset` (int, default 0)

### 5.2 `GET /api/v1/workspaces/{workspace_id}/groups/{group_id}/genealogy`
Returns full duplicate genealogy tree:
- Canonical representative record.
- All member records with provider-level metadata.
- Pairwise matching signals and similarity scores.
- Field-level metadata provenance comparison.
- Merge and split historical audit trail.

### 5.3 `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/reconcile`
Authoritatively resolves conflicting screening decisions.
- **Request Body**:
  - `chosen_decision`: `"include"` | `"exclude"` | `"maybe"`
  - `reason`: Mandatory scientific justification
  - `actor_id`: Reviewer identifier
  - `apply_to_all_members`: boolean
  - `expected_version`: Optimistic concurrency version check

### 5.4 `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/split`
Separates specified records into an independent group.
- **Request Body**:
  - `source_record_ids_to_split`: `string[]`
  - `reason`: Rationale for distinction
  - `mark_as_cannot_link`: Enforce permanent rejection edge
  - `actor_id`: Reviewer identifier
  - `expected_version`: Optimistic concurrency version check

### 5.5 `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/reverse-merge`
Safely reverses a specific merge event, re-establishing pre-merge group state.

---

## 6. Frontend Components

- **`DuplicatesPage.tsx`**: Multi-tab management dashboard:
  - *Genealogy & Merged Groups*: Searchable directory of duplicate groups with conflict badges and inline selection.
  - *Decision Conflicts Ledger*: Dedicated conflict resolution queue.
  - *Pairwise Candidate Review*: Side-by-side comparison with match confidence tokens.
- **`DuplicateGenealogyView.tsx`**:
  - Member cards indicating canonical representative.
  - Pairwise similarity evidence breakdown.
  - Interactive field-level metadata comparison table highlighting discrepancies.
  - Reconcile and split modal dialogues with optimistic concurrency protection.
  - Audit trail displaying all past merge operations with safe reversal actions.
