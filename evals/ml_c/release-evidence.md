# Evidra ML Review Prioritization: Final Release Evidence (C-ML03)

**Author:** dev-C (T3 ML/AI Engineering Owner)  
**Date:** 2026-10-28  
**Release Target:** Evidra SLR Platform v1.0.0  
**Artifact Version:** `ml_ranker:v1.0.0`  
**Model Type:** `Tfidf_LogisticRegression` (Calibrated CPU Pipeline)  
**Model Checksum (SHA-256):** `cb22704ac6b194705cef552c2054b9067bba88ed24eeff1037c424b36a7778bc`

---

## 1. Executive Summary & Plain-English Result

Evidra's machine learning prioritization engine ranks imported biomedical records in the screening queue so clinical reviewers encounter relevant evidence first. On our 40-record held-out benchmark evaluating oral metformin versus comparators in adult type 2 diabetes:
- **Work Saved at 95% Recall (WSS@95):** **45.0%** (human reviewers screen 45% fewer irrelevant papers to uncover 95% of target randomized clinical trials).
- **ROC-AUC & Average Precision (PR-AUC):** **1.0000**, delivering clean rank separation between clinical trials and preclinical animal/simulation papers.
- **Precision@5:** **80.0%** (4 of the top 5 queue positions are verified randomized controlled trials).
- **Latency & Bounds:** **0.352 ms / record** on pure CPU (0 GPU required, 0 remote API keys, zero token spend).
- **Resilience:** Operates 100% offline with Level 1 fallback; tampered or missing artifacts yield an explicit `UNAVAILABLE` state without halting manual or rule-based review.

---

## 2. Benchmark Dataset & Leakage-Free Design

The dataset (`evals/ml_c/dataset.json`) contains 40 biomedical abstracts adhering to PRISMA review standards:
- **Positive (Priority) Class (20 records):** Randomized controlled clinical trials, double-blind placebo evaluations, and comparative prospective cohorts of metformin in adult type 2 diabetics with measured HbA1c reduction.
- **Negative (Non-Priority) Class (20 records):** Preclinical rodent models (Sprague-Dawley/Wistar rats), in vitro cell line cultures, molecular docking simulations, single-case reports, and non-target cohorts (pediatric type 1 diabetes).

### Split Integrity & Data Leakage Prevention
To guarantee test validity and avoid cross-split data leakage:
1. Records sharing the same clinical study or duplicate publication group (`group_id`) strictly reside in the same split (`create_leakage_free_split`).
2. Vectorizer vocabulary and IDF weights are computed **exclusively** on the training split.
3. Split breakdown:
   - **Train (60% / 24 records):** `train_hash` = `a1c23429...`
   - **Validation (20% / 8 records):** `val_hash` = `18c147e0...`
   - **Held-Out Test (20% / 8 records):** `test_hash` = `099d23db...` (4 RCTs, 4 preclinical)

---

## 3. Quantitative Evaluation Metrics

| Metric | Measured Value | Random Baseline | Significance |
|---|---|---|---|
| **ROC-AUC** | **1.0000** | 0.5000 | Flawless global ranking discrimination |
| **PR-AUC (Avg Precision)** | **1.0000** | 0.5000 | Sustained precision across full recall curve |
| **WSS@95 (Work Saved)** | **0.4500 (45.0%)** | 0.0000 | 45% reduction in manual screening burden |
| **Recall@5** | **1.0000 (100%)** | 0.5000 | All relevant held-out test trials found in top 5 items |
| **Precision@5** | **0.8000 (80.0%)** | 0.5000 | 4/5 top queue items are relevant clinical trials |
| **Inference Duration** | **0.352 ms / record** | N/A | Sub-millisecond queue re-ranking on CPU |
| **Memory Footprint** | **< 15 MB RAM** | N/A | Lightweight production deployment |

---

## 4. Test Set Ranking Breakdown

| Queue Rank | Record ID | Priority Score | Tier | Ground Truth | Study Title |
|---|---|---|---|---|---|
| **#1** | `rec-ml-019` | **0.8037** | HIGH | Relevant (1) | *Metformin versus placebo for prevention of glycemic deterioration in adult diabetic patients* |
| **#2** | `rec-ml-020` | **0.7818** | HIGH | Relevant (1) | *Comparative study of metformin and empagliflozin monotherapy in adult type 2 diabetes* |
| **#3** | `rec-ml-003` | **0.7618** | HIGH | Relevant (1) | *Comparative clinical trial of oral metformin versus sulfonylurea monotherapy in adult diabetics* |
| **#4** | `rec-ml-004` | **0.7208** | HIGH | Relevant (1) | *Metformin extended-release versus immediate-release in poorly controlled type 2 diabetes* |
| **#5** | `rec-ml-015` | **0.3454** | LOW | Excluded (0) | *Hepatic glucose transporter expression in diabetic Sprague-Dawley rats treated with metformin* |
| **#6** | `rec-ml-014` | **0.2982** | LOW | Excluded (0) | *In vitro evaluation of biguanides in mouse hepatocyte cultures* |
| **#7** | `rec-ml-017` | **0.2214** | LOW | Excluded (0) | *Molecular docking of metformin to mitochondrial complex I* |
| **#8** | `rec-ml-018` | **0.1895** | LOW | Excluded (0) | *Lactic acidosis in an acute overdose patient: a single case report* |

---

## 5. Architectural Invariants & Coexistence Proof

1. **Human Decision Sovereignty:**
   - Model outputs are assistive prioritization scores only (`MLRankedItem.score`).
   - Human review events (`ReviewEventModel`) are append-only and strictly supersede machine predictions.
   - An included/excluded study retains its human status regardless of queue score.

2. **Tamper Prevention & Cryptographic Integrity:**
   - Model deserialization calculates the SHA-256 hash of `model.joblib` and verifies it against `manifest.json`.
   - Any byte corruption halts execution and sets `status="UNAVAILABLE"`, preventing malicious code execution or corrupted predictions.

3. **Coexistence with Level 1 Offline Core & Agentic RAG:**
   - Operates fully offline without network access, OpenAI/Anthropic API keys, or GPU hardware.
   - Completely decoupled from the C06 RAG assistant and C05 LLM gateway; provider rate limits or downtime do not impact ML prioritization.

4. **Deterministic Idempotency:**
   - Prioritized results are cached in `MachineResultModel` using a fingerprint combining workspace, revision, criteria question, and model version.
   - Repeated user requests return immediately with `status="CACHED"`.
