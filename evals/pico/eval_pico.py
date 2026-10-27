"""Benchmark evaluation script for PICO baseline extractor across canonical synthetic records."""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[2] / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.contracts.enums import PicoLabel
from app.contracts.models import RecordRevisionResponse
from app.pico.extractor import extract_pico_spans
from app.pico.validator import validate_pico_result
from tests.fixtures.synthetic_records import ALL_SYNTHETIC_RECORDS


def run_pico_evaluation() -> dict[str, int]:
    """Evaluate PICO baseline extractor against all synthetic canonical records."""
    total_records = len(ALL_SYNTHETIC_RECORDS)
    total_spans = 0
    p_spans = 0
    i_spans = 0
    c_spans = 0
    o_spans = 0
    validation_failures = 0

    print(f"--- Running PICO Evaluation across {total_records} Canonical Synthetic Records ---")

    for rec_dict in ALL_SYNTHETIC_RECORDS:
        record = RecordRevisionResponse(**rec_dict)
        result = extract_pico_spans(record)
        is_valid, errors = validate_pico_result(result, record.abstract_text)

        if not is_valid:
            print(f"FAILED validation on record {record.id} ({record.title}): {errors}")
            validation_failures += 1
            continue

        for span in result.spans:
            total_spans += 1
            if span.label == PicoLabel.P:
                p_spans += 1
            elif span.label == PicoLabel.I:
                i_spans += 1
            elif span.label == PicoLabel.C:
                c_spans += 1
            elif span.label == PicoLabel.O:
                o_spans += 1

            # Assert quote equals exact text slice
            if record.abstract_text is not None:
                assert record.abstract_text[span.start_cp : span.end_cp] == span.quote

    stats = {
        "total_records": total_records,
        "total_spans": total_spans,
        "population_spans": p_spans,
        "intervention_spans": i_spans,
        "comparator_spans": c_spans,
        "outcome_spans": o_spans,
        "validation_failures": validation_failures,
    }

    print("--- PICO Evaluation Complete ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    return stats


if __name__ == "__main__":
    stats = run_pico_evaluation()
    if stats["validation_failures"] > 0:
        sys.exit(1)
    sys.exit(0)
