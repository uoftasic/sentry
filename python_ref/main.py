from __future__ import annotations

import argparse

from sentry.classifier import WeightedSumClassifier
from sentry.features.activity import ActivityTracker
from sentry.features.entropy import EntropyTracker
from sentry.features.lba import LBATracker
from sentry.features.patterns import PatternTracker
from sentry.features.request_size import RequestSizeTracker
from sentry.features.rewrite import RewriteTracker
from sentry.ransmap import load_ransmap
from sentry.window import WindowController


WINDOW_SIZE = 64
NUM_LBA_REGIONS = 32


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reads", help="Path to ata_read.csv")
    parser.add_argument("writes", help="Path to ata_write.csv")
    parser.add_argument(
        "--max-lba",
        type=int,
        required=True,
        help="Exclusive upper bound of the usable LBA range",
    )
    args = parser.parse_args()

    events = load_ransmap(args.reads, args.writes)

    trackers = [
        ActivityTracker(),
        EntropyTracker(),
        LBATracker(args.max_lba, NUM_LBA_REGIONS),
        RewriteTracker(args.max_lba, NUM_LBA_REGIONS),
        PatternTracker(),
        RequestSizeTracker(),
    ]

    controller = WindowController(
        trackers=trackers,
        window_size=WINDOW_SIZE,
    )

    # TODO(Task 10):
    # Decide the final ordered feature names after the tracker tasks are merged.
    feature_names: list[str] = []

    # TODO(Task 10):
    # Supply one weight per feature after feature_names is finalized.
    classifier = WeightedSumClassifier(
        weights=[],
        bias=0.0,
        threshold=0.0,
    )

    for event in events:
        result = controller.update(event)

        if result is None:
            continue

        feature_vector = [
            float(result.features[name])
            for name in feature_names
        ]

        score = classifier.score(feature_vector)
        prediction = classifier.predict(feature_vector)

        print(f"Window {result.window_index}")
        print(f"Features: {result.features}")
        print(f"Score: {score}")
        print(f"Suspicious: {prediction}")
        print()


if __name__ == "__main__":
    main()
