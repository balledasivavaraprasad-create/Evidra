"""Bounded heterogeneous features and optional boosting challengers.

No optional estimator is imported by normal API startup. All learned transforms
belong inside the pipeline fitted on the training partition.
"""
from __future__ import annotations

import numpy as np
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from app.ml_feature.types import RecordInput

FEATURE_SCHEMA = "heterogeneous-v1"


def feature_rows(records: list[RecordInput]) -> np.ndarray:
    """Only features available before human review; no IDs/labels/rule outputs.

    Each record is bounded identically in offline training and online scoring.
    """
    rows = []
    for record in records:
        title = (record.title or "")[:50000]
        abstract = (record.abstract_text or "")[:50000]
        rows.append([title, abstract, len(title), len(abstract),
                     "present" if abstract.strip() else "missing"])
    return np.asarray(rows, dtype=object).reshape((-1, 5))


class SafeTfidf(TransformerMixin, BaseEstimator):
    """Represent an empty text branch without breaking the other branches."""

    def __init__(self, max_features=2000, analyzer="word", ngram_range=(1, 2)):
        self.max_features = max_features
        self.analyzer = analyzer
        self.ngram_range = ngram_range

    def fit(self, X, y=None):
        self.vectorizer_ = TfidfVectorizer(
            max_features=self.max_features, analyzer=self.analyzer,
            ngram_range=self.ngram_range, sublinear_tf=True,
            stop_words=None, dtype=np.float32,
        )
        self.empty_ = False
        try:
            self.vectorizer_.fit(X)
        except ValueError as exc:
            if "empty vocabulary" not in str(exc):
                raise
            self.empty_ = True
        return self

    def transform(self, X):
        if self.empty_:
            return sparse.csr_matrix((len(X), 1), dtype=np.float32)
        return self.vectorizer_.transform(X)

    def get_feature_names_out(self, input_features=None):
        if self.empty_:
            return np.asarray(["empty_text"])
        return self.vectorizer_.get_feature_names_out()


def _numeric(X):
    return np.asarray(X, dtype=np.float32)


class BoundedSVD(TransformerMixin, BaseEstimator):
    """Fold-fitted reduction with feasible dimensions and a bounded dense output."""

    def __init__(self, n_components=32, seed=42):
        self.n_components = n_components
        self.seed = seed

    def fit(self, X, y=None):
        dimensions = min(self.n_components, X.shape[1] - 1, X.shape[0] - 1)
        if dimensions < 1:
            raise ValueError("Insufficient rows/features for SVD")
        self.reducer_ = TruncatedSVD(n_components=dimensions, random_state=self.seed)
        self.reducer_.fit(X)
        return self

    def transform(self, X):
        if X.shape[0] * self.reducer_.n_components > 5_000_000:
            raise ValueError("Dense SVD output exceeds resource bound")
        return self.reducer_.transform(X).astype(np.float32)


def build_challenger(family: str, *, seed=42, max_features=2000,
                     character=False, svd=False, strength=1.0, positive_weight=1.0,
                     iterations=120) -> Pipeline:
    """Family-specific classifiers behind the same record/feature contract."""
    numeric = Pipeline([
        ("cast", FunctionTransformer(_numeric, feature_names_out="one-to-one")),
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ])
    branches = [
        ("title", SafeTfidf(max_features=max_features), 0),
        ("abstract", SafeTfidf(max_features=max_features), 1),
        ("numeric", numeric, [2, 3]),
        ("availability", OneHotEncoder(handle_unknown="ignore", dtype=np.float32), [4]),
    ]
    if character:
        branches.append(("characters", SafeTfidf(max_features=max_features,
                                                analyzer="char_wb", ngram_range=(3, 5)), 1))
    features = ColumnTransformer(branches, sparse_threshold=1.0,
                                 transformer_weights={"title": 1.5}, n_jobs=1)
    if family == "logistic":
        estimator = LogisticRegression(C=strength, class_weight="balanced",
                                       max_iter=1000, random_state=seed)
    elif family == "xgboost":
        from xgboost import XGBClassifier
        estimator = XGBClassifier(
            objective="binary:logistic", tree_method="hist", device="cpu", n_jobs=2,
            n_estimators=iterations, learning_rate=0.08, max_depth=3,
            min_child_weight=1, subsample=0.9, colsample_bytree=0.8,
            reg_lambda=strength, reg_alpha=0.1, scale_pos_weight=positive_weight,
            random_state=seed, eval_metric="logloss",
        )
    elif family == "catboost":
        from catboost import CatBoostClassifier
        estimator = CatBoostClassifier(
            iterations=iterations, depth=4, learning_rate=0.08,
            l2_leaf_reg=strength, loss_function="Logloss", thread_count=2,
            auto_class_weights="Balanced", random_seed=seed,
            verbose=False, allow_writing_files=False,
        )
    else:
        raise ValueError(f"Unsupported challenger family: {family}")
    steps = [("features", features)]
    if svd:
        steps.append(("svd", BoundedSVD(seed=seed)))
    steps.append(("classifier", estimator))
    return Pipeline(steps)


def fit_with_early_stopping(pipeline, training: list[RecordInput], validation: list[RecordInput],
                            *, family: str, rounds=15):
    """Optional future experiment: validation MUST be a training-internal split.

    Frozen test/outer scoring folds never belong here. The current quick benchmark
    deliberately uses fixed tree counts and does not claim early-stopping results.
    """
    if family not in {"xgboost", "catboost"} or not 1 <= rounds <= 100:
        raise ValueError("Supported family and bounded stopping rounds required")
    train_groups = {r.group_id or r.id for r in training}
    validation_groups = {r.group_id or r.id for r in validation}
    if not validation or train_groups & validation_groups:
        raise ValueError("Early-stopping validation groups must be disjoint")
    if any(r.label not in (0, 1) for r in training + validation):
        raise ValueError("Explicit binary labels required")
    features = pipeline[:-1]
    y_train, y_validation = [r.label for r in training], [r.label for r in validation]
    train_matrix = features.fit_transform(feature_rows(training), y_train)
    validation_matrix = features.transform(feature_rows(validation))
    estimator = pipeline.named_steps["classifier"]
    estimator.set_params(early_stopping_rounds=rounds)
    if family == "xgboost":
        estimator.fit(train_matrix, y_train, eval_set=[(validation_matrix, y_validation)], verbose=False)
    else:
        estimator.fit(train_matrix, y_train, eval_set=(validation_matrix, y_validation), use_best_model=True)
    return pipeline
