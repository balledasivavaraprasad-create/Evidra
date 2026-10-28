# Evidra: Five-Minute Live Demonstration Script

**Target Time:** Exactly 5 minutes (300 seconds)  
**Presenter:** dev-A (T1: Frontend / Full-Stack Owner)  
**URL:** `http://localhost:5173` (or container `http://localhost:8000`)  
**Prerequisites:** Backend running on port 8000 (or 8800), Frontend running on port 5173 (or 5180).

---

## Timing Breakdown

### Segment 1: The Premium 3D Hero & Architectural Vision (0:00 – 0:45)
- **Visual:** Navigate to `/` (Landing page).
- **Actions:**
  - Move the cursor across the canvas to demonstrate the interactive 3D WebGL hero scene (Three.js + React Three Fiber).
  - Highlight the light/dark theme toggle and luxury frosted-glass aesthetic.
  - Explain the core thesis: *"Evidra eliminates the chaos of systematic reviews by combining a 100% deterministic Level 1 review engine with Level 2 snapshot-preserved review loops."*
- **Talking Points:**
  - *"Notice that Level 1 requires zero cloud LLM keys or GPU clusters—it operates entirely offline and deterministically on local SQLite with WAL mode."*
  - Click **"Launch Review Workbench"** to navigate into workspace `ws-synth-001`.

---

### Segment 2: Literature Search & Approved Record Ingestion (0:45 – 1:30)
- **Visual:** Navigate to Search & Ingestion view (`/search`).
- **Actions:**
  - Show the structured Boolean query builder with MeSH terms (`"metformin" AND "type 2 diabetes"`).
  - Click **"Execute Count Query"** against PubMed / Europe PMC adapters. Show the live hit count acquisition and translation.
  - Demonstrate the quota-protected import job approval: *"Reviewers explicitly approve search imports; background ingestion runs durably with optimistic concurrency."*
  - Show the imported record cards populated in the workspace.

---

### Segment 3: Intelligent Deduplication & Same-Study Separation (1:30 – 2:30)
- **Visual:** Navigate to Review Workbench (`/workbench`).
- **Actions:**
  - Point to the paper groups list. Show that duplicate records with matching DOIs and normalized title tokens are clustered into single PaperGroups.
  - **The Critical Distinction:** Show two papers from the same clinical trial (e.g. *Step 1 Trial Interim Report* vs. *Step 1 Trial 5-Year Extension*):
    - *"Notice that Evidra keeps these two papers separate because they report distinct findings from the same study. Evidra never deletes a paper simply because it belongs to the same clinical trial."*
  - Demonstrate a **Manual Dedup Override**: Confirm a proposed duplicate pair or establish a `cannot-link` constraint with recorded reviewer attribution.

---

### Segment 4: Explainable Screening & PICO Span Offsets (2:30 – 3:30)
- **Visual:** Click on paper group `grp-001` in the Screening Workbench.
- **Actions:**
  - **Screening Evidence:** Show the deterministic rule evaluation panel. Point to the attributed criteria rules: *"Evidra explains exactly why a paper is excluded (e.g. Preclinical animal model), citing the verbatim text snippet."*
  - **Honest Maybe State:** Point to a study with missing outcome information: *"When data is incomplete, Evidra outputs an honest Maybe rather than hallucinating an exclusion."*
  - **Exact PICO Span Offsets:** Click the **"Abstract & PICO"** tab. Show the interactive color-coded highlights for Population (blue), Intervention (emerald), Comparator (purple), and Outcome (amber).
  - Click on a PICO span to inspect the exact Unicode code-point offset `[start_cp, end_cp)` and show that `abstract_text[start:end] == quote`.
  - Record an inclusion screening decision: Click **"Include Study"**. Show the instant status transition and optimistic concurrency version increment.

---

### Segment 5: Level 2 Snapshot Revert, Corpus Diff & Export (3:30 – 4:30)
- **Visual:** Navigate to History & Diff view (`/history`).
- **Actions:**
  - Point to the historical timeline of published corpus revisions.
  - Select **Revision 2** and compare against **Revision 1** to view the **Corpus Diff**:
    - Highlight added papers (green badge), removed papers (red badge), and modified review decisions.
  - **Group Conflict Resolution:** Show the conflict resolution modal where conflicting reviewer decisions on merged groups are presented side-by-side for human resolution.
  - **Exact Snapshot Restore:** Click **"Restore Snapshot"**. Demonstrate instant, one-click restoration of historical corpus state directly from SQLite without re-fetching external APIs.
  - Navigate to Export: Generate sanitized CSV and RIS files with full provenance hash tracking.

---

### Segment 6: Benchmark Metrics & Outage Fallback Summary (4:30 – 5:00)
- **Visual:** Switch to terminal or `docs/report-evaluation.md`.
- **Actions:**
  - Present the empirical metrics:
    - **100% Deduplication F1 Score** with 0 false study merges.
    - **30.71% Work Saved at 95% Recall (WSS@95)** using classical ML ranking at 0.21 ms latency.
    - **100% PICO code-point validity** across 79 spans with 0 errors.
  - **Outage Fallback Protocol:**
    - *"If live PubMed APIs or network connections fail during judging, Evidra's `SOURCE_MODE=fixture` and offline SQLite snapshot architecture guarantee that 100% of the review workflow functions with zero downtime."*
  - Conclude: *"Evidra proves clinical reviews can be fast, beautiful, and completely auditable."*
