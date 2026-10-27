"""Default review criteria definitions conforming to docs/review-question.md."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from app.contracts.models import CriteriaVersionResponse, CriterionDefinition

METHOD_VERSION = "screening-rules-v1.0.0"

# Standard review criteria definitions based on review question:
# "In adults with type 2 diabetes, how does metformin, compared with placebo or
# another glucose-lowering intervention, affect HbA1c?"
DEFAULT_CRITERIA_DEFINITIONS: list[CriterionDefinition] = [
    CriterionDefinition(
        id="population_adults_t2d",
        name="Target Population: Adults with Type 2 Diabetes",
        category="population",
        is_inclusion=True,
        rationale="Study must evaluate human adult patients diagnosed with type 2 diabetes mellitus.",
        metadata_first=True,
    ),
    CriterionDefinition(
        id="comparative_clinical_design",
        name="Study Design: Comparative Clinical Investigation",
        category="study_design",
        is_inclusion=True,
        rationale="Study must be an empirical clinical trial, randomized trial, or comparative cohort study.",
        metadata_first=True,
    ),
    CriterionDefinition(
        id="exclude_animal_only",
        name="Exclude Animal-Only Preclinical Studies",
        category="species",
        is_inclusion=False,
        rationale="Preclinical animal models (rats, mice, dogs) without human clinical evaluation must be excluded.",
        metadata_first=True,
    ),
    CriterionDefinition(
        id="exclude_simulation_only",
        name="Exclude Simulation-Only Studies",
        category="methodology",
        is_inclusion=False,
        rationale="In silico, computational docking, or purely theoretical modeling without patient data must be excluded.",
        metadata_first=True,
    ),
    CriterionDefinition(
        id="exclude_case_reports",
        name="Exclude Single Case Reports",
        category="study_design",
        is_inclusion=False,
        rationale="Individual patient case reports lack comparative control groups and must be excluded.",
        metadata_first=True,
    ),
    CriterionDefinition(
        id="english_language",
        name="Language: English Reviewable",
        category="language",
        is_inclusion=True,
        rationale="Article must be reviewable in English as per protocol capacity constraints.",
        metadata_first=True,
    ),
    CriterionDefinition(
        id="abstract_available",
        name="Content: Abstract Text Availability",
        category="content",
        is_inclusion=True,
        rationale="Record must have an accessible abstract for title/abstract screening stage.",
        metadata_first=False,
    ),
]


def compute_criteria_hash(criteria: list[CriterionDefinition]) -> str:
    """Calculate deterministic SHA-256 fingerprint for criteria configuration."""
    canonical_payload = [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "is_inclusion": c.is_inclusion,
            "rationale": c.rationale,
            "metadata_first": c.metadata_first,
        }
        for c in sorted(criteria, key=lambda x: x.id)
    ]
    raw = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_default_criteria_version(
    workspace_id: str = "ws-default",
    version_id: str = "crit-ver-default",
    sequence: int = 1,
) -> CriteriaVersionResponse:
    """Instantiate canonical default review criteria version."""
    criteria = list(DEFAULT_CRITERIA_DEFINITIONS)
    content_hash = compute_criteria_hash(criteria)
    return CriteriaVersionResponse(
        id=version_id,
        workspace_id=workspace_id,
        sequence=sequence,
        question="In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?",
        pico_description={
            "population": "Adults with type 2 diabetes",
            "intervention": "Metformin",
            "comparator": "Placebo or another glucose-lowering intervention",
            "outcome": "Change in HbA1c",
        },
        criteria=criteria,
        content_hash=content_hash,
        created_at=datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
    )
