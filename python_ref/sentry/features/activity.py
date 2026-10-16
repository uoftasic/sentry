from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class ActivityTracker(FeatureTracker):
    """Tracks write/read activity and window timing."""

    def __init__(self) -> None:
        """TODO(Task 2): initialize counters and timestamps."""
        raise NotImplementedError

    def update(self, event: Event) -> None:
        """TODO(Task 2): update activity state from one event."""
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO(Task 2): return the activity features from TASKS.md."""
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO(Task 2): clear per-window activity state."""
        raise NotImplementedError
