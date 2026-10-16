from __future__ import annotations

import argparse
import csv

from sentry_model.features import (
    ActivityTracker,
    EntropyTracker,
    LBATracker,
    OperationPatternTracker,
    RequestSizeTracker,
    RewriteTracker,
)
from sentry_model.pipeline import run_pipeline
from sentry_model.ransmap import load_ransmap
from sentry_model.window import WindowController


def build_controller(
    *,
    window_size: int,
    max_lba: int,
    lba_regions: int,
) -> WindowController:
    trackers = [
        ActivityTracker(),
        EntropyTracker(),
        LBATracker(
            max_lba_exclusive=max_lba,
            num_regions=lba_regions,
        ),
        RewriteTracker(
            max_lba_exclusive=max_lba,
            num_regions=lba_regions,
            rotation_events=max(1, window_size // 2),
        ),
        OperationPatternTracker(),
        RequestSizeTracker(),
    ]

    return WindowController(
        trackers=trackers,
        window_size=window_size,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reads", required=True)
    parser.add_argument("--writes", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--window-size", type=int, default=64)
    parser.add_argument("--max-lba", type=int, required=True)
    parser.add_argument("--lba-regions", type=int, default=32)
    parser.add_argument("--logical-block-size", type=int, default=512)
    args = parser.parse_args()

    events = load_ransmap(
        args.reads,
        args.writes,
        logical_block_size_bytes=args.logical_block_size,
    )

    controller = build_controller(
        window_size=args.window_size,
        max_lba=args.max_lba,
        lba_regions=args.lba_regions,
    )

    windows = run_pipeline(events, controller)

    if not windows:
        raise SystemExit(
            "trace did not contain enough events to complete one window"
        )

    fieldnames = [
        "window_index",
        "start_timestamp_ns",
        "end_timestamp_ns",
        *windows[0].features.keys(),
    ]

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for window in windows:
            writer.writerow(
                {
                    "window_index": window.window_index,
                    "start_timestamp_ns": window.start_timestamp_ns,
                    "end_timestamp_ns": window.end_timestamp_ns,
                    **window.features,
                }
            )


if __name__ == "__main__":
    main()
