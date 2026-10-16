from __future__ import annotations

from pathlib import Path

from .event import Event


def load_ransmap(
    read_csv: str | Path,
    write_csv: str | Path,
    logical_block_size_bytes: int = 512,
) -> list[Event]:
    """Load and chronologically merge one RanSMAP read/write trace pair.

    TODO(Task 1): implement exactly as described in TASKS.md.
    """
    raise NotImplementedError
