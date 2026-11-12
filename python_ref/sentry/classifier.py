from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class Classifier(ABC):
    """Common interface for classifiers used by the Sentry pipeline."""

    @abstractmethod
    def score(self, feature_vector: Sequence[float]) -> float:
        """Return the model's raw score for an ordered feature vector."""

    @abstractmethod
    def predict(self, feature_vector: Sequence[float]) -> bool:
        """Return the model's boolean prediction for an ordered feature vector."""


def __getattr__(name: str):
    """Keep the old import path working during the package migration."""
    exported = {
        "DecisionTreeClassifier",
        "TreeNode",
        "TsetlinClassifier",
        "WeightedSumClassifier",
    }
    if name in exported:
        from .classifiers import (
            DecisionTreeClassifier,
            TsetlinClassifier,
            TreeNode,
            WeightedSumClassifier,
        )

        return {
            "DecisionTreeClassifier": DecisionTreeClassifier,
            "TreeNode": TreeNode,
            "TsetlinClassifier": TsetlinClassifier,
            "WeightedSumClassifier": WeightedSumClassifier,
        }[name]
    raise AttributeError(name)


__all__ = [
    "Classifier",
    "DecisionTreeClassifier",
    "TreeNode",
    "TsetlinClassifier",
    "WeightedSumClassifier",
]
