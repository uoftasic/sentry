# Run from the python_ref directory:
#   python -m sentry.ransmap path/to/ata_read.csv path/to/ata_write.csv
# Add --show N to print more events, or --block-size BYTES for another block size.

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from .event import Event, Op


@dataclass(frozen=True, slots=True)
class ransmap_row:
    timestamp_s: int
    time_ns: int
    lba: int
    size: int  # bytes in the CSV
    entropy: float | None = None


def load_ransmap(
    read_csv: str | Path,
    write_csv: str | Path,
    logical_block_size_bytes: int = 512,
) -> list[Event]:
    """Load RanSMAP ATA reads and writes as chronological storage events."""
    if logical_block_size_bytes <= 0:
        raise ValueError("logical_block_size_bytes must be positive")

    reads = process_csv(read_csv)
    writes = process_csv(write_csv)
    return interlace_reads_and_writes(writes, reads, logical_block_size_bytes)


def process_csv(path: str | Path) -> list[ransmap_row]:
    """Read the six-column, headerless RanSMAP ATA CSV format."""
    rows: list[ransmap_row] = []
    with Path(path).open("r", newline="", encoding="utf-8-sig") as file:
        for fields in csv.reader(file):
            if not fields or all(not field.strip() for field in fields):
                continue
            if len(fields) != 6:
                raise ValueError(f"{path}: expected 6 columns, got {len(fields)}")

            try:
                timestamp_s = int(fields[0].strip())
                time_ns = int(fields[1].strip())
                lba = int(fields[2].strip())
                size = int(fields[3].strip())
                entropy_value = float(fields[4].strip())
            except ValueError as exc:
                raise ValueError(f"{path}: invalid numeric CSV row: {fields!r}") from exc

            if not 0 <= time_ns < 1_000_000_000:
                raise ValueError(f"{path}: nanosecond offset out of range: {time_ns}")
            if lba < 0 or size < 0:
                raise ValueError(f"{path}: LBA and size must be nonnegative")

            rows.append(
                ransmap_row(
                    timestamp_s=timestamp_s,
                    time_ns=time_ns,
                    lba=lba,
                    size=size,
                    entropy=None if entropy_value == -1 else entropy_value,
                )
            )
    return rows


def interlace_reads_and_writes(
    list_of_row_writes: list[ransmap_row],
    list_of_row_reads: list[ransmap_row],
    logical_block_size_bytes: int,
) -> list[Event]:
    """Convert both streams and sort by timestamp, keeping ties stable."""
    events: list[Event] = []
    for op, rows in ((Op.WRITE, list_of_row_writes), (Op.READ, list_of_row_reads)):
        for row in rows:
            if row.size % logical_block_size_bytes:
                raise ValueError(
                    f"request size {row.size} is not a multiple of "
                    f"logical block size {logical_block_size_bytes}"
                )
            events.append(
                Event(
                    op=op,
                    timestamp_ns=row.timestamp_s * 1_000_000_000 + row.time_ns,
                    lba=row.lba,
                    block_count=row.size // logical_block_size_bytes,
                    entropy=row.entropy if op == Op.WRITE else None,
                    logical_block_size_bytes=logical_block_size_bytes,
                )
            )
    events.sort(key=lambda event: event.timestamp_ns)
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a RanSMAP ATA trace pair")
    parser.add_argument("reads", type=Path, help="Path to ata_read.csv")
    parser.add_argument("writes", type=Path, help="Path to ata_write.csv")
    parser.add_argument(
        "--block-size",
        type=int,
        default=512,
        metavar="BYTES",
        help="Logical block size in bytes (default: 512)",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=10,
        metavar="N",
        help="Number of first events to print (default: 10)",
    )
    args = parser.parse_args()
    if args.show < 0:
        parser.error("--show must be nonnegative")

    try:
        events = load_ransmap(args.reads, args.writes, args.block_size)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    reads = sum(event.op == Op.READ for event in events)
    print(f"Parsed {len(events)} events: {reads} reads, {len(events) - reads} writes")
    for event in events[: args.show]:
        print(event)
    if len(events) > args.show:
        print(f"... {len(events) - args.show} more events")


if __name__ == "__main__":
    main()

