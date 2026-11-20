"""Save, load, and score the reference ANN on large feature CSVs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sentry.classifiers import ANNClassifier

from ..dataset import FEATURE_NAMES


def model_payload(model: ANNClassifier) -> dict:
    return {
        "classifier": "ann",
        "feature_names": list(FEATURE_NAMES),
        "hidden_weights": model.hidden_weights,
        "hidden_biases": model.hidden_biases,
        "output_weights": model.output_weights,
        "output_bias": model.output_bias,
        "threshold": model.threshold,
    }


def load_model(path: Path) -> ANNClassifier:
    saved = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(saved, dict)
        or saved.get("classifier") != "ann"
        or saved.get("feature_names") != list(FEATURE_NAMES)
    ):
        raise ValueError("Expected an ANN model with Sentry's feature order")

    model = ANNClassifier(
        hidden_weights=saved["hidden_weights"],
        hidden_biases=saved["hidden_biases"],
        output_weights=saved["output_weights"],
        output_bias=saved["output_bias"],
        threshold=saved["threshold"],
    )
    if model.num_features != len(FEATURE_NAMES):
        raise ValueError("Expected an input weight for each Sentry feature")
    return model


def score_dataset(model: ANNClassifier, features: np.ndarray) -> np.ndarray:
    """Compute the reference raw scores with matrix operations."""
    if features.ndim != 2 or features.shape[1] != model.num_features:
        raise ValueError(f"Expected feature rows with {model.num_features} columns")

    # Do the hidden units' weighted sums for every window, then clip at zero.
    hidden = features @ np.asarray(model.hidden_weights).T + model.hidden_biases
    np.maximum(hidden, 0.0, out=hidden)
    # The final weighted sum turns the hidden units into one score per window.
    return hidden @ np.asarray(model.output_weights) + model.output_bias


def predict_dataset(model: ANNClassifier, features: np.ndarray) -> np.ndarray:
    return score_dataset(model, features) > model.threshold
