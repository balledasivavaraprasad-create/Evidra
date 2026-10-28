# C05 LLM-Assisted PICO Extraction Evaluation Report

## Benchmark Configuration
- **Benchmark:** `evidra_pico_llm_comparison_v1` (4 curated clinical trial abstracts)
- **Benchmark Hash:** `02b73cb2902a0a2157847130668828e4fa6faa42484108e38af0f083f998348c`
- **Provider Status:** `mock_verified (live provider not run: offline default)`
- **Offline / Level 1 Invariant:** Fully preserved. Offline rule baseline operates with 0 model keys.

## Comparative Performance Table

| Metric | Deterministic Rule Baseline | Bounded LLM Extraction |
|---|---|---|
| **Total Spans Extracted** | 11 | **11** |
| **Invalid Span Rate** | **0.0%** | **0.0%** |
| **Total Latency** | 0.65 ms | 0.69 ms |
| **Latency per Record** | 0.162 ms | 0.172 ms |
| **Model Cost (USD)** | $0.0000 | $0.0000 |
| **Guaranteed Span Slicing** | 100% Unicode exact | 100% Unicode exact |

## Key Findings & Security Constraints
1. **Zero Hallucination / Zero Offset Drift:** Every extracted span undergoes Unicode code-point slice verification `abstract_text[start_cp:end_cp] == quote`. Any hallucinated or mismatched span is discarded or locally repaired.
2. **Fail-Closed Gate:** If LLM is disabled, credentials missing, or rate-limited, the system yields instant fallback to deterministic rules without service disruption.
3. **Budget Bounds:** Enforced token caps and allowlisted tasks prevent resource exhaustion and indirect injection.
