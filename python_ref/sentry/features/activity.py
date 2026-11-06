from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class ActivityTracker(FeatureTracker):
    """Tracks write/read activity and window timing."""

    def __init__(self) -> None:
        """TODO(Task 2): initialize counters and timestamps."""
        self.reset_window()

    def update(self, event: Event) -> None:
        """TODO(Task 2): update activity state from one event."""
        self._n_events += 1

        if event.op.name == "WRITE":
            self._n_writes += 1
            self._bytes_written += event.size_bytes
        elif event.op.name == "READ":
            self._bytes_read += event.size_bytes

        if self._first_ts_ns is None:
            self._first_ts_ns = event.timestamp_ns
        self._last_ts_ns = event.timestamp_ns

    def features(self) -> dict[str, int | float]:
        """TODO(Task 2): return the activity features from TASKS.md."""
        if self._first_ts_ns is None or self._last_ts_ns is None:
            window_time_ns = 0
        else:
            window_time_ns = self._last_ts_ns - self._first_ts_ns

        write_fraction = (
            self._n_writes / self._n_events if self._n_events else 0.0
        )

        return {
            "num_writes": self._n_writes,
            "write_fraction": write_fraction,
            "bytes_written": self._bytes_written,
            "bytes_read": self._bytes_read,
            "window_time_ns": window_time_ns,
        }

    def reset_window(self) -> None:
        """TODO(Task 2): clear per-window activity state."""
        self._n_events = 0
        self._n_writes = 0
        self._bytes_written = 0
        self._bytes_read = 0
        self._first_ts_ns = None
        self._last_ts_ns = None