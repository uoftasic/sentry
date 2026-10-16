from __future__ import annotations


class WeightedSumClassifier:
    """Generic weighted-sum classifier.

    This class must only see an ordered numeric feature vector. It must not
    contain feature-specific logic.
    """

    def __init__(
        self,
        weights: list[float],
        bias: float = 0.0,
        threshold: float = 0.0,
    ) -> None:
        """TODO(Task 9): store and validate classifier parameters."""
        raise NotImplementedError

    def score(self, feature_vector: list[float]) -> float:
        """TODO(Task 9): return bias + sum(weight * feature)."""
        raise NotImplementedError

    def predict(self, feature_vector: list[float]) -> bool:
        """TODO(Task 9): compare score against the configured threshold."""
        raise NotImplementedError

class DecisionTreeClassifier:
    """Needs more research"""

    def __init__(
        self,
    ) -> None:
        """TODO(Task 9): store and validate the decision tree."""
        raise NotImplementedError

    def predict(self, feature_vector: list[float]) -> bool:
        """TODO(Task 9): traverse the tree to return a prediction."""
        raise NotImplementedError

class ANNClassifier:
    """Needs more research"""

    def __init__(
        self,
    ) -> None:
        """TODO"""
        raise NotImplementedError

    def predict(self, feature_vector: list[float]) -> bool:
        """TODO"""
        raise NotImplementedError
