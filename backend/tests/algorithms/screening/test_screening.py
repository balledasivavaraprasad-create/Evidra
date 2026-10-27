"""Comprehensive tests for explainable screening rules engine (B02)."""
from __future__ import annotations

from app.contracts.enums import EligibilityStatus
from app.contracts.models import CriteriaVersionResponse, RecordRevisionResponse
from app.contracts.ports import ScreeningPort
from app.screening import (
    ScreeningEngine,
    compute_screening_fingerprint,
    get_default_criteria_version,
    screen_record,
)
from tests.fixtures.synthetic_records import (
    RECORD_ANIMAL_STUDY,
    RECORD_CASE_REPORT,
    RECORD_EXACT_PUBMED,
    RECORD_MISSING_ABSTRACT,
    RECORD_SIMULATION_STUDY,
)


def make_record(raw: dict) -> RecordRevisionResponse:
    return RecordRevisionResponse.model_validate(raw)


def test_screening_engine_conforms_to_port():
    """ScreeningEngine must implement runtime checkable ScreeningPort protocol."""
    engine = ScreeningEngine()
    assert isinstance(engine, ScreeningPort)


def test_human_rct_included():
    """Canonical human RCT in type 2 diabetes must receive an INCLUDE verdict."""
    record = make_record(RECORD_EXACT_PUBMED)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.INCLUDE
    assert len(result.reasons) == 0
    assert len(result.criteria_evidence) == len(criteria.criteria)


def test_animal_study_excluded():
    """Preclinical animal study must be excluded with ANIMAL_STUDY_EXCLUDED."""
    record = make_record(RECORD_ANIMAL_STUDY)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.EXCLUDE
    assert "ANIMAL_STUDY_EXCLUDED" in result.reasons


def test_human_trial_with_preclinical_background_included():
    """Human trial mentioning preclinical background must NOT be excluded as an animal study."""
    raw = dict(RECORD_EXACT_PUBMED)
    raw["id"] = "rec-human-preclinical"
    raw["abstract_text"] = (
        "Background: Previous animal studies suggested AMPK activation in rodent models. "
        "Methods: In a double-blind randomized clinical trial of 400 adult patients with type 2 diabetes, "
        "metformin was compared to placebo over 24 weeks. Results: Metformin reduced HbA1c by 1.1% in humans."
    )
    record = make_record(raw)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.INCLUDE
    assert "ANIMAL_STUDY_EXCLUDED" not in result.reasons


def test_simulation_only_excluded():
    """In silico simulation without human clinical data must be excluded."""
    record = make_record(RECORD_SIMULATION_STUDY)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.EXCLUDE
    assert "SIMULATION_ONLY_EXCLUDED" in result.reasons


def test_human_trial_with_computational_modeling_included():
    """Human clinical trial utilizing pharmacokinetic modeling must NOT be excluded."""
    raw = dict(RECORD_EXACT_PUBMED)
    raw["id"] = "rec-human-pk"
    raw["abstract_text"] = (
        "We performed a randomized clinical trial in 200 adults with type 2 diabetes. "
        "A pharmacokinetic simulation model was calibrated against measured clinical plasma concentrations and HbA1c."
    )
    record = make_record(raw)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.INCLUDE
    assert "SIMULATION_ONLY_EXCLUDED" not in result.reasons


def test_case_report_excluded():
    """Single patient case report must be excluded with CASE_REPORT_EXCLUDED."""
    record = make_record(RECORD_CASE_REPORT)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.EXCLUDE
    assert "CASE_REPORT_EXCLUDED" in result.reasons


def test_cohort_of_cases_not_excluded():
    """Cohort of cases (e.g. 500 cases) must NOT be false-positive excluded as a single case report."""
    raw = dict(RECORD_EXACT_PUBMED)
    raw["id"] = "rec-cohort-cases"
    raw["abstract_text"] = (
        "In a comparative cohort of 500 cases of adult type 2 diabetes, metformin therapy "
        "was evaluated versus lifestyle control over 3 years. Significant HbA1c reductions were observed."
    )
    record = make_record(raw)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.INCLUDE
    assert "CASE_REPORT_EXCLUDED" not in result.reasons


def test_non_english_excluded():
    """Non-English publication must be excluded with NON_ENGLISH_LANGUAGE."""
    raw = dict(RECORD_EXACT_PUBMED)
    raw["id"] = "rec-french"
    raw["language"] = ["fre"]
    record = make_record(raw)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.EXCLUDE
    assert "NON_ENGLISH_LANGUAGE" in result.reasons


def test_missing_abstract_yields_maybe():
    """Missing abstract prevents automatic pass/fail, yielding honest MAYBE abstention."""
    record = make_record(RECORD_MISSING_ABSTRACT)
    criteria = get_default_criteria_version()
    result = screen_record(record, criteria)

    assert result.status == EligibilityStatus.MAYBE
    # Missing abstract must be captured in evidence
    evidence_codes = [ev.reason_code for ev in result.criteria_evidence]
    assert "MISSING_ABSTRACT" in evidence_codes


def test_toggling_criteria_alters_only_affected_results():
    """Disabling a criterion alters results only where that criterion triggered."""
    record = make_record(RECORD_ANIMAL_STUDY)
    default_criteria = get_default_criteria_version()

    # Default criteria excludes animal study
    res_default = screen_record(record, default_criteria)
    assert res_default.status == EligibilityStatus.EXCLUDE
    assert "ANIMAL_STUDY_EXCLUDED" in res_default.reasons

    # Create modified criteria without the animal exclusion rule
    modified_criteria_list = [c for c in default_criteria.criteria if c.id != "exclude_animal_only"]
    modified_criteria = CriteriaVersionResponse(
        id="crit-ver-no-animal-rule",
        workspace_id=default_criteria.workspace_id,
        sequence=2,
        question=default_criteria.question,
        pico_description=default_criteria.pico_description,
        criteria=modified_criteria_list,
        content_hash="modified-hash",
        created_at=default_criteria.created_at,
    )

    res_modified = screen_record(record, modified_criteria)
    # With animal rule removed, ANIMAL_STUDY_EXCLUDED is not triggered
    assert "ANIMAL_STUDY_EXCLUDED" not in res_modified.reasons


def test_deterministic_fingerprint():
    """Screening evaluation fingerprint is stable and sensitive to criteria/content changes."""
    record = make_record(RECORD_EXACT_PUBMED)
    criteria = get_default_criteria_version()

    fp1 = compute_screening_fingerprint(record, criteria)
    fp2 = compute_screening_fingerprint(record, criteria)
    assert fp1 == fp2

    # Changing criteria content alters fingerprint
    criteria_mod = CriteriaVersionResponse(
        id="crit-ver-v2",
        workspace_id=criteria.workspace_id,
        sequence=2,
        question=criteria.question,
        pico_description=criteria.pico_description,
        criteria=criteria.criteria,
        content_hash="altered-hash-123",
        created_at=criteria.created_at,
    )
    fp_mod = compute_screening_fingerprint(record, criteria_mod)
    assert fp1 != fp_mod
