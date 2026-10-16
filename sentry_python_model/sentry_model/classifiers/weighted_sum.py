from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WeightedSumClassifier:
    """Generic linear scorer that only sees an ordered feature vector."""

    weights: list[float]
    bias: float = 0.0
    threshold: float = 0.0

    def score(self, vector: list[float]) -> float:
        if len(vector) != len(self.weights):
            raise ValueError(
                f"expected {len(self.weights)} features, got {len(vector)}"
            )

        return self.bias + sum(
            weight * value
            for weight, value in zip(self.weights, vector, strict=True)
        )

    def predict(self, vector: list[float]) -> bool:
        return self.score(vector) >= self.threshold
