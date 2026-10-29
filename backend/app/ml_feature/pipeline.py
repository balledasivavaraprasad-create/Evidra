"""Scikit-learn pipeline definition and feature extraction for review prioritization."""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline

from app.ml_feature.dataset import prepare_text
from app.ml_feature.types import RecordInput, TrainConfig


def build_pipeline(config: TrainConfig) -> Pipeline:
    """Build a deterministic, bounded scikit-learn TF-IDF + LogisticRegression pipeline."""
    vectorizer = TfidfVectorizer(
        max_features=config.max_features,
        ngram_range=(config.ngram_min, config.ngram_max),
        sublinear_tf=True,
        stop_words="english",
    )

    classifier = LogisticRegression(
        C=config.c_param,
        class_weight=config.class_weight if config.class_weight != "none" else None,
        random_state=config.seed,
        solver="lbfgs",
        max_iter=1000,
    )

    return make_pipeline(vectorizer, classifier)


def extract_texts_and_labels(records: list[RecordInput]) -> tuple[list[str], list[int]]:
    """Extract canonical texts and integer labels from record inputs."""
    texts = [prepare_text(r.title, r.abstract_text) for r in records]
    labels = [r.label for r in records if r.label in (0, 1)]
    if len(texts) != len(labels):
        raise ValueError("All records must possess an integer label (0 or 1)")
    return texts, labels
