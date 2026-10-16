from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class PatternTracker(FeatureTracker):
    """Tracks read/write ordering within the event stream."""

    def __init__(self) -> None:
        """TODO(Task 6): initialize previous-operation and run-length state."""
        raise NotImplementedError

    def update(self, event: Event) -> None:
        """TODO(Task 6): update transition count and consecutive-write count."""
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO(Task 6): return transition count and max consecutive writes."""
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO(Task 6): clear per-window pattern state."""
        raise NotImplementedError
