from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class LBATracker(FeatureTracker):
    """Tracks LBA variance and an LBA-region histogram."""

    def __init__(
        self,
        max_lba: int,
        num_regions: int = 32,
        condition = None # bool = foo(Event), to filter events 
    ) -> None:
        if num_regions < 1:
            raise ValueError("num_regions must be positive")
        if max_lba < 1:
            raise ValueError("max_lba must be positive")
        if num_regions > max_lba:
            raise ValueError("max_lba must not be less than num_regions")
        if max_lba % num_regions != 0:
            raise ValueError("max_lba must be divisible by num_regions")

        # for calculating variance
        self.list_lba = []
        self.num_events = 0
        self.true_variance = 0
        self.histogram_approximated_variance

        # histogram
        self.LBA_histogram = [0] * num_regions
        self.region_width = max_lba // num_regions
        self.max_lba = max_lba

        # number of regions touched
        self.num_nonzero_regions = 0

        # only track LBA if event meets a specified condition
        # always track LBA if no condition is specified
        if condition is None:
            self.condition = lambda x: True
        else:
            self.condition = condition

    def update(self, event: Event) -> None:
        """TODO(Task 4): update variance accumulators and region histogram."""
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO(Task 4): return LBA variance and regions-touched values."""
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO(Task 4): clear per-window LBA state."""
        raise NotImplementedError
