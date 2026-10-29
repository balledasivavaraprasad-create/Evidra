# PRISMA 2020 Flow Diagram and Automated Reporting

## 1. Overview and Architecture

The **PRISMA 2020 Flow Diagram and Automated Reporting** feature in Evidra provides automated, auditable, and mathematically reconciled reporting for systematic literature reviews, following the official **PRISMA 2020 Statement** (*Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ 2021;372:n71*).

In systematic literature reviews, reporting how studies entered, progressed through, or were excluded from the review is mandatory for publication. Prior tools often rely on static drawings or manually calculated numbers prone to human transcription errors. Evidra solves this by deriving all PRISMA flow numbers directly from persisted database entities: bibliographic search executions, source records, deduplication clusters, and audited screening events.

---

## 2. Core Methodological Invariants

1. **Direct Data Derivation**: Every count in the PRISMA diagram is computed directly from persisted records in the database (`source_records`, `paper_groups`, `group_members`, `review_events`, and `review_conflicts`). No mock or fabricated metrics are used.
2. **Mathematical Balance**: Flow numbers must satisfy conservation equations at each stage:
   - *Identification Balance*: $\text{Total Identified} = \text{Duplicates Removed} + \text{Other Removed} + \text{Eligible for Screening}$
   - *Screening Balance*: $\text{Eligible for Screening} = \text{Screened} + \text{Pending} + \text{Maybe} + \text{Active Conflicts}$
3. **Study vs. Report Separation**: Distinguishes unique canonical clinical trials/studies (`studies_included`) from the total bibliographic publication reports/citations (`reports_included`) that describe those studies across multiple databases.
4. **Truthful Stage Disclosure**: Evidra currently evaluates literature deterministically at the title and abstract level with character-level PICO offsets. The full-text retrieval and eligibility stages are truthfully reported as `not_started` (`is_supported=False`) rather than fabricating zero counts or pretending full-text screening occurred.
5. **Formula Injection Sanitization**: All CSV export fields (titles, exclusion reasons, author names, review notes) are sanitized against CSV formula injection (`=`, `+`, `-`, `@`, `\t`, `\r`) by prepending a safe apostrophe (`'`).
6. **Immutable Snapshots**: Reviewers can capture and preserve immutable PRISMA snapshots with milestone notes and reviewer attribution for manuscript submissions or protocol compliance auditing.

---

## 3. Data Model and Database Schema

### 3.1 Migration: `008_prisma_reporting`

Introduces the persistent `prisma_snapshots` table:

```sql
CREATE TABLE prisma_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    corpus_revision_id VARCHAR(64) REFERENCES corpus_revisions(id) ON DELETE SET NULL,
    query_version_id VARCHAR(64) REFERENCES query_versions(id) ON DELETE SET NULL,
    name VARCHAR(256) NOT NULL,
    notes TEXT,
    schema_version VARCHAR(32) NOT NULL DEFAULT '2020.1',
    counts_json TEXT NOT NULL,
    exclusion_reasons_json TEXT NOT NULL,
    validation_issues_json TEXT NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);
CREATE INDEX ix_prisma_snapshots_workspace ON prisma_snapshots (workspace_id);
```

### 3.2 SQLAlchemy Model: `PrismaSnapshotModel`

Located in `backend/app/db/models.py`, mapping foreign key cascade deletion to `WorkspaceModel.prisma_snapshots`.

---

## 4. PRISMA Flow Stages & Calculation Logic

| PRISMA Stage | Evidra Source Entity | Metric / Description |
|---|---|---|
| **Identification** | `source_records` & `search_executions` | Total raw records identified across databases (e.g. PubMed, Europe PMC). Retains per-database record breakdowns. |
| **Pre-Screening** | `paper_groups` & `group_members` | Deduplication pass removing duplicates ($\text{Raw Records} - \text{Unique Study Groups}$). Net unique study groups entering screening. |
| **Screening** | `review_events` (`screen_decision`) | Title and abstract screening decisions: included vs excluded. Aggregates frequency and percentage for every distinct exclusion reason. Also tracks tentative in-flight records (`pending`, `maybe`, `conflicts`). |
| **Retrieval** | Explicit protocol disclosure | Truthfully disclosed as `not_started` with transparent explanatory notes. |
| **Eligibility** | Explicit protocol disclosure | Full-text eligibility stage marked `not_started`. |
| **Included** | `paper_groups` with effective `include` | Unique canonical studies included vs total individual publication reports included. |

---

## 5. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/workspaces/{workspace_id}/prisma` | Compute live PRISMA 2020 flow report with audited counts, exclusion breakdown, and mathematical balance validation. |
| `GET` | `/api/v1/workspaces/{workspace_id}/prisma/records` | Drill down into records contributing to any stage/box (`identification`, `pre_screening`, `screening`, `included`). Supports search and pagination. |
| `GET` | `/api/v1/workspaces/{workspace_id}/prisma/export/csv` | Download sanitized CSV report containing metrics, exclusion reasons frequency, and validation warnings. |
| `POST` | `/api/v1/workspaces/{workspace_id}/prisma/snapshots` | Create an immutable audit snapshot for manuscript submission or protocol milestones. |
| `GET` | `/api/v1/workspaces/{workspace_id}/prisma/snapshots` | List historical report snapshots for a review workspace. |
| `GET` | `/api/v1/workspaces/{workspace_id}/prisma/snapshots/{snapshot_id}` | Retrieve a saved historical PRISMA snapshot. |

---

## 6. Frontend Components

- **`PrismaFlowPage`** (`frontend/src/features/prisma/PrismaFlowPage.tsx`): Main dashboard featuring KPI summary strips, reconciliation status banner, exclusion reasons breakdown, and database source distribution.
- **`PrismaDiagram`** (`frontend/src/features/prisma/PrismaDiagram.tsx`): Interactive, publication-faithful SVG rendering of the PRISMA 2020 flow diagram with clickable nodes, directional arrows, and stage banners.
- **`PrismaStageRecordsModal`** (`frontend/src/features/prisma/PrismaStageRecordsModal.tsx`): Record-level drill-down modal displaying studies contributing to any clicked node with title, authors, DOI/PMID links, and exclusion reasons.
- **`PrismaSnapshotModal`** (`frontend/src/features/prisma/PrismaSnapshotModal.tsx`): Snapshot creation modal capturing milestone name, notes, and reviewer ID.
- **`PrismaHistoryDrawer`** (`frontend/src/features/prisma/PrismaHistoryDrawer.tsx`): Slide-out drawer to browse and switch between live data and saved historical snapshots.
