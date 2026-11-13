from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Op(IntEnum):
    READ = 0
    WRITE = 1
    DEALLOCATE = 2
    OTHER = 3


@dataclass(frozen=True, slots=True)
class Event:
    """Shared decoded event used by every feature tracker."""

    op: Op
    timestamp_ns: int
    lba: int
    block_count: int
    entropy: float | None = None
    data_sample: bytes | None = None
    logical_block_size_bytes: int = 512

    @property
    def size_bytes(self) -> int:
        return self.block_count * self.logical_block_size_bytes
