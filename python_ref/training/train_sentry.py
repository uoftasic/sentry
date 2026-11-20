"""Train Sentry's 16-feature weighted-sum classifier from exported CSVs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler

from export_ransmap import FEATURE_NAMES


def read_dataset(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read the features in Sentry's order, followed by the run label."""
    names = (*FEATURE_NAMES, "run_label")
    with path.open(newline="", encoding="utf-8-sig") as file:
        header = next(csv.reader(file), [])
        missing = [name for name in names if header.count(name) != 1]
        if missing:
            raise ValueError(f"{path}: expected one column for each of {', '.join(missing)}")
        # Use column names to keep features aligned if the CSV columns move.
        columns = [header.index(name) for name in names]
        rows = np.loadtxt(file, delimiter=",", usecols=columns, ndmin=2, comments=None, quotechar='"')

    if not rows.size or not np.isfinite(rows).all():
        raise ValueError(f"{path}: expected at least one row with finite numeric values")
    labels = rows[:, -1]
    if not np.isin(labels, (0, 1)).all():
        raise ValueError(f"{path}: run_label must be 0 or 1")
    return rows[:, :-1], labels.astype(int)


def train_model(features: np.ndarray, labels: np.ndarray, epochs: int) -> dict:
    classes = np.array([0, 1])
    if not np.array_equal(np.unique(labels), classes):
        raise ValueError("The training CSV must contain both run labels, 0 and 1")

    # Put small ratios and large measurements on a similar scale for training.
    scaler = StandardScaler()
    scaled_features = np.ascontiguousarray(scaler.fit_transform(features))
    model = SGDClassifier(
        loss="log_loss",
        average=True,
        random_state=np.random.RandomState(42),
    )

    training_accuracy = []
    for epoch in range(1, epochs + 1):
        # Each pass continues from the previous epoch's weights.
        model.partial_fit(scaled_features, labels, classes=classes)
        accuracy = float(model.score(scaled_features, labels))
        training_accuracy.append(accuracy)
        print(f"Epoch {epoch:2}/{epochs}  training accuracy {accuracy:.2%}", flush=True)

    # Fold scaling into the weights and bias so Sentry can score raw features.
    weights = model.coef_[0] / scaler.scale_
    bias = float(model.intercept_[0] - weights @ scaler.mean_)
    return {
        "feature_names": list(FEATURE_NAMES),
        "weights": weights.tolist(),
        "bias": bias,
        # A score strictly above this cutoff predicts label 1.
        "threshold": 0.0,
        "training_accuracy_by_epoch": training_accuracy,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path, help="Training feature CSV")
    parser.add_argument("--test", type=Path, help="Optional held-out feature CSV")
    parser.add_argument("--epochs", type=int, default=10, help="Passes over the training data (default: 10)")
    parser.add_argument("--output", type=Path, default=Path("weights.json"), help="New JSON file for the learned weights")
    args = parser.parse_args()

    if args.epochs < 1:
        parser.error("--epochs must be at least 1")
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    if args.test and args.test.resolve() == args.train.resolve():
        parser.error("Use a separate file for --test")

    try:
        train_features, train_labels = read_dataset(args.train)
        result = train_model(train_features, train_labels, args.epochs)

        if args.test:
            test_features, test_labels = read_dataset(args.test)
            # Multiply matching features and weights, sum them, and add the bias.
            scores = test_features @ np.array(result["weights"]) + result["bias"]
            test_accuracy = float(np.mean((scores > result["threshold"]) == test_labels))
            result["test_accuracy"] = test_accuracy
            print(f"Test accuracy {test_accuracy:.2%}")

        output = json.dumps(result, indent=2, allow_nan=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            file.write(output + "\n")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

    print(f"Saved {len(FEATURE_NAMES)} weights and bias to {args.output}")


if __name__ == "__main__":
    main()
