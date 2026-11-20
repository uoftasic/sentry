"""Load and score a deep ANN using its saved weights and biases."""

from __future__ import annotations

import json
from collections.abc import Sequence
from math import isfinite
from pathlib import Path

import numpy as np

from sentry.classifier import Classifier

from ..dataset import FEATURE_NAMES


HIDDEN_LAYERS = 4


class DeepANNClassifier(Classifier):
    """Four dense ReLU layers followed by a single raw decision score."""

    def __init__(
        self,
        weights: Sequence[np.ndarray],
        biases: Sequence[np.ndarray],
        threshold: float = 0.0,
    ) -> None:
        if len(weights) != HIDDEN_LAYERS + 1 or len(biases) != len(weights):
            raise ValueError("Expected four hidden layers and one output layer")

        self.weights = tuple(np.asarray(layer, dtype=float) for layer in weights)
        self.biases = tuple(np.asarray(layer, dtype=float) for layer in biases)
        self.threshold = float(threshold)
        if not isfinite(self.threshold):
            raise ValueError("Expected a finite decision threshold")

        # Each layer must accept one input for every value the previous layer produces.
        input_width = len(FEATURE_NAMES)
        for index, (matrix, bias) in enumerate(zip(self.weights, self.biases)):
            if (
                matrix.ndim != 2
                or matrix.shape[0] != input_width
                or matrix.shape[1] < 1
                or bias.shape != (matrix.shape[1],)
                or not np.isfinite(matrix).all()
                or not np.isfinite(bias).all()
            ):
                raise ValueError(f"Invalid weights or biases for layer {index + 1}")
            input_width = matrix.shape[1]
        if input_width != 1:
            raise ValueError("Expected one output score per window")

    @property
    def parameter_count(self) -> int:
        return sum(matrix.size + bias.size for matrix, bias in zip(self.weights, self.biases))

    def score_dataset(self, features: np.ndarray) -> np.ndarray:
        if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
            raise ValueError(f"Expected feature rows with {len(FEATURE_NAMES)} columns")

        scores = np.empty(len(features), dtype=float)
        batch_size = 16_384
        for start in range(0, len(features), batch_size):
            stop = start + batch_size
            activations = features[start:stop]
            # Each hidden layer mixes the previous values and clips negative results to zero.
            for matrix, bias in zip(self.weights[:-1], self.biases[:-1]):
                activations = activations @ matrix + bias
                np.maximum(activations, 0.0, out=activations)
            # The final layer adds up the signals and produces one score for each window.
            scores[start:stop] = activations @ self.weights[-1][:, 0] + self.biases[-1][0]
        return scores

    def predict_dataset(self, features: np.ndarray) -> np.ndarray:
        return self.score_dataset(features) > self.threshold

    def score(self, feature_vector: Sequence[float]) -> float:
        return float(self.score_dataset(np.asarray([feature_vector], dtype=float))[0])

    def predict(self, feature_vector: Sequence[float]) -> bool:
        return self.score(feature_vector) > self.threshold


def model_payload(model: DeepANNClassifier) -> dict:
    return {
        "classifier": "ann_deep",
        "feature_names": list(FEATURE_NAMES),
        "weights": [matrix.tolist() for matrix in model.weights],
        "biases": [bias.tolist() for bias in model.biases],
        "threshold": model.threshold,
    }


def load_model(path: Path) -> DeepANNClassifier:
    saved = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(saved, dict)
        or saved.get("classifier") != "ann_deep"
        or saved.get("feature_names") != list(FEATURE_NAMES)
    ):
        raise ValueError("Expected a deep ANN with Sentry's feature order")
    return DeepANNClassifier(saved["weights"], saved["biases"], threshold=saved["threshold"])
