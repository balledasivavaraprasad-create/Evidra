---
name: literature-pipeline
description: Implement or evaluate Mini-Rayyan PubMed/Europe PMC adapters, dedup and eligibility rules, classical ML ranking, or exact PICO extraction.
---

Read `../../docs/algorithms-and-sources.md` and the offset/schema contract in `../../docs/architecture.md` for the requested stage.

Source work must preserve provenance, explicit query semantics, partial/truncation status and resumable page progress. Counted hits are not imported records. Use shared rate limits and bounded retries; test missing metadata and malformed responses with fixtures. Do not assume the organizer's frozen-data format.

Screen criteria from metadata first; record rule evidence when metadata is absent. Negation, mixed populations and missing abstracts must be represented conservatively. Exclude requires a criterion/reason. ML initially prioritizes review; one-class or inadequate-label data must not crash the baseline.

PICO requires exact saved-text spans with a hash, not fluent paraphrases. No comparator evidence means absent C. Validate Unicode code-point offsets, repeated phrases and overlapping labels. Keep LLM extraction optional and subject to deterministic span checks.

Evaluate on separated paper/review-level splits and report the actual dataset/method versions. Do not redistribute restricted EBM-NLP content or claim its PIO labels include comparator. Keep rules-only end-to-end operation intact.
