"""Automated tests validating reproducibility of final algorithm evaluations (B06)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVALS_DIR = ROOT / "evals"


def test_eval_manifest_integrity():
    manifest_path = EVALS_DIR / "manifest.json"
    assert manifest_path.exists(), "evals/manifest.json must exist"

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["manifest_version"] == "2.0.0"
    algos = manifest["algorithms"]

    # 1. Deduplication
    assert "dedup" in algos
    dedup = algos["dedup"]["evaluation"]
    assert dedup["precision"] == 1.0
    assert dedup["recall"] == 1.0
    assert dedup["study_vs_paper_false_merges"] == 0

    # 2. Screening
    assert "screening" in algos
    scr = algos["screening"]["evaluation"]
    assert scr["accuracy"] == 1.0
    assert scr["reason_completeness"] == 1.0
    assert scr["maybe_rate"] > 0.0  # Honest abstention required

    # 3. Classical ML Ranking
    assert "classical_ml_ranking" in algos
    ml = algos["classical_ml_ranking"]["evaluation"]
    assert ml["wss_at_95"] > 0.20  # Work saved at 95% recall > 20%
    assert ml["recall_at_75_pct"] >= 0.90  # Recall at 75% cutoff >= 90%
    assert ml["inference_ms_per_record"] < 50.0  # Real-time responsiveness

    # 4. Deterministic PICO
    assert "pico_deterministic" in algos
    pico = algos["pico_deterministic"]["evaluation"]
    assert pico["validation_failures"] == 0
    assert pico["span_validity_rate"] == 1.0
    assert pico["total_spans"] > 50

    # 5. Optional LLM Extraction
    assert "llm_extraction_optional" in algos
    llm = algos["llm_extraction_optional"]["evaluation"]
    assert llm["valid_span_rate"] == 1.0
    assert llm["forged_quote_rejection_rate"] == 1.0

    # 6. Optional RAG Assistant
    assert "rag_assistant_optional" in algos
    rag = algos["rag_assistant_optional"]["evaluation"]
    assert rag["citation_verification_rate"] == 1.0
    assert rag["out_of_domain_abstention_rate"] == 1.0


def test_final_evaluation_results_json_matches_manifest():
    manifest_path = EVALS_DIR / "manifest.json"
    results_path = EVALS_DIR / "final_evaluation_results.json"

    assert results_path.exists(), "evals/final_evaluation_results.json must exist"

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    assert results == manifest["algorithms"]
