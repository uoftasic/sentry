from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class LBATracker(FeatureTracker):
    """Tracks LBA variance and an LBA-region histogram."""

    def __init__(
        self,
        max_lba: int,
        num_regions: int = 32,
    ) -> None:
        """TODO(Task 4): save configuration and initialize LBA state."""
        raise NotImplementedError

    def update(self, event: Event) -> None:
        """TODO(Task 4): update variance accumulators and region histogram."""
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO(Task 4): return LBA variance and regions-touched values."""
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO(Task 4): clear per-window LBA state."""
        raise NotImplementedError
