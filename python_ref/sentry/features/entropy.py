from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class EntropyTracker(FeatureTracker):
    """Tracks statistics of the supplied per-write entropy values."""

    def __init__(self) -> None:
        """TODO(Task 3): initialize entropy accumulators."""
        raise NotImplementedError

    def update(self, event: Event) -> None:
        """TODO(Task 3): consume entropy from valid write events."""
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO(Task 3): return mean and variance of write entropy."""
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO(Task 3): clear per-window entropy state."""
        raise NotImplementedError
