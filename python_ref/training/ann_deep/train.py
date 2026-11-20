"""Train a four-hidden-layer neural network on Sentry feature CSVs."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from ..dataset import read_dataset
from ..metrics import print_evaluation
from .model import HIDDEN_LAYERS, DeepANNClassifier, model_payload


def to_reference_model(
    network: MLPClassifier, scaler: StandardScaler, threshold: float
) -> DeepANNClassifier:
    # Fold the scaler into layer one so the saved network can read raw feature values.
    weights = [matrix.copy() for matrix in network.coefs_]
    biases = [bias.copy() for bias in network.intercepts_]
    weights[0] /= scaler.scale_[:, None]
    biases[0] -= scaler.mean_ @ weights[0]
    return DeepANNClassifier(weights, biases, threshold)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path, help="Training feature CSV")
    parser.add_argument("--validation", type=Path,
                        help="Optional validation CSV used to pick the best epoch")
    parser.add_argument("--test", type=Path, help="Optional held-out feature CSV")
    parser.add_argument("--output", type=Path, default=Path("build/ann-deep.json"),
                        help="New model JSON (default: build/ann-deep.json)")
    parser.add_argument("--hidden-units", type=int, nargs=HIDDEN_LAYERS, default=(32, 16, 8, 4),
                        metavar="N", help="Four hidden layer widths (default: 32 16 8 4)")
    parser.add_argument("--epochs", type=int, default=24, help="Training passes (default: 24)")
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

    if min(*args.hidden_units, args.epochs, args.batch_size) < 1:
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
    inputs = [path.resolve() for path in (args.train, args.validation, args.test) if path is not None]
    if len(set(inputs)) != len(inputs):
        parser.error("Use separate files for training, validation, and test")

    try:
        features, labels = read_dataset(args.train)
        if len(np.unique(labels)) != 2:
            raise ValueError("The training CSV must contain both run labels, 0 and 1")

        validation = read_dataset(args.validation) if args.validation else None
        # Only training windows determine the feature scales and learned weights.
        scaler = StandardScaler()
        scaled_features = np.ascontiguousarray(scaler.fit_transform(features))
        network = MLPClassifier(
            hidden_layer_sizes=tuple(args.hidden_units),
            activation="relu",
            solver="adam",
            alpha=args.l2,
            batch_size=args.batch_size,
            learning_rate_init=args.learning_rate,
            random_state=np.random.RandomState(args.seed),
        )

        training_accuracy = []
        validation_accuracy = []
        best_accuracy = -1.0
        for epoch in range(1, args.epochs + 1):
            network.partial_fit(scaled_features, labels, classes=[0, 1])
            model = to_reference_model(network, scaler, args.threshold)
            accuracy = float(np.mean(model.predict_dataset(features) == labels))
            training_accuracy.append(accuracy)
            message = f"Epoch {epoch:2}/{args.epochs}  training accuracy {accuracy:.2%}"

            if validation is None:
                selected_model, selected_epoch = model, epoch
            else:
                val_features, val_labels = validation
                val_accuracy = float(np.mean(model.predict_dataset(val_features) == val_labels))
                validation_accuracy.append(val_accuracy)
                message += f"  validation accuracy {val_accuracy:.2%}"
                # Use the earliest epoch at the highest validation accuracy.
                if val_accuracy > best_accuracy:
                    best_accuracy = val_accuracy
                    selected_model, selected_epoch = model, epoch

            print(message, flush=True)

        result = model_payload(selected_model)
        result["training_parameters"] = {
            "hidden_units": list(args.hidden_units),
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "l2": args.l2,
            "seed": args.seed,
        }
        result["selected_epoch"] = selected_epoch
        result["training_accuracy_by_epoch"] = training_accuracy
        if validation is not None:
            result["validation_accuracy_by_epoch"] = validation_accuracy

        if args.test:
            # Test windows are read only after model selection is complete.
            test_features, test_labels = read_dataset(args.test)
            predictions = selected_model.predict_dataset(test_features)
            result["test_accuracy"] = float(np.mean(predictions == test_labels))
            print_evaluation(test_labels, predictions)

        output = json.dumps(result, indent=2, allow_nan=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            file.write(output + "\n")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

    print(f"Saved epoch {selected_epoch} with {selected_model.parameter_count:,} learned parameters to {args.output}")


if __name__ == "__main__":
    main()
