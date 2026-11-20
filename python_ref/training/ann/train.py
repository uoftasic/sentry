"""Train a small one-hidden-layer neural network on Sentry feature CSVs."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from sentry.classifiers import ANNClassifier

from ..dataset import read_dataset
from ..metrics import print_evaluation
from .model import model_payload, predict_dataset


def to_reference_model(
    network: MLPClassifier, scaler: StandardScaler, threshold: float
) -> ANNClassifier:
    # Fold feature centering and scaling into the first layer's weights
    # and biases so a saved model can score the original feature values.
    input_weights = network.coefs_[0] / scaler.scale_[:, None]
    input_biases = network.intercepts_[0] - scaler.mean_ @ input_weights
    return ANNClassifier(
        hidden_weights=input_weights.T,
        hidden_biases=input_biases,
        output_weights=network.coefs_[1][:, 0],
        output_bias=network.intercepts_[1][0],
        threshold=threshold,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path, help="Training feature CSV")
    parser.add_argument("--test", type=Path, help="Optional held-out feature CSV")
    parser.add_argument("--output", type=Path, default=Path("build/ann.json"),
                        help="New model JSON (default: build/ann.json)")
    parser.add_argument("--hidden-units", type=int, default=4,
                        help="Width of the single hidden layer (default: 4)")
    parser.add_argument("--epochs", type=int, default=12, help="Training passes (default: 12)")
    parser.add_argument("--batch-size", type=int, default=512,
                        help="Training windows per optimizer update (default: 512)")
    parser.add_argument("--learning-rate", type=float, default=0.001,
                        help="Adam learning rate (default: 0.001)")
    parser.add_argument("--l2", type=float, default=0.0001,
                        help="L2 weight penalty during training (default: 0.0001)")
    parser.add_argument("--threshold", type=float, default=0.0,
                        help="Decision threshold on the raw score (default: 0.0)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    if min(args.hidden_units, args.epochs, args.batch_size) < 1:
        parser.error("--hidden-units, --epochs and --batch-size must be positive")
    if not isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("--learning-rate must be finite and positive")
    if not isfinite(args.l2) or args.l2 < 0:
        parser.error("--l2 must be finite and nonnegative")
    if not isfinite(args.threshold):
        parser.error("--threshold must be finite")
    if not 0 <= args.seed < 2**32:
        parser.error("--seed must be between 0 and 4294967295")
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    if args.test and args.test.resolve() == args.train.resolve():
        parser.error("Use a separate file for --test")

    try:
        features, labels = read_dataset(args.train)
        if len(np.unique(labels)) != 2:
            raise ValueError("The training CSV must contain both run labels, 0 and 1")

        # The trainer sees features on a similar scale, even when the original
        # measurements range from fractions to large disk addresses.
        scaler = StandardScaler()
        scaled_features = np.ascontiguousarray(scaler.fit_transform(features))
        network = MLPClassifier(
            hidden_layer_sizes=(args.hidden_units,),
            activation="relu",
            solver="adam",
            alpha=args.l2,
            batch_size=args.batch_size,
            learning_rate_init=args.learning_rate,
            random_state=np.random.RandomState(args.seed),
        )

        training_accuracy = []
        for epoch in range(1, args.epochs + 1):
            # Each pass keeps the weights learned during the previous passes.
            network.partial_fit(scaled_features, labels, classes=[0, 1])
            model = to_reference_model(network, scaler, args.threshold)
            predictions = predict_dataset(model, features)
            accuracy = float(np.mean(predictions == labels))
            training_accuracy.append(accuracy)
            print(f"Epoch {epoch:2}/{args.epochs}  training accuracy {accuracy:.2%}", flush=True)

        result = model_payload(model)
        result["training_parameters"] = {
            "hidden_units": args.hidden_units,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "l2": args.l2,
            "seed": args.seed,
        }
        result["training_accuracy_by_epoch"] = training_accuracy
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

    parameter_count = args.hidden_units * (model.num_features + 2) + 1
    print(f"Saved {args.hidden_units} hidden units and {parameter_count} learned parameters to {args.output}")


if __name__ == "__main__":
    main()
