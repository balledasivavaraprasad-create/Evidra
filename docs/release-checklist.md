# Evidra Release & Verification Checklist (v1.0.0)

**Release Date:** October 2026  
**Release Tag:** `v1.0.0`  
**Integration Lead:** dev-A (T1) in coordination with dev-B (T2), dev-C (T3), and dev-D (T4)  
**Release Position:** Canonical Merge Position 24 of 24 (Complete System Release)

---

## 1. Feature Delivery Ledger (All 24 Prompts Delivered)

| Prompt ID | Domain Owner | Implemented Capability | Verified Merge SHA | Status |
|---|---|---|---|---|
| **D01** | dev-D | Database foundation, SQLite WAL, initial migrations, Alembic, OpenAPI contracts | `2f643e2` | **VERIFIED** |
| **A01** | dev-A | React 19 application shell, layout, API client, design system tokens | `1aa63b1` | **VERIFIED** |
| **B01** | dev-B | Deterministic deduplication, exact/fuzzy DOI & title matching, cannot-link graph | `76d9cbb` | **VERIFIED** |
| **C01** | dev-C | Deterministic PICO span extractor with exact Unicode code-point offsets `[start, end)` | `28e67a0` | **VERIFIED** |
| **D02** | dev-D | Source adapters for PubMed E-Utilities and Europe PMC with rate limiting | `a32b904` | **VERIFIED** |
| **B02** | dev-B | Deterministic screening rule engine, attributed inclusion/exclusion, honest Maybe | `977da96` | **VERIFIED** |
| **C02** | dev-C | Resumable LangGraph workflow, SQLite checkpointer, human interrupt node | `0ef04df` | **VERIFIED** |
| **A02** | dev-A | Search query builder UI, MeSH terms, count preview, approved record ingestion | `4f41ddf` | **VERIFIED** |
| **D03** | dev-D | Domain endpoints: paper groups, review events, optimistic concurrency, CSV/RIS export | `6ae229b` | **VERIFIED** |
| **B03** | dev-B | Deduplication & screening evaluation harness (`evals/manifest.json`), confusion matrix | `87f6516` | **VERIFIED** |
| **C03** | dev-C | Agent security guardrails, prompt injection detection, token budget caps | `141b777` | **VERIFIED** |
| **A03** | dev-A | Screening workbench UI, PICO offset highlighter, optimistic concurrency handling | `e88ffad` | **VERIFIED** |
| **D04** | dev-D | End-to-end integration test harness, Playwright Level 1 spec, fixture mode | `82ec4f1` | **VERIFIED** |
| **A04** | dev-A | Premium 3D WebGL scene, Three.js / React Three Fiber, luxury frosted glass design | `a3d03fd` | **VERIFIED** |
| **D05** | dev-D | Immutable corpus snapshots, decision lineage, group conflicts, exact restore | `ef5ff75` | **VERIFIED** |
| **B04** | dev-B | Group merge/split and cross-version regression suite | `14795d4` | **VERIFIED** |
| **C04** | dev-C | Incremental graph execution and snapshot-aware replay | `8c7c93b` | **VERIFIED** |
| **A05** | dev-A | Version history, conflicts, diff and restore UI | `290099d` | **VERIFIED** |
| **B05** | dev-B | Optional classical ML ranking (TF-IDF + LogisticRegression, WSS@95 = 30.71%) | `e8e44a4` | **VERIFIED** |
| **C05** | dev-C | Optional budgeted LLM gateway, exact span slicing, quote repair | `152d750` | **VERIFIED** |
| **C06** | dev-C | Optional bounded, cited corpus SQLite FTS5 RAG assistant | `d08b87c` | **VERIFIED** |
| **D06** | dev-D | Operational hardening, SQLite WAL-safe backup, readiness probes, CI promotion | `93ab93a` | **VERIFIED** |
| **B06** | dev-B | Final reproducible algorithm evaluation evidence (`evals/run_all_evals.py`) | `99f3ad2` | **VERIFIED** |
| **A06** | dev-A | Deployment packaging, Docker single-host setup, demo script, release handoff | `[CURRENT]` | **VERIFIED** |

---

## 2. Release Gate Verification Summary

- [x] **Backend Test Suite:** 167 tests passed (0 failures, 0 errors, duration: 3.60s).
- [x] **Frontend Test Suite:** 21 unit tests passed (0 failures, duration: 373ms).
- [x] **TypeScript Typecheck:** 0 type errors (`tsc --noEmit`).
- [x] **OpenAPI Contract Drift Check:** 0 drift (`npm run api:check` and `export_openapi.py --check` both pass).
- [x] **Frontend Production Build:** Successful minified client bundle with code-splitting.
- [x] **CI Stage Promotions:** `.ci/stages.json` promoted with `level2: true` and `ai: true`.
- [x] **Linear Database Migration:** Exactly one Alembic head (`002_review_services_schema`).
- [x] **Zero Secrets in Client:** No API keys, model passwords, or session tokens exposed to the browser.
- [x] **Offline Level 1 Independence:** Baseline operates completely offline without live LLM or external provider keys.
- [x] **Quiescent Backup Verification:** SQLite backup API tested with active WAL pages and verified against SHA-256 manifest.
- [x] **Health & Readiness Probe:** `/health/ready` verified under active database, migration, and disk space conditions.

---

## 3. Deployment Artifacts Generated

1. `infra/Dockerfile`: Verified multi-stage build (Node 24 + Python 3.12-slim).
2. `infra/docker-compose.yml`: Single-host deployment with persistent volume mount on `/app/data`.
3. `infra/entrypoint.sh`: Automated migration execution and uvicorn startup.
4. `infra/nginx.conf`: Production reverse proxy configuration.
5. `evals/manifest.json`: Cryptographic benchmark audit manifest (v2.0.0).
6. `docs/operations.md`: Reliability and operations runbook.
7. `docs/report.md`: Three-page comprehensive system report.
8. `docs/demo-script.md`: Timed five-minute demonstration script.
