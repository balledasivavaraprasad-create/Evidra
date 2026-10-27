# ML Review Prioritization Evaluation Report (C-ML01)

## 1. Task Definition & Review Question Scope

The machine learning feature prioritizes biomedical literature records for human screening in the review queue. It computes a continuous review priority score in \([0.0, 1.0]\) where higher scores represent higher likelihood that the record meets inclusion criteria for the agreed systematic review question:

> **Review Question:** *"In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?"*

### Critical Invariants
1. **Queue Prioritization Only:** The model reorders the review queue so human reviewers inspect likely relevant RCTs earlier. It does **not** decide final eligibility and does **not** silently exclude records.
2. **Scope Protection:** The trained artifact strictly binds to the review question scope. Out-of-scope queries are explicitly rejected or tagged `OUT_OF_SCOPE`.
3. **Artifact Integrity:** The model binary `model.joblib` is protected with SHA-256 fingerprint verification against `manifest.json`.

---

## 2. Dataset & Leakage-Free Splitting

The benchmark dataset ([`evals/ml_c/dataset.json`](dataset.json)) comprises 40 clinical records conforming to [`docs/review-question.md`](../../docs/review-question.md) and [`evals/screening/fixtures.json`](../screening/fixtures.json):
- **Positive Records (20 cases):** Randomized controlled clinical trials, double-blind placebo-controlled studies, and comparative prospective cohorts of metformin in adult type 2 diabetics with measured HbA1c changes.
- **Negative Records (20 cases):** Preclinical rodent models (Sprague-Dawley rats, Wistar rats, mice), in silico molecular docking/simulation studies, single-patient case reports, off-target populations (pediatric type 1 diabetes, gestational diabetes, healthy volunteers), and in vitro cell culture studies.

### Leakage-Free Group Partitioning
To guarantee zero data leakage:
- Records sharing the same clinical study or duplicate publication group (`group_id`) are strictly isolated to the exact same split using `create_leakage_free_split()`.
- Vocabulary fitting and IDF weight calculation are performed **exclusively** on the training split.
- Split fingerprints:
  - **Train Split (24 records):** SHA-256 recorded in manifest
  - **Validation Split (8 records):** SHA-256 recorded in manifest
  - **Held-Out Test Split (8 records):** SHA-256 recorded in manifest

---

## 3. Model Architecture & Bounded Resources

- **Vectorization:** `TfidfVectorizer` (sublinear TF scaling, max 500 n-gram features, unigram + bigram, English stop-word filtering).
- **Classification:** `LogisticRegression` (class-weighted balanced penalties, L2 penalty with \(C=1.5\), L-BFGS solver, fixed seed `42`).
- **Resource Bounds:** Bounded to 500 features and lightweight in-memory inference without GPU acceleration or remote API dependencies.

---

## 4. Benchmark Evaluation Results

Evaluated on the 8 held-out test records (4 positive, 4 negative):

| Metric | Measured Value | Baseline Comparison | Clinical Interpretation |
|---|---|---|---|
| **ROC-AUC** | **1.0000** | 0.5000 (Random) | Perfect ranking separation between relevant and excluded papers |
| **PR-AUC (Avg Precision)** | **1.0000** | 0.5000 (Random) | Sustained precision across all recall levels |
| **WSS@95 (Work Saved)** | **0.4500 (45.0%)** | 0.0000 (Random) | Human reviewers screen 45% fewer papers to find 95% of relevant evidence |
| **Precision@5** | **0.8000 (80.0%)** | 0.5000 (Random) | 4 out of the top 5 prioritized papers in queue are relevant clinical trials |
| **Inference Latency** | **1.544 ms / record** | N/A | Sub-2ms per record allows real-time interactive queue re-ranking |

### Top 5 Prioritized Records on Test Set

| Queue Rank | Record ID | Priority Score | True Status | Study Title |
|---|---|---|---|---|
| **1** | `rec-ml-019` | **0.8037** | Relevant (1) | *Metformin versus placebo for prevention of glycemic deterioration in adult diabetic patients* |
| **2** | `rec-ml-020` | **0.7818** | Relevant (1) | *Comparative study of metformin and empagliflozin monotherapy in adult type 2 diabetes* |
| **3** | `rec-ml-003` | **0.7618** | Relevant (1) | *Comparative clinical trial of oral metformin versus sulfonylurea monotherapy in adult diabetics* |
| **4** | `rec-ml-004` | **0.7208** | Relevant (1) | *Metformin extended-release versus immediate-release in poorly controlled type 2 diabetes* |
| **5** | `rec-ml-038` | **0.3752** | Excluded (0) | *Historical perspective on the discovery and clinical adoption of biguanides: review* |

---

## 5. Limitations & Future Work

1. **Topic Specificity:** The artifact is tailored to the Metformin / T2D review question. Switching to another review question requires retraining a scoped artifact; the system safely rejects scope mismatches.
2. **Missing Abstracts:** Records without abstract text receive `state="UNAVAILABLE"` and `score=0.0` with reason `MISSING_ABSTRACT`, routing them directly to manual reviewer inspection.
