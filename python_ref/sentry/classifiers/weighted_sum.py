from __future__ import annotations

from collections.abc import Sequence
from math import floor

from ..classifier import Classifier


def _quantize(value: float, fraction_bits: int) -> int:
    """Convert a real value to a signed fixed-point integer.

    Rounds half up (add half an LSB, then truncate), as RTL usually does.
    Python's round() would send halves to the even integer instead.
    """
    return floor(value * (1 << fraction_bits) + 0.5)


def _check_fraction_bits(fraction_bits: int | None) -> None:
    if fraction_bits is not None and not 0 <= fraction_bits <= 16:
        raise ValueError("fraction_bits must be None or between 0 and 16")


class WeightedSumClassifier(Classifier):
    """Generic weighted-sum classifier.

    This class must only see an ordered numeric feature vector. It must not
    contain feature-specific logic.

    score = bias + sum(weights[i] * feature_vector[i])
    predict = score > threshold

    In hardware this is one multiply-accumulate unit stepping through the
    feature vector, followed by one comparator. With ``fraction_bits`` set,
    weights, bias, threshold and features are rounded to fixed-point integers
    so the Python result matches an integer RTL datapath bit for bit.
    Products of two Q.f values have 2f fraction bits, so the bias and the
    threshold are aligned to that scale with a left shift, not a multiply.
    """

    def __init__(
        self,
        weights: list[float],
        bias: float = 0.0,
        threshold: float = 0.0,
        fraction_bits: int | None = None,
    ) -> None:
        if not weights:
            raise ValueError("weights must contain at least one value")
        _check_fraction_bits(fraction_bits)

        self.weights = [float(weight) for weight in weights]
        self.bias = float(bias)
        self.threshold = float(threshold)
        self.fraction_bits = fraction_bits

        if fraction_bits is not None:
            # These are the constants that would be stored in registers/ROM.
            self.quantized_weights = [
                _quantize(weight, fraction_bits) for weight in self.weights
            ]
            self.quantized_bias = _quantize(self.bias, fraction_bits)
            self.quantized_threshold = _quantize(self.threshold, fraction_bits)

    @property
    def num_features(self) -> int:
        return len(self.weights)

    def _check_vector(self, feature_vector: Sequence[float]) -> None:
        if len(feature_vector) != len(self.weights):
            raise ValueError(
                f"expected {len(self.weights)} features, "
                f"got {len(feature_vector)}"
            )

    def _accumulate(self, feature_vector: Sequence[float]) -> int:
        """Integer accumulator value at 2 * fraction_bits fraction bits."""
        fraction_bits = self.fraction_bits
        assert fraction_bits is not None
        accumulator = self.quantized_bias << fraction_bits
        for weight, feature in zip(self.quantized_weights, feature_vector):
            accumulator += weight * _quantize(feature, fraction_bits)
        return accumulator

    def score(self, feature_vector: Sequence[float]) -> float:
        """Return bias + sum(weight * feature)."""
        self._check_vector(feature_vector)
        if self.fraction_bits is None:
            return self.bias + sum(
                weight * feature
                for weight, feature in zip(self.weights, feature_vector)
            )
        return self._accumulate(feature_vector) / (1 << (2 * self.fraction_bits))

    def predict(self, feature_vector: Sequence[float]) -> bool:
        """Return True when the score is strictly above the threshold."""
        self._check_vector(feature_vector)
        if self.fraction_bits is None:
            return self.score(feature_vector) > self.threshold
        threshold = self.quantized_threshold << self.fraction_bits
        return self._accumulate(feature_vector) > threshold
