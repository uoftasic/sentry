from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class RewriteTracker(FeatureTracker):
    """Tracks writes to recently read LBA regions using rotating bitmaps."""

    def __init__(
        self,
        max_lba: int,
        num_regions: int = 32,
        rotation_events: int = 32,
    ) -> None:
        """TODO(Task 5): initialize region mapping, bitmaps, and counters."""
        raise NotImplementedError

    def update(self, event: Event) -> None:
        """TODO(Task 5): record reads, detect matching writes, rotate bitmaps."""
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO(Task 5): return read-then-write count and fraction."""
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO(Task 5): reset window counters.

        Decide carefully whether the rotating read-history bitmaps should
        survive a feature-window boundary.
        """
        raise NotImplementedError
