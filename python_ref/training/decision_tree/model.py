"""Save, load, and score the flat trees used by the reference classifier."""

from __future__ import annotations

import json
from dataclasses import asdict
from math import isfinite
from pathlib import Path

import numpy as np

from sentry.classifiers import DecisionTreeClassifier, TreeNode

from ..dataset import FEATURE_NAMES


def model_payload(model: DecisionTreeClassifier) -> dict:
    """Return the reference model as JSON-compatible values."""
    return {
        "classifier": "decision_tree",
        "feature_names": list(FEATURE_NAMES),
        "bias": model.bias,
        "threshold": model.threshold,
        # Each tree is a list. An internal node stores where to go for each answer.
        "forest": [[asdict(node) for node in tree] for tree in model.forest],
    }


def load_model(path: Path) -> DecisionTreeClassifier:
    saved = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(saved, dict)
        or saved.get("classifier") != "decision_tree"
        or saved.get("feature_names") != list(FEATURE_NAMES)
    ):
        raise ValueError("Expected a decision-tree model with Sentry's feature order")

    bias = float(saved["bias"])
    threshold = float(saved["threshold"])
    if not isfinite(bias) or not isfinite(threshold):
        raise ValueError("Expected a finite bias and decision threshold")

    forest = [[TreeNode(**node) for node in tree] for tree in saved["forest"]]
    for tree in forest:
        for index, node in enumerate(tree):
            if type(node.is_leaf) is not bool or not all(
                isfinite(value) for value in (node.threshold, node.value)
            ):
                raise ValueError("Expected a leaf flag and finite numeric values for each node")
            if node.is_leaf:
                continue
            # The importer puts parents before children. Moving forward at
            # every question guarantees that a window eventually reaches a leaf.
            if not (
                type(node.feature_idx) is int and 0 <= node.feature_idx < len(FEATURE_NAMES)
                and type(node.left) is int and index < node.left < len(tree)
                and type(node.right) is int and index < node.right < len(tree)
            ):
                raise ValueError("Expected a valid feature index and forward child indices")

    return DecisionTreeClassifier(forest, bias=bias, threshold=threshold)


def score_dataset(model: DecisionTreeClassifier, features: np.ndarray) -> np.ndarray:
    """Compute the reference raw margin for each row using the flat forest."""
    if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
        raise ValueError(f"Expected feature rows with {len(FEATURE_NAMES)} columns")

    scores = np.full(len(features), model.bias, dtype=float)
    all_rows = np.arange(len(features))
    for tree in model.forest:
        # Every window starts at the first question in each tree.
        pending = [(0, all_rows)]
        while pending:
            node_index, rows = pending.pop()
            if not rows.size:
                continue
            node = tree[node_index]
            if node.is_leaf:
                # A leaf gives each window that reached it a number to add.
                scores[rows] += node.value
                continue

            # Ask one yes-or-no question for every window at this node.
            goes_left = features[rows, node.feature_idx] <= node.threshold
            pending.append((node.left, rows[goes_left]))
            pending.append((node.right, rows[~goes_left]))
    return scores


def predict_dataset(model: DecisionTreeClassifier, features: np.ndarray) -> np.ndarray:
    # A window is flagged when its total reaches the decision threshold.
    return score_dataset(model, features) >= model.threshold
