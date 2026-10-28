# Evidence Passport for Evidra

## 1. Overview & Core Principle

**Evidence Passport** is an evidence-transparency and explainability system for AI-assisted literature screening and PICO extraction in Evidra.

In systematic reviews, AI-generated outputs (such as inclusion/exclusion rationales or PICO entities) cannot be blindly accepted. Reviewers must be able to trace every claim to its exact source sentence in the stored study text, confirm structural validity, inspect whether the passage logically supports the claim, and record human corrections without erasing the original audit trail.

### Core Invariants:
1. **Structural Verification vs. Semantic Support:**
   - An exact quotation match proves that the passage exists in the source text and that offsets match.
   - It **does not** automatically prove that the passage logically supports the claim (e.g. quoting *"No statistically significant difference was observed"* accurately does not prove an intervention was superior).
   - Structural quotation validation and semantic support assessment (`supports`, `contradicts`, `insufficient`, `unassessed`) are maintained as separate fields. Semantic support is never falsely marked as verified without explicit evaluation.
2. **Deterministic Offset Anchoring:**
   - Offsets are computed using half-open Unicode code points `[start_cp, end_cp)`.
   - When models omit offsets or provide slight shifts, backend code resolves single unambiguous occurrences automatically.
   - Ambiguous multi-match quotations are flagged as `needs_review` rather than guessing an arbitrary offset.
3. **Audit Trail & Decision Preservation:**
   - When a reviewer edits or corrects a claim, `original_claim_value` retains the initial AI output.
   - Reviewer edits are recorded in append-only `ReviewEventModel` records (`event_type: evidence_correction`).
   - Rerunning automated extraction never overwrites human-corrected claims.
4. **CSV Formula Injection Sanitization:**
   - All exported Evidence Passport CSV cells starting with dangerous formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped.

---

## 2. Architecture & Data Model

### Database Table: `evidence_passports`
Defined in [`backend/app/db/models.py`](file:///c:/Hackathon/epoch/Evidra/backend/app/db/models.py) and migrated via Alembic revision `003_evidence_passport`:

| Column | Type | Description |
|---|---|---|
| `id` | String(64) PK | UUID identifier |
| `workspace_id` | String(64) FK | Workspace scoping for multi-tenant isolation |
| `paper_group_id` | String(64) FK | Associated deduplicated paper group |
| `record_revision_id`| String(64) FK | Immutable source record revision |
| `claim_type` | String(32) | `screening_rationale`, `population`, `intervention`, `comparator`, `outcome`, `study_characteristic` |
| `claim_value` | Text | Active clinical claim or entity value |
| `original_claim_value`| Text | Initial AI-proposed claim before human edits |
| `source_field` | String(32) | `abstract`, `title`, or `full_text` |
| `supporting_quote` | Text | Exact quoted passage from source |
| `start_cp` / `end_cp` | Integer | Half-open Unicode code-point offsets `[start, end)` |
| `source_fingerprint` | String(64) | SHA-256 fingerprint of stored source text at generation time |
| `provenance` | String(64) | `model_generated`, `deterministic_extraction`, `imported_annotation`, `human_created`, `human_corrected` |
| `validation_status` | String(32) | `verified`, `stale`, `mismatched`, `missing_source`, `insufficient_evidence`, `needs_review` |
| `validation_message`| Text | Granular explanation of checks performed |
| `semantic_assessment`| String(32) | `supports`, `contradicts`, `insufficient`, `unassessed` |
| `assessed_by` | String(128) | Actor identity (`human:reviewer_1`, `system:rule`, etc.) |
| `is_contradictory` | Boolean | Flag indicating passage contradicts claim |
| `reviewer_correction_reason` | Text | Reviewer justification rationale |
| `event_id` | String(64) FK | Link to append-only audit event in `review_events` |

---

## 3. Endpoints & API

All endpoints are registered in [`backend/app/main.py`](file:///c:/Hackathon/epoch/Evidra/backend/app/main.py) with full OpenAPI schema contracts:

1. `GET /api/v1/workspaces/{workspace_id}/groups/{group_id}/evidence`  
   Retrieves complete `EvidencePassportBundle` (claims, quotations, offsets, and summary metrics).
2. `POST /api/v1/workspaces/{workspace_id}/evidence/{evidence_id}/correct`  
   Reviewer edits a claim, updates quotation/offsets, sets semantic assessment, records mandatory reason, and saves to audit history.
3. `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/evidence`  
   Creates manual evidence claim with backend deterministic quotation verification.
4. `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/evidence/revalidate`  
   Revalidates all evidence items for a paper group against the current stored record text.
5. `GET /api/v1/workspaces/{workspace_id}/evidence/summary`  
   Workspace-wide transparency metrics (% verified quotes, % needing review, PICO coverage).
6. `GET /api/v1/workspaces/{workspace_id}/evidence/export`  
   Downloads CSV export with formula injection sanitization.

---

## 4. User Interface

The Evidence Passport panel is embedded directly into the screening workbench in [`frontend/src/features/review-queue/ReviewQueuePage.tsx`](file:///c:/Hackathon/epoch/Evidra/frontend/src/features/review-queue/ReviewQueuePage.tsx) under the **Passport** tab:
- **Summary Metrics Bar:** Displays Verified Quotes count, Requires Review count, PICO Evidence coverage, Human Corrected count, and Contradictory Evidence count.
- **Filter Tabs:** Filter claims by `All`, `PICO Elements`, `Screening Rationales`, or `Requires Review`.
- **Claim Cards:** Each card displays claim type, current value, original AI value, provenance tag, status badge with explanatory tooltip, semantic support tag, supporting quote box, and correction history.
- **Interactive Source Passage Highlighter:** Clicking any quotation displays the stored abstract with the exact passage highlighted and auto-scrolled into view.
- **Reviewer Correction Modal:** Allows reviewers to correct claims, adjust quotations, select semantic support assessment, and provide audit reasons.

---

## 5. Verification Commands

To verify the implementation locally, run:

```powershell
# 1. Backend Linting & OpenAPI Contract Check
cd c:\Hackathon\epoch\Evidra\backend
uv run --locked ruff check app tests scripts
uv run --locked python scripts/export_openapi.py --check
uv run --locked alembic heads

# 2. Backend Unit, Service, and Integration Tests (198 tests)
uv run --locked pytest -q

# 3. Frontend Schema Drift, Typecheck, Unit Tests, and Build (31 tests)
cd c:\Hackathon\epoch\Evidra\frontend
npm run api:check
npm run typecheck
npm run test:unit
npm run build
```
