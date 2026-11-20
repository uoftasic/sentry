"""Train a boosted tree ensemble for Sentry's reference decision-tree classifier."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path

import lightgbm as lgb
import numpy as np

from sentry.classifiers import DecisionTreeClassifier

from ..dataset import read_dataset
from ..metrics import print_evaluation
from .model import model_payload, predict_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path, help="Training feature CSV")
    parser.add_argument("--test", type=Path, help="Optional held-out feature CSV")
    parser.add_argument("--output", type=Path, default=Path("build/decision-tree.json"),
                        help="New model JSON (default: build/decision-tree.json)")
    parser.add_argument("--trees", type=int, default=64, help="Boosting rounds (default: 64)")
    parser.add_argument("--max-depth", type=int, default=4, help="Maximum tree depth (default: 4)")
    parser.add_argument("--min-leaf-rows", type=int, default=100,
                        help="Target minimum rows in a leaf (default: 100)")
    parser.add_argument("--learning-rate", type=float, default=0.1,
                        help="How much each new tree changes the score (default: 0.1)")
    parser.add_argument("--threshold", type=float, default=0.0,
                        help="Decision threshold on the raw score (default: 0.0)")
    parser.add_argument("--threads", type=int, default=4, help="Training threads (default: 4)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    if min(args.trees, args.max_depth, args.min_leaf_rows, args.threads) < 1:
        parser.error("--trees, --max-depth, --min-leaf-rows and --threads must be positive")
    if not isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("--learning-rate must be finite and positive")
    if not isfinite(args.threshold) or args.seed < 0:
        parser.error("--threshold must be finite and --seed must be nonnegative")
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    if args.test and args.test.resolve() == args.train.resolve():
        parser.error("Use a separate file for --test")

    parameters = {
        "objective": "binary",
        "max_depth": args.max_depth,
        "min_data_in_leaf": args.min_leaf_rows,
        "learning_rate": args.learning_rate,
        "num_threads": args.threads,
        "seed": args.seed,
        "deterministic": True,
        "force_col_wise": True,
        # Zero is a real measurement. Sentry's trees branch on numeric cutoffs.
        "use_missing": False,
        "zero_as_missing": False,
        "verbosity": -1,
    }
    try:
        # Each training window supplies 16 measurements and its run's label.
        train_features, train_labels = read_dataset(args.train)
        if len(np.unique(train_labels)) != 2:
            raise ValueError("The training CSV must contain both run labels, 0 and 1")

        print(f"Training up to {args.trees} trees on {len(train_labels):,} windows", flush=True)
        # Boosting builds one tree at a time to improve the group's predictions.
        training_data = lgb.Dataset(train_features, label=train_labels)
        booster = lgb.train(parameters, training_data, num_boost_round=args.trees)
        model = DecisionTreeClassifier.from_lightgbm(booster, threshold=args.threshold)

        # Save the questions and leaf scores that the reference model uses.
        result = model_payload(model)
        result["training_parameters"] = {"num_boost_round": args.trees, **parameters}
        train_predictions = predict_dataset(model, train_features)
        result["training_accuracy"] = float(np.mean(train_predictions == train_labels))
        print(f"Training accuracy: {result['training_accuracy']:.2%}", flush=True)

        if args.test:
            # These windows are held out until the trees are finished.
            test_features, test_labels = read_dataset(args.test)
            predictions = predict_dataset(model, test_features)
            result["test_accuracy"] = float(np.mean(predictions == test_labels))
            print_evaluation(test_labels, predictions)

        output = json.dumps(result, indent=2, allow_nan=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            file.write(output + "\n")
    except (OSError, ValueError, lgb.basic.LightGBMError) as exc:
        parser.exit(1, f"{exc}\n")

    print(f"Saved {len(model.forest)} trees to {args.output}")


if __name__ == "__main__":
    main()
