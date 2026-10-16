from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .event import Event, Op


@dataclass(frozen=True, slots=True)
class _RawRecord:
    timestamp_ns: int
    op: Op
    lba: int
    size_bytes: int
    entropy: float | None
    source_order: int


def _read_file(path: str | Path, op: Op) -> list[_RawRecord]:
    records: list[_RawRecord] = []

    with open(path, "r", newline="") as f:
        reader = csv.reader(f)

        for row_number, row in enumerate(reader):
            if not row:
                continue

            row = [field.strip() for field in row]
            if len(row) < 5:
                raise ValueError(
                    f"{path}:{row_number + 1}: expected at least 5 columns"
                )

            seconds = int(row[0])
            nanoseconds = int(row[1])
            lba = int(row[2])
            size_bytes = int(row[3])
            raw_entropy = float(row[4])

            entropy = None if raw_entropy < 0 else raw_entropy

            records.append(
                _RawRecord(
                    timestamp_ns=seconds * 1_000_000_000 + nanoseconds,
                    op=op,
                    lba=lba,
                    size_bytes=size_bytes,
                    entropy=entropy,
                    source_order=row_number,
                )
            )

    return records


def load_ransmap(
    read_csv: str | Path,
    write_csv: str | Path,
    logical_block_size_bytes: int = 512,
) -> list[Event]:
    """Merge RanSMAP read/write CSVs into one chronological event stream.

    Exact read-vs-write ordering is not available when the two files contain
    identical timestamps, so a deterministic tie-break is used.
    """
    if logical_block_size_bytes <= 0:
        raise ValueError("logical_block_size_bytes must be positive")

    raw = _read_file(read_csv, Op.READ) + _read_file(write_csv, Op.WRITE)

    raw.sort(
        key=lambda r: (
            r.timestamp_ns,
            int(r.op),
            r.source_order,
        )
    )

    events: list[Event] = []

    for record in raw:
        if record.size_bytes % logical_block_size_bytes != 0:
            raise ValueError(
                f"request size {record.size_bytes} is not divisible by "
                f"logical block size {logical_block_size_bytes}"
            )

        events.append(
            Event(
                op=record.op,
                timestamp_ns=record.timestamp_ns,
                lba=record.lba,
                block_count=record.size_bytes // logical_block_size_bytes,
                entropy=record.entropy,
                logical_block_size_bytes=logical_block_size_bytes,
            )
        )

    return events
