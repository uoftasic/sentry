from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class RequestSizeTracker(FeatureTracker):
    """Tracks total and average request size."""

    def __init__(self) -> None:
        """TODO(Task 7): initialize request-size accumulators."""
        raise NotImplementedError

    def update(self, event: Event) -> None:
        """TODO(Task 7): accumulate request sizes."""
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO(Task 7): return total and average request size."""
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO(Task 7): clear per-window request-size state."""
        raise NotImplementedError
