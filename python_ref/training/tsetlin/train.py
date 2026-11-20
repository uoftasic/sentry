"""Train the reference Tsetlin classifier on Sentry feature CSVs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from sentry.classifiers import TsetlinClassifier

from ..dataset import FEATURE_NAMES, read_dataset
from ..metrics import print_evaluation
from .model import predict_dataset


def fit_cutoffs(features: np.ndarray, count: int) -> list[list[float]]:
    """Choose thermometer cutoffs from the training feature distributions."""
    quantiles = np.arange(1, count + 1) / (count + 1)
    cutoffs = []
    for column in features.T:
        values = np.unique(column)
        candidates = np.quantile(column, quantiles, method="inverted_cdf")
        # With a strict > comparison, use the next lower value if a quantile
        # lands at the maximum. Keep one cutoff even for a constant feature.
        candidates = np.minimum(candidates, values[max(0, len(values) - 2)])
        cutoffs.append(np.unique(candidates).tolist())
    return cutoffs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path, help="Training feature CSV")
    parser.add_argument("--test", type=Path, help="Optional held-out feature CSV")
    parser.add_argument("--output", type=Path, default=Path("build/tsetlin.json"),
                        help="New model JSON (default: build/tsetlin.json)")
    parser.add_argument("--epochs", type=int, default=3, help="Training passes (default: 3)")
    parser.add_argument("--cutoffs", type=int, default=3,
                        help="Quantile cutoffs per feature before deduplication (default: 3)")
    parser.add_argument("--clauses", type=int, default=8, help="Even clause count (default: 8)")
    parser.add_argument("--vote-margin", type=int, default=4, help="Training vote margin (default: 4)")
    parser.add_argument("--specificity", type=int, default=3, help="Clause specificity (default: 3)")
    parser.add_argument("--state-bits", type=int, default=4, help="Counter width in bits (default: 4)")
    parser.add_argument("--threshold", type=int, default=0, help="Decision threshold (default: 0)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    if args.epochs < 1 or args.cutoffs < 1:
        parser.error("--epochs and --cutoffs must both be at least 1")
    if args.seed < 0:
        parser.error("--seed must be nonnegative")
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    if args.test and args.test.resolve() == args.train.resolve():
        parser.error("Use a separate file for --test")

    parameters = {
        "num_clauses": args.clauses,
        "vote_margin": args.vote_margin,
        "specificity": args.specificity,
        "state_bits": args.state_bits,
        "threshold": args.threshold,
        "seed": args.seed,
    }
    try:
        train_features, train_labels = read_dataset(args.train)
        if len(np.unique(train_labels)) != 2:
            raise ValueError("The training CSV must contain both run labels, 0 and 1")

        cutoffs = fit_cutoffs(train_features, args.cutoffs)
        model = TsetlinClassifier(cutoffs, **parameters)
        rng = np.random.default_rng(args.seed)
        training_accuracy = []
        for epoch in range(1, args.epochs + 1):
            # The export groups rows by run. Shuffle before each online pass.
            for index in rng.permutation(len(train_labels)):
                model.update(train_features[index], bool(train_labels[index]))
            predictions = predict_dataset(model, train_features)
            accuracy = float(np.mean(predictions == train_labels))
            training_accuracy.append(accuracy)
            print(f"Epoch {epoch:2}/{args.epochs}  training accuracy {accuracy:.2%}", flush=True)

        result = {
            "classifier": "tsetlin",
            "feature_names": list(FEATURE_NAMES),
            "cutoffs": cutoffs,
            "parameters": parameters,
            "states": model.states,
            "training_accuracy_by_epoch": training_accuracy,
        }
        if args.test:
            test_features, test_labels = read_dataset(args.test)
            predictions = predict_dataset(model, test_features)
            result["test_accuracy"] = float(np.mean(predictions == test_labels))
            print_evaluation(test_labels, predictions)

        output = json.dumps(result, indent=2, allow_nan=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            file.write(output + "\n")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

    print(f"Saved {model.num_clauses} clauses to {args.output}")


if __name__ == "__main__":
    main()
