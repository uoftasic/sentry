"""Evaluate saved Sentry weights on a labeled feature CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix

from export_ransmap import FEATURE_NAMES
from train_sentry import read_dataset


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
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    total_windows = matrix.sum()
    benign_total = tn + fp
    ransomware_total = fn + tp
    benign_rate = f"{fp / benign_total:.2%}" if benign_total else "n/a"
    ransomware_rate = f"{fn / ransomware_total:.2%}" if ransomware_total else "n/a"

    print(f"Test accuracy: {matrix.trace() / total_windows:.2%} ({total_windows:,} windows)")
    print()
    print("Confusion matrix (rows = actual, columns = predicted)")
    print(f"{'':28}{'Predicted 0':>14}{'Predicted 1':>14}{'Mispredict rate':>18}")
    print(f"{'Actual 0 (benign)':28}{tn:>14,}{fp:>14,}{benign_rate:>18}")
    print(f"{'Actual 1 (ransomware run)':28}{fn:>14,}{tp:>14,}{ransomware_rate:>18}")
    print(f"Overall mispredict rate: {(fp + fn) / total_windows:.2%}")


if __name__ == "__main__":
    main()
