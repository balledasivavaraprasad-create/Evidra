# Devil's Advocate Reviewer: Adversarial Exclusion Challenge System

## 1. Overview and Problem Statement

In systematic literature reviews, the cost of a false negative (excluding a truly relevant study) is far higher than a false positive. Because reviewers must evaluate hundreds or thousands of citations rapidly, they frequently exclude studies based on:
1. Perceived absence of a comparator in an abstract (even when the full trial was comparative).
2. Overly narrow population assumptions that miss relevant cohorts or subgroup analyses.
3. Premature rejection of surrogate or secondary clinical endpoints.
4. Vague or hastily recorded exclusion rationales.

**Devil's Advocate Reviewer** adds an adversarial challenge pass to Evidra. When an exclusion is proposed (by automated screening or a human reviewer), the system independently examines the study text for counter-evidence, identifies weaknesses in the exclusion rationale, and recommends whether the decision should stand, be reconsidered, or receive dual-screening deliberation.

> [!IMPORTANT]
> **Core Invariant — Zero Silent Overrides:**
> The Devil's Advocate Reviewer actively challenges screening decisions, but it **never** silently alters a human screening decision. Overturning an exclusion requires explicit human concession through an audited workflow.

---

## 2. Challenge Reasoning & Fragility Scoring

### Fragility Signals (`VulnerabilityFlag`)
- `ABSTRACT_ONLY_LIMITATION`: Lack of full-text access makes exclusion premature (e.g. dosing or secondary outcomes omitted from abstract).
- `INDIRECT_COMPARATOR`: Text indicates active comparator, standard-of-care control, or comparative design despite an exclusion reason claiming "single-arm".
- `OVERLOOKED_SUBGROUP`: Abstract reports a sub-cohort or patient demographic meeting inclusion criteria.
- `SURROGATE_OUTCOME`: Clinical biomarkers or surrogate efficacy endpoints were reported.
- `WEAK_RATIONALE`: The stated exclusion rationale is brief ($< 15$ characters) or generic (e.g., "not relevant").
- `UNCERTAIN_PICO_ELEMENT`: Linked Missing-Evidence Radar or Evidence Passport marked the cited element as uncertain or not found in abstract.
- `COUNTER_EVIDENCE_FOUND`: Direct verbatim quotes located in the study title or abstract contradicting the exclusion rationale.

### Vulnerability Scoring & Recommendation Tiers
Vulnerability scores range from `0.0` (robust exclusion) to `1.0` (highly fragile exclusion):
- **$\ge 0.60$ $\to$ `RECONSIDER_EXCLUSION`:** Direct counter-evidence identified; high risk of false exclusion; reviewer recommended to reverse to `Maybe` (for full text) or `Include`.
- **$0.35 \le score < 0.60$ $\to$ `NEEDS_HUMAN_REVIEW`:** Borderline evidence or textual ambiguity; dual-screening or senior consensus recommended.
- **$< 0.35$ $\to$ `UPHOLD_EXCLUSION`:** Stated exclusion reason is consistent with examined text; exclusion stands.

---

## 3. Human Reviewer Disposition Lifecycle

Reviewers interact with challenges through four disposition states:
1. `PENDING`: Challenge has been formulated and is awaiting reviewer inspection.
2. `CONCEDED`: Reviewer concedes to the challenge and specifies a new status (`Include` or `Maybe`). This appends an immutable `SCREEN_DECISION` review event and updates the study's effective status without bypassing human judgment.
3. `UPHELD`: Reviewer re-evaluates the counter-arguments but reaffirms the exclusion, recording their clinical/methodological justification in the audit ledger.
4. `DISMISSED`: Reviewer marks the challenge as non-applicable.

---

## 4. API Endpoints

Under the OpenAPI tag `Devil's Advocate Reviewer`:

- `GET /api/v1/workspaces/{workspace_id}/groups/{group_id}/devils-advocate`:
  Retrieve or compute the adversarial challenge for a paper group.
- `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/devils-advocate/generate`:
  Force a fresh challenge evaluation with custom parameters.
- `POST /api/v1/workspaces/{workspace_id}/groups/{group_id}/devils-advocate/disposition`:
  Submit reviewer disposition (`conceded`, `upheld`, `dismissed`) with notes and optional new status.
- `GET /api/v1/workspaces/{workspace_id}/devils-advocate`:
  Review-level dashboard with summary metrics, concession rates, false-exclusions-saved counters, and filterable ledger.

---

## 5. UI Architecture

- **`DevilsAdvocateCard` (`frontend/src/features/devils-advocate/DevilsAdvocateCard.tsx`):**
  Embedded directly inside the Review Queue workbench under the "Devil's Advocate" tab. Features recommendation banners, vulnerability gauge, fragility tags, structured critique, verbatim counter-quotes, and one-click disposition dialogs.
- **`DevilsAdvocateDashboard` (`frontend/src/features/devils-advocate/DevilsAdvocateDashboard.tsx`):**
  Corpus-wide challenge ledger accessible at `/reviews/:id/devils-advocate` and `/devils-advocate`. Displays metric ribbons (total challenged, pending, high vulnerability, concession rate, false exclusions saved), multi-tab filtering, and modal inspection dialogs.

---

## 6. Database Schema & Migration

- **Migration:** `006_devils_advocate.py`
- **Table:** `devils_advocate_challenges`
- **Columns:**
  - `id`: `VARCHAR(64)` primary key.
  - `workspace_id`: Foreign key to `workspaces.id`, indexed.
  - `group_id`: Foreign key to `paper_groups.id`, indexed.
  - `record_revision_id`: Foreign key to `record_revisions.id`.
  - `proposed_decision`: `VARCHAR(32)`.
  - `original_exclusion_reason`: `TEXT`.
  - `recommendation`: `VARCHAR(32)`, default `'uphold_exclusion'`.
  - `vulnerability_score`: `FLOAT`, indexed.
  - `critique`: `TEXT`.
  - `counter_arguments_json`: `TEXT` JSON array.
  - `vulnerability_flags_json`: `TEXT` JSON array.
  - `disposition`: `VARCHAR(32)`, indexed, default `'pending'`.
  - `disposition_notes`: `TEXT`.
  - `disposition_by`: `VARCHAR(128)`.
  - `disposed_at`: `DATETIME`.
  - `is_active`: `BOOLEAN`, default `TRUE`.
