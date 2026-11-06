from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class RequestSizeTracker(FeatureTracker):
    """Tracks total and average request size."""

    def __init__(self) -> None:
        """Initialize request-size accumulators."""
        self.reset_window()

    def update(self, event: Event) -> None:
        """Accumulate request sizes."""
        self._n_events += 1
        self._total_bytes += event.size_bytes

    def features(self) -> dict[str, int | float]:
        """Return total and average request size."""
        avg_bytes = self._total_bytes // self._n_events if self._n_events else 0

        return {
            "total_request_bytes": self._total_bytes,
            "avg_request_bytes": avg_bytes,
        }

    def reset_window(self) -> None:
        """Clear per-window request-size state."""
        self._n_events = 0
        self._total_bytes = 0