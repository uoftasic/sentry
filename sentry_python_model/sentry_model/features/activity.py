from __future__ import annotations

from ..event import Event, Op
from ..tracker import FeatureTracker


class ActivityTracker(FeatureTracker):
    """Counts read/write activity within the current window."""

    def __init__(self) -> None:
        self.reset_window()

    def update(self, event: Event) -> None:
        self.event_count += 1

        if event.op == Op.WRITE:
            self.write_count += 1
            self.bytes_written += event.size_bytes
        elif event.op == Op.READ:
            self.read_count += 1
            self.bytes_read += event.size_bytes

    def features(self) -> dict[str, int | float]:
        write_fraction = (
            self.write_count / self.event_count
            if self.event_count
            else 0.0
        )

        return {
            "write_count": self.write_count,
            "write_fraction": write_fraction,
            "bytes_written": self.bytes_written,
            "bytes_read": self.bytes_read,
        }

    def reset_window(self) -> None:
        self.event_count = 0
        self.write_count = 0
        self.read_count = 0
        self.bytes_written = 0
        self.bytes_read = 0
