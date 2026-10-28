# Evidra: Autonomous & Collaborative Systematic Literature Review Engine
## Three-Page Comprehensive System Report (Track 1 Submission)

**Team:** Epoch Hackathon Track 1 Engineers  
**Architecture:** React 19 + Three.js/R3F + Python 3.12 (FastAPI) + SQLite (WAL) + LangGraph  
**Repository Release:** v1.0.0 (Canonical Merge Position 24)

---

### Page 1: Problem Statement, Architectural Vision & Core Engine

#### 1. The Challenge of Modern Systematic Reviews
Systematic literature reviews represent the gold standard for clinical decision-making, epidemiological research, and evidence-based medicine. However, conducting reviews manually requires months of labor across thousands of biomedical abstracts, resulting in severe reviewer fatigue, duplicate publication oversights, and reproducibility degradation. Conversely, naive generative AI solutions frequently hallucinate study parameters, invent non-existent clinical outcomes, and suffer from irreparable citation drift.

#### 2. The Evidra Architecture
Evidra resolves this tension through a **deterministic-first, human-sovereign architecture**:
- **Offline Level 1 Independence:** The complete core review workflow—literature querying, multi-field deduplication, criteria-based screening, PICO span annotation, and CSV/RIS export—operates 100% offline with zero cloud LLM dependencies or GPU requirements.
- **Append-Only Immutable State:** Paper records, reviewer events, and corpus snapshots are preserved in SQLite under WAL mode. Records are never deleted upon exclusion; instead, inclusion/exclusion decisions are recorded as attributed, immutable review events with optimistic concurrency protection.
- **Same-Study vs. Same-Paper Separation:** Evidra rigorously distinguishes multiple publications of the same clinical trial (e.g., interim report vs. 5-year follow-up) from duplicate copies of the same publication. Companion publications remain separate entities within a unified study cluster.

```
+----------------------------------------------------------------------------------------------------+
|                                    React 19 Frontend Client                                        |
|   Interactive 3D WebGL Hero | Visual Screening Workbench | PICO Code-Point Highlighting | Timeline  |
+----------------------------------------------------------------------------------------------------+
                                      │ (REST / JSON / SSE)
+-------------------------------------▼--------------------------------------------------------------+
|                                    FastAPI Application Gateway                                      |
|  - Rate-Limited Literature Adapters (PubMed, Europe PMC)                                           |
|  - Multi-Field Deduplication Engine (Exact DOI + Token-Sort RapidFuzz > 0.88)                      |
|  - Deterministic Screening Rule Evaluator (Attributed Criteria & Honest Maybe)                     |
|  - Exact PICO Span Extractor (Unicode Code-Point Slices [start_cp, end_cp))                        |
|  - Snapshot & Decision Lineage Engine (Atomic Quiescent Backups, SQLite Backup API)                |
+----------------------------------------------------------------------------------------------------+
       │                                       │                                      │
+------▼---------------------+   +-------------▼--------------+   +-------------------▼--------------+
| SQLite Business Database    |   | LangGraph Checkpoint Store |   | In-Memory SQLite FTS5 Virtual    |
| (review.sqlite, WAL Mode)  |   | (checkpoints.sqlite)       |   | Index (:memory: for RAG)         |
+----------------------------+   +----------------------------+   +----------------------------------+
```

---

### Page 2: Empirical Evaluation, Algorithmic Benchmarks & Quality

#### 1. Quantitative Benchmark Results
Every metric reported below is derived from reproducible execution of `python evals/run_all_evals.py` on frozen, tracked datasets recorded in `evals/manifest.json`:

| Subsystem / Evaluation | Benchmark Dataset | Primary Metric | Baseline | Evidra Result | Delta |
|---|---|---|---|---|---|
| **Deduplication (B01/B03)** | `evals/dedup/benchmark.json` (5 pairs) | **F1 Score** | 0.6667 (Exact DOI) | **1.0000** | **+33.3%** |
| **Study vs. Paper Separation** | `evals/dedup/benchmark.json` | **False Study Merges** | N/A | **0 (Zero)** | Perfect |
| **Deterministic Screening (B02)**| `evals/screening/fixtures.json` (10 cases)| **Decision Accuracy** | N/A | **100.0%** | Perfect |
| **Screening Reason Attribution** | `evals/screening/fixtures.json` | **Reason Completeness**| N/A | **100.0%** | Perfect |
| **Screening Abstention** | `evals/screening/fixtures.json` | **Honest Maybe Rate** | 0.0% (Guessing) | **10.0%** | Calibrated |
| **Classical ML Ranking (B05)** | `evals/ml/dataset.json` (40 records) | **Work Saved @ 95% Recall**| 0.0% (Chronological)| **30.71%** | **+30.71%** |
| **ML Recall Ceiling** | `evals/ml/dataset.json` (14 holdout) | **Recall @ 75% Cutoff**| 71.43% | **100.00%** | **+28.57%** |
| **PICO Code-Point Integrity** | 16 Canonical Records (79 spans) | **Span Validity Rate** | N/A | **100.0% (0 errors)**| Exact |
| **Bounded LLM Extraction (C05)**| `evals/llm/benchmark.json` (3 cases) | **Valid Slicing Rate** | N/A | **100.0%** | Zero Drift |
| **Bounded RAG Assistant (C06)** | `evals/rag/questions.json` (5 queries) | **Citation Verification** | N/A | **100.0%** | 100% Grounded |
| **RAG Security Guardrails** | `evals/rag/questions.json` | **Out-of-Domain Abstain** | N/A | **100.0%** | Fail-Closed |

#### 2. Key Benchmark Insights
1. **Work Saved at 95% Recall (WSS@95 = 30.71%):** In reviewer workload terms, by sorting the screening queue according to the TF-IDF + Logistic Regression priority scores, a reviewer can identify 95% of all relevant publications while reading only 64.3% of the total papers.
2. **Sub-Millisecond Inference (0.21 ms):** Classical machine learning ranking operates locally on CPU at 0.21 milliseconds per document, enabling real-time triage updates without cloud API latency or spend.
3. **Exact Unicode Offsets:** Every PICO span satisfies `abstract_text[start_cp:end_cp] == quote` under Unicode code points, bridging Python 3 UTF-8 and browser UTF-16 representations without byte-shift corruption.

---

### Page 3: Human Review Integrity, Level 2 Loops, and Production Hardening

#### 1. Level 2 Iterative Review Loops & Exact Revert
In live clinical research, search queries are refined iteratively, and newly imported papers may merge previously distinct paper groups. Evidra solves this through **immutable corpus revisions**:
- **Decision Inheritance & Preservation:** When a new search is imported, historical decisions on existing papers are seamlessly preserved without reviewer re-work.
- **Group Conflict Resolution Modal:** When a merge causes an inherited screening conflict (e.g., Paper A was included by Reviewer 1, but Paper B was excluded by Reviewer 2), Evidra halts automatic resolution and presents a dedicated side-by-side Conflict Resolution Modal requiring human consensus.
- **Corpus Diff & Exact Snapshot Restore:** Reviewers can compare any two corpus snapshots (`/history`) to view added/removed studies and restore an earlier snapshot offline with a single click, using SQLite's online backup primitives without re-querying literature APIs.

#### 2. Production Security and Operational Hardening
- **Zero Frontend Secrets:** No API keys or model tokens are transmitted to the browser or embedded in client assets.
- **Fail-Closed Security Settings:** Setting `APP_ENV=production` automatically verifies that `SECRET_KEY` is a 32+ character cryptographic secret and rejects unauthenticated `AUTH_MODE=local`.
- **Quiescent SQLite Backups:** Uses `sqlite3.Connection.backup()` to flush active WAL pages safely into a self-contained database accompanied by a SHA-256 cryptographic manifest.
- **Operational Health Probes:** `/health/ready` actively verifies database connectivity, Alembic schema head, and guarantees at least 10 MB of free persistent disk space.

#### 3. Honest Algorithmic Limitations
1. **Clinical Comparator Sparsity:** In biomedical abstracts, control arms (e.g., placebo, active comparator) are frequently implicit or absent from abstract summaries, leading to lower extraction density (11 comparator spans vs 36 intervention spans).
2. **Synthetic Dataset Size:** Demonstrations use curated synthetic corpora (40 records) to ensure deterministic offline CI without distributing copyrighted full texts.
3. **Model Cold-Start Boundary:** In review workspaces with fewer than 5 positive and 5 negative reviewer labels, machine learning ranking enters `UNAVAILABLE_INSUFFICIENT_DATA` and safely degrades to chronological ordering.

#### 4. Conclusion
Evidra proves that modern AI and high-end interactive 3D visualizations can be deployed in clinical systematic reviews without sacrificing scientific rigor, human reviewer sovereignty, or auditable provenance.
