"""Evaluate a saved Tsetlin model on a labelled feature CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..dataset import read_dataset
from ..metrics import print_evaluation
from .model import load_model, predict_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test", type=Path, help="Held-out feature CSV")
    parser.add_argument("--model", type=Path, default=Path("build/tsetlin.json"),
                        help="Saved model JSON (default: build/tsetlin.json)")
    args = parser.parse_args()

    try:
        model = load_model(args.model)
        features, labels = read_dataset(args.test)
        predictions = predict_dataset(model, features)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"{exc}\n")

    print_evaluation(labels, predictions)


if __name__ == "__main__":
    main()
