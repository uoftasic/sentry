"""Evaluate saved Sentry weights on a labeled feature CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..dataset import FEATURE_NAMES, read_dataset
from ..metrics import print_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test", type=Path, help="Held-out feature CSV")
    parser.add_argument(
        "--weights", type=Path, default=Path("build/weights.json"),
        help="Saved model JSON (default: build/weights.json)",
    )
    args = parser.parse_args()

    try:
        model = json.loads(args.weights.read_text(encoding="utf-8"))
        if not isinstance(model, dict) or model.get("feature_names") != list(FEATURE_NAMES):
            raise ValueError("The saved feature order does not match Sentry's feature order")

        weights = np.asarray(model["weights"], dtype=float)
        bias = float(model["bias"])
        threshold = float(model["threshold"])
        if weights.shape != (len(FEATURE_NAMES),) or not np.isfinite(weights).all():
            raise ValueError("Expected 16 finite weights in the saved model")
        if not np.isfinite([bias, threshold]).all():
            raise ValueError("Expected a finite bias and threshold")

        features, labels = read_dataset(args.test)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"{exc}\n")

    # The exported weights already account for training-time feature scaling.
    scores = features @ weights + bias
    predictions = (scores > threshold).astype(int)
    print_evaluation(labels, predictions)


if __name__ == "__main__":
    main()
