"""Saved state and batch inference for the reference Tsetlin classifier."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sentry.classifiers import TsetlinClassifier

from ..dataset import FEATURE_NAMES


def load_model(path: Path) -> TsetlinClassifier:
    saved = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(saved, dict)
        or saved.get("classifier") != "tsetlin"
        or saved.get("feature_names") != list(FEATURE_NAMES)
    ):
        raise ValueError("Expected a Tsetlin model with Sentry's feature order")

    model = TsetlinClassifier(saved["cutoffs"], **saved["parameters"])
    if model.num_features != len(FEATURE_NAMES) or not all(
        np.isfinite(cutoffs).all() for cutoffs in model.cutoffs
    ):
        raise ValueError("Expected finite cutoffs for each Sentry feature")

    states = np.asarray(saved["states"])
    if (
        states.shape != (model.num_clauses, model.num_literals)
        or states.dtype.kind not in "iu"
        or (states < 0).any()
        or (states >= 1 << model.state_bits).any()
    ):
        raise ValueError("Invalid Tsetlin automaton states")
    model.states = states.tolist()
    return model


def predict_dataset(model: TsetlinClassifier, features: np.ndarray) -> np.ndarray:
    """Evaluate the reference clause masks in batches for large feature CSVs."""
    if features.ndim != 2 or features.shape[1] != model.num_features:
        raise ValueError(f"Expected feature rows with {model.num_features} columns")

    clauses = [
        (1 if index % 2 == 0 else -1,
         [bit for bit in range(model.num_literals) if mask & (1 << bit)])
        for index, mask in enumerate(model.clause_masks)
        if mask
    ]
    predictions = np.empty(len(features), dtype=bool)
    for start in range(0, len(features), 16_384):
        rows = features[start:start + 16_384]
        bits = np.concatenate(
            [column[:, None] > cutoffs for column, cutoffs in zip(rows.T, model.cutoffs)],
            axis=1,
        )
        literals = np.concatenate((bits, ~bits), axis=1)
        votes = np.zeros(len(rows), dtype=int)
        for sign, included in clauses:
            votes += sign * np.all(literals[:, included], axis=1)
        predictions[start:start + len(rows)] = votes > model.threshold
    return predictions
