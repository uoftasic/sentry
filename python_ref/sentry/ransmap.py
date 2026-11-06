from __future__ import annotations
from dataclasses import dataclass

from pathlib import Path

from .event import Event

@dataclass
class ransmap_row:
    timestamp_s: int
    time_ns: int
    lba: int
    size: int # number of lba blocks
    entropy: float | None = None

def load_ransmap(
    read_csv: str | Path,
    write_csv: str | Path,
    logical_block_size_bytes: int = 512,
) -> list[Event]:
    """Load and chronologically merge one RanSMAP read/write trace pair.

    TODO(Task 1): implement exactly as described in TASKS.md.
    """
    # process read_csv -> list[ransmap_row] with just reads
    list_of_row_reads = process_csv(read_csv)
    # process write_csv -> list[ransmap_row] with just writes
    list_of_row_writes = process_csv(write_csv)

    # interlace into one list[Event] based on Event.timestamp_ns, in increasing order
    list_of_events = interlace_reads_and_writes(list_of_row_writes, list_of_row_reads, logical_block_size_bytes)
    
    return list_of_events

def process_csv(
    csv: str | Path
) -> list[ransmap_row]:
    pass

def interlace_reads_and_writes(
    list_of_row_writes: list[ransmap_row],
    list_of_row_reads: list[ransmap_row],
    logical_block_size_bytes: int
) -> list[Event]:
    pass

