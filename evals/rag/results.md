# C06 Bounded RAG Assistant Evaluation Report

## Benchmark Configuration
- **Benchmark:** `evidra_corpus_rag_comparison_v1` (5 questions: 3 in-domain, 2 out-of-domain)
- **Corpus Size:** 40 authorized records in in-memory FTS5 index.
- **SHA-256 Hash:** `3f569e292c9a145288184139362082648fc5d44d962b2eb83c786aca91ddd08c`

## Method Comparison Table

| Metric | Lexical Retrieval Only | One-Pass Cited RAG | Bounded Agent Loop (Reformulation + Guardrail) |
|---|---|---|---|
| **Citation Verification Rate** | 100.0% (raw snippets) | **100.0%** | **100.0%** |
| **Out-of-Domain Abstention** | 0.0% | 40.0% | **100.0%** |
| **Total Latency** | 1.0 ms | 2.19 ms | 1.96 ms |
| **Latency per Query** | 0.201 ms | 0.438 ms | 0.393 ms |
| **Requires Reviewer Approval** | Always human read | Always human read | **Always human read (100%)** |

## Key Insights & Adoption Recommendation
1. **Honest Abstention Demonstrated:** On questions outside the authorized corpus (cholecystectomy, rabies), the bounded assistant achieves 100% abstention with zero fabricated citations.
2. **Zero Invalidation / Zero Offset Drift:** Every cited chunk matches an exact slice of an authorized record in the current corpus revision.
3. **Keep/Cut Recommendation:** **RETAIN.** The bounded assistant provides valuable proposal synthesis with strictly verified provenance while maintaining zero mutation authority over reviewer decisions.
