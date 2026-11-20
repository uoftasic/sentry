"""A small feed-forward classifier with one ReLU hidden layer."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

from ..classifier import Classifier


class ANNClassifier(Classifier):
    """Score features with one weighted sum per hidden unit and one output sum."""

    def __init__(
        self,
        hidden_weights: Sequence[Sequence[float]],
        hidden_biases: Sequence[float],
        output_weights: Sequence[float],
        output_bias: float,
        threshold: float = 0.0,
    ) -> None:
        self.hidden_weights = tuple(tuple(map(float, weights)) for weights in hidden_weights)
        self.hidden_biases = tuple(map(float, hidden_biases))
        self.output_weights = tuple(map(float, output_weights))
        self.output_bias = float(output_bias)
        self.threshold = float(threshold)

        width = len(self.hidden_weights)
        if width == 0 or width != len(self.hidden_biases) or width != len(self.output_weights):
            raise ValueError("Expected a matching hidden bias and output weight for each hidden unit")
        self.num_features = len(self.hidden_weights[0])
        if self.num_features == 0 or any(
            len(weights) != self.num_features for weights in self.hidden_weights
        ):
            raise ValueError("Expected the same nonzero number of inputs for each hidden unit")
        if not (
            all(isfinite(weight) for row in self.hidden_weights for weight in row)
            and all(isfinite(value) for value in self.hidden_biases + self.output_weights)
            and isfinite(self.output_bias)
            and isfinite(self.threshold)
        ):
            raise ValueError("ANN parameters must be finite")

    def score(self, feature_vector: Sequence[float]) -> float:
        if len(feature_vector) != self.num_features:
            raise ValueError(f"Expected {self.num_features} features, got {len(feature_vector)}")

        total = self.output_bias
        for weights, bias, output_weight in zip(
            self.hidden_weights, self.hidden_biases, self.output_weights
        ):
            # Each hidden unit adds up the inputs it cares about. A negative
            # result becomes zero, so that unit contributes nothing.
            activation = max(0.0, sum(w * x for w, x in zip(weights, feature_vector)) + bias)
            total += output_weight * activation
        return total

    def predict(self, feature_vector: Sequence[float]) -> bool:
        return self.score(feature_vector) > self.threshold
