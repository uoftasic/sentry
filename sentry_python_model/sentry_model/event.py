from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Op(IntEnum):
    """Normalized operation type seen by Sentry after decoding."""

    READ = 0
    WRITE = 1
    DEALLOCATE = 2
    OTHER = 3


@dataclass(frozen=True, slots=True)
class Event:
    """One decoded storage event used by the Python reference model."""

    op: Op
    timestamp_ns: int
    lba: int
    block_count: int
    entropy: float | None = None
    logical_block_size_bytes: int = 512

    def __post_init__(self) -> None:
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if self.lba < 0:
            raise ValueError("lba must be non-negative")
        if self.block_count <= 0:
            raise ValueError("block_count must be positive")
        if self.logical_block_size_bytes <= 0:
            raise ValueError("logical_block_size_bytes must be positive")
        if self.entropy is not None and not (0.0 <= self.entropy <= 1.0):
            raise ValueError("entropy must be normalized to [0, 1]")

    @property
    def size_bytes(self) -> int:
        return self.block_count * self.logical_block_size_bytes

    @property
    def end_lba_exclusive(self) -> int:
        return self.lba + self.block_count
