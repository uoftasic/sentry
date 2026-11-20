"""Export labeled RanSMAP ATA windows with the Sentry Python reference."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from zipfile import ZipFile


# Match the classifier input order in python_ref/main.py.
FEATURE_NAMES = (
    "num_writes",
    "write_fraction",
    "bytes_written",
    "bytes_read",
    "window_time_ns",
    "average_write_entropy",
    "write_entropy_variance",
    "lba_variance",
    "lba_histogram_variance",
    "lba_regions_touched",
    "read_then_write_count",
    "read_then_write_fraction",
    "read_write_transition_count",
    "max_consecutive_writes",
    "total_request_bytes",
    "avg_request_bytes",
)
METADATA = (
    "run_label", "workload", "run_id", "window_index", "window_start_ns", "window_end_ns"
)
LABELS = {
    "AESCrypt": 0, "Firefox": 0, "Idle": 0, "Office": 0, "SDelete": 0, "Zip": 0,
    "Conti": 1, "Darkside": 1, "LockBit": 1, "REvil": 1, "Ryuk": 1, "WannaCry": 1,
}


def trace_csv(run_dir: Path, name: str, scratch: Path) -> Path:
    """Return the CSV path, unpacking only the requested trace if needed."""
    csv_path = run_dir / f"{name}.csv"
    if csv_path.is_file():
        return csv_path

    with ZipFile(run_dir / f"{name}.zip") as archive:
        members = [entry for entry in archive.namelist() if PurePosixPath(entry).name == csv_path.name]
        if len(members) != 1:
            raise ValueError(f"Expected one {csv_path.name} inside {name}.zip")
        dest = scratch / csv_path.name
        with archive.open(members[0]) as source, dest.open("wb") as output:
            copyfileobj(source, output)
    return dest


def export(args: argparse.Namespace) -> None:
    ref_path = args.sentry.resolve() / "python_ref"
    if not (ref_path / "main.py").is_file():
        raise ValueError(f"Could not find Sentry's Python reference at {ref_path}")
    sys.path.insert(0, str(ref_path))
    from main import NUM_LBA_REGIONS, WINDOW_SIZE
    from sentry.features.activity import ActivityTracker
    from sentry.features.entropy import EntropyTracker
    from sentry.features.lba import LBATracker
    from sentry.features.patterns import PatternTracker
    from sentry.features.request_size import RequestSizeTracker
    from sentry.features.rewrite import RewriteTracker
    from sentry.ransmap import load_ransmap
    from sentry.window import WindowController

    if args.max_lba < NUM_LBA_REGIONS or args.max_lba % NUM_LBA_REGIONS:
        raise ValueError(f"--max-lba must be a positive multiple of {NUM_LBA_REGIONS}")

    dataset = args.dataset.resolve()
    train_setups = {(dataset / setup).resolve() for setup in args.train_setup}
    test_setup = (dataset / args.test_setup).resolve()
    if test_setup in train_setups:
        raise ValueError("The test setup must be separate from the training setups")
    runs = []
    for setup_dir in sorted(train_setups | {test_setup}):
        if not setup_dir.is_relative_to(dataset) or not setup_dir.is_dir():
            raise ValueError(f"Could not find setup: {setup_dir}")
        split = "test" if setup_dir == test_setup else "train"
        for workload in sorted(LABELS):
            for run_dir in sorted((setup_dir / workload).glob("*/")):
                if not run_dir.is_dir():
                    continue
                streams = [
                    any((run_dir / f"{name}.{ext}").is_file() for ext in ("csv", "zip"))
                    for name in ("ata_read", "ata_write")
                ]
                if all(streams):
                    runs.append((split, workload, run_dir))
                elif any(streams):
                    raise ValueError(f"Incomplete ATA trace pair: {run_dir}")

    out = args.output.resolve()
    if out.exists():
        raise FileExistsError(f"Choose a new output folder: {out} already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    window_counts = Counter()
    run_counts = Counter()
    total_events = unaligned_events = 0

    with TemporaryDirectory(prefix=".ransmap-export-", dir=out.parent) as staging:
        staging_path = Path(staging)
        deliverables = staging_path / "csv"
        deliverables.mkdir()
        with (deliverables / "train.csv").open("w", newline="", encoding="utf-8") as train, (
            deliverables / "test.csv"
        ).open("w", newline="", encoding="utf-8") as test:
            writers = {"train": csv.writer(train), "test": csv.writer(test)}
            for writer in writers.values():
                writer.writerow((*FEATURE_NAMES, *METADATA))

            for split, workload, run_dir in runs:
                run_id = run_dir.relative_to(dataset).as_posix()
                label = LABELS[workload]
                try:
                    with TemporaryDirectory(dir=staging_path) as scratch:
                        read_csv = trace_csv(run_dir, "ata_read", Path(scratch))
                        write_csv = trace_csv(run_dir, "ata_write", Path(scratch))
                        # Keep exact request sizes, including partial sectors.
                        # LBA stays unchanged and the tracker uses request starts.
                        events = load_ransmap(read_csv, write_csv, logical_block_size_bytes=1)
                except (OSError, ValueError) as exc:
                    raise ValueError(f"{run_id}: {exc}") from exc

                if len(events) < WINDOW_SIZE:
                    raise ValueError(f"{run_id}: too few events for a complete window")
                if max(event.lba for event in events) >= args.max_lba:
                    raise ValueError(f"{run_id}: an LBA exceeds the configured drive range")

                total_events += len(events)
                unaligned_events += sum(event.size_bytes % 512 != 0 for event in events)
                start_ns = events[0].timestamp_ns
                controller = WindowController(
                    trackers=[
                        ActivityTracker(), EntropyTracker(),
                        LBATracker(args.max_lba, NUM_LBA_REGIONS),
                        RewriteTracker(args.max_lba, NUM_LBA_REGIONS),
                        PatternTracker(), RequestSizeTracker(),
                    ],
                    window_size=WINDOW_SIZE,
                )
                windows = 0
                for event in events:
                    result = controller.update(event)
                    if result is None:
                        continue
                    features = [result.features[name] for name in FEATURE_NAMES]
                    if not all(math.isfinite(value) for value in features):
                        raise ValueError(f"{run_id}: non-finite features in window {result.window_index}")
                    first = events[result.window_index * WINDOW_SIZE]
                    writers[split].writerow((
                        *features, label, workload, run_id, result.window_index,
                        first.timestamp_ns - start_ns, event.timestamp_ns - start_ns,
                    ))
                    windows += 1
                window_counts[split, label] += windows
                run_counts[split, label] += 1
                print(f"{split:5} {label} {run_id}: {windows:,} windows", flush=True)

        for split in ("train", "test"):
            for label in (0, 1):
                if not window_counts[split, label]:
                    raise ValueError(f"The {split} split needs recordings for label {label}")
                print(f"{split} label {label}: {run_counts[split, label]} runs, "
                      f"{window_counts[split, label]:,} windows")
        deliverables.rename(out)

    print(f"Processed {total_events:,} events, including {unaligned_events:,} partial-sector sizes")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sentry", type=Path, required=True, help="Path to the Sentry checkout")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to RanSMAP's dataset directory")
    parser.add_argument("--output", type=Path, required=True, help="New directory for train.csv and test.csv")
    parser.add_argument("--train-setup", action="append", required=True, help="Setup path inside dataset, repeatable")
    parser.add_argument("--test-setup", required=True, help="Held-out setup path inside dataset")
    parser.add_argument("--max-lba", type=int, default=500_000_000, help="Exclusive LBA bound used for all runs")
    args = parser.parse_args()
    try:
        export(args)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
