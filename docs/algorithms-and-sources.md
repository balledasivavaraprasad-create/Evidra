# Sources, deterministic algorithms and ML additions

## 1. Shared source adapter

Interface: `search_count(query_spec) -> SearchExecution`; `iter_ids(execution, checkpoint) -> pages`; `fetch_records(ids) -> normalized records + errors`. Save exact query, source namespace, fetch time, adapter version, raw checksum and mapping warnings. All adapters return the same typed record model. Frozen test data gets a separate adapter only after its format is known; do not assume it is a CSV or a live API replay.

### PubMed

Use ESearch for counts/IDs and EFetch for abstracts/metadata, with Entrez history/batching when appropriate. NCBI documents limits of 3 requests/second without a key and 10 with one, per shared site/IP context; it also describes tool/email registration and off-peak bulk usage ([NCBI usage guidance](https://www.ncbi.nlm.nih.gov/books/NBK25497/)). Choose conservative application limits below these ceilings; coordinate all workers rather than giving each its own full allowance. Display the NCBI disclaimer and attribution link required by the pre-read. Registration is an operational team action, not achieved merely by writing a tool/email parameter.

Translate the Boolean AST with parentheses and properly encoded phrases; declare publication-date semantics with inclusive dates. Keep the translated query for reproducibility. Save ESearch count separately from IDs actually imported. Large PubMed result retrieval has service-specific limitations: confirm the current ESearch limit in [parameter documentation](https://www.ncbi.nlm.nih.gov/books/NBK25499/); date-partition large queries or expose an explicit cap instead of pretending all hits were imported.

Parse XML with external entities disabled (`defusedxml`), bounded response sizes and timeouts. Handle multiple `AbstractText` sections and labels, author collective names, missing journal/year, publication dates with seasons/ranges, multiple language tags, DOI locations and missing abstracts. Create the canonical abstract text once and preserve its hash. Do not use publication date heuristics to silently drop records.

### Europe PMC

Use its [REST API](https://europepmc.org/RestfulWebService), explicitly request JSON, a fixed page size and `resultType=core` when abstracts/metadata are needed. Persist cursor progression, source namespace and identifier; do not identify all returned records as MED/PubMed. Set synonym expansion explicitly and record the setting rather than relying on the pre-read's stated default. Count and search semantics may differ from PubMed; label them in the UI. Current endpoint behavior still needs a small live integration smoke test; documentation access was partially restricted during planning.

Use conservative pacing, honor `Retry-After`, and tune against actual responses; do not invent a Europe PMC quota. A repeated cursor, empty page with remaining count, unexpected schema, or partial source failure must not loop forever. DOI/PMID matching reconciles source overlap through deduplication while keeping provenance.

### Shared reliability defaults (project choices)

Connect timeout 5 seconds, read timeout 30 seconds; at most 3 transient attempts with jitter and a total job deadline. Retry 429/temporary 5xx/network failures, not invalid queries or authorization failures. Persist progress between batches, allow cancellation between pages, and never hold a write transaction during backoff. Begin demo imports with a configurable 200-record cap, explicitly displayed; increase after measurement and organizer guidance. These are engineering defaults, not scoring constraints.

## 2. Deduplication: same paper, not merely same topic or trial

Normalize DOI by trimming, removing known DOI URL/prefix wrappers and case-folding; validate syntax without treating failed validation as identity loss. Normalize PMID as digit text. Keep original values. Normalize titles with Unicode normalization, case folding, whitespace/punctuation simplification; retain meaning-bearing numbers. Missing values are unknown, not equal.

**Phase A:** repeat source ID is an upsert, not a newly created duplicate. Matching non-conflicting DOI/PMID strongly supports same paper. Conflicting strong identifiers or correction/retraction/version signals route to manual review rather than automatic merge.

**Phase B:** block candidate pairs using combinations of year ±1, title-token fingerprint, first-author surname and journal. Use multiple blocking keys so a missing author does not exclude a plausible candidate. For small inputs compare all candidates as a reference test; do not require all fields to match in order to consider a pair.

**Phase C:** compute title similarity plus independent author/year/journal/page evidence. A provisional score can weight title 0.55, author 0.20, year 0.10, journal 0.10, pages 0.05, renormalizing only observed fields **and requiring at least two independent supporting fields**. This is a proposed heuristic, not a calibrated probability. Tune on labeled fixtures and report errors. Default fuzzy candidates require human confirmation; auto-merge only exact, consistent identifiers until precision is demonstrated.

**Phase D:** form groups from accepted edges with deterministic ordering. A strong-identifier contradiction or explicit human-rejected edge is a cannot-link constraint. Before transitive A–B–C merging, validate the proposed whole component against constraints; send uncertain bridge merges to review. Persist edges, rejected decisions, membership and lineage. Representative choice: reviewer-pinned if valid; otherwise complete abstract, richer metadata, stable source preference, then stable record ID. Never use fetch order or current time as a tie break.

Conference paper vs journal report, trial protocol vs results, follow-up analyses and papers sharing a registration number are not duplicates solely because they concern the same study. Test these as hard negatives.

## 3. Screening: explainable, conservative eligibility

Every criterion returns `pass|fail|unknown`, a reason code, human-readable explanation, evidence location/value, source (`metadata|rule|ml|llm|human`) and method version. Aggregate: any well-supported active exclusion → Exclude; all necessary criteria pass → Include; otherwise Maybe. A human can override. Exclude requires at least one active criterion and reason; confidence alone is not a reason.

Prefer language/publication-type/species metadata where available, retaining disagreements. Text fallback must consider negation and context. “Unlike studies in mice, we enrolled adults” is not animal-only. “A model adjusted the human trial outcomes” is not a simulation-only study. Language detection for tiny/mixed abstracts should abstain; implement a documented stopword/script heuristic or a separately validated detector. Missing comparator, missing abstract or uncertain population usually means Maybe, not an invented negative finding.

**Classical ML after baseline:** TF-IDF word/character features plus class-weighted logistic regression. Fit vectorizer only on training data. Split by paper/study and preferably whole review to avoid duplicate/topic leakage; preserve a holdout. Use labels from explicit eligibility review, not pseudo-labels masquerading as ground truth. On too few positives or one-class data, skip training. Use model output to prioritize the review queue or flag disagreement; do not silently auto-exclude based on an uncalibrated score. Pin model artifact hash, sklearn version and feature/label schema. Never load untrusted pickle/joblib files.

## 4. PICO extraction

Run on every included abstract and on newly human-included records. Empty/missing abstracts produce an explicit unavailable result and manual-review path. Pattern baseline extracts population phrases, treatments/doses, comparator cues (“versus”, “compared with”, “placebo”, “control group”) and outcome phrases tied to measured endpoints. Return multiple exact spans where supported. Distinguish outcome from an invented effect claim. No comparator in text → C absent; never hallucinate a comparator to fill a form.

Store half-open code-point offsets into the immutable abstract revision, quote, label and provenance. Preserve cross-label overlaps and repeated mentions. Rule matching against normalized text must map back to original offsets; easiest baseline matches the original text with case-insensitive patterns. The UI shows original text and can add/delete/relabel spans. Re-annotation produces a human event, not edits to machine output.

Optional LLM receives one bounded abstract plus extraction schema; returns evidence quotes/offsets, no database actions. Validate every quote and offset deterministically. If a quote occurs more than once, require unambiguous occurrence/offset; do not choose the first match silently. At most one repair attempt, then fallback to rules/manual review. Evaluate separate P, I, C, O scores, especially C.

## 5. Data use and evaluation discipline

[SYNERGY](https://github.com/asreview/synergy-dataset) documents 26 reviews and strong class imbalance (2,834 included among 169,288 records) and identifies CC0 licensing. Freeze a release/commit and record attribution when used. Treat its labels as review-specific: a record relevant to one question is not universal relevance truth. It is optional and not needed to complete Level 1.

[EBM-NLP](https://github.com/bepnye/EBM-NLP) describes 4,993 abstracts with P/I/O annotations, including expert test labels and noisy aggregated training labels. There is no separate comparator label. The supplied pre-read says the Hugging Face license is unknown and restricts use to training/testing without redistribution. Follow that event restriction; do not claim it is cleared for redistribution. If using a legacy loading script, inspect and convert offline to a controlled format; do not enable arbitrary remote code. Model training and dataset conversion are deferred unless time and rights permit.

Build a small synthetic edge-case suite immediately, then a manually labeled abstract-only development/holdout set appropriate to the selected topic. Keep source IDs and decisions separate from training features. Double-label a subset and record disagreements. Do not report a metric until predictions and references were actually evaluated; distinguish team-labeled tests from organizer tests.
