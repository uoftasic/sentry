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
        self.true_variance = 0.0
        self.histogram_approximated_variance = 0.0

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
        if event.lba < 0:
            raise ValueError("event lba must not be negative")
        if event.lba >= self.max_lba:
            raise ValueError("event lba must be less than LBATracker's max_lba")

        if self.condition(event):
            self.list_lba.append(event.lba)
            self.num_events += 1

            region_index = event.lba // self.region_width
            if self.LBA_histogram[region_index] == 0:
                self.num_nonzero_regions += 1
            self.LBA_histogram[region_index] += 1

    def features(self) -> dict[str, int | float]:
        """Return population variance and the number of occupied LBA regions.

        The histogram approximation treats each region as if its events were
        located at the midpoint of that region.
        """
        if self.num_events == 0:
            self.true_variance = 0.0
            self.histogram_approximated_variance = 0.0
        else:
            mean_lba = sum(self.list_lba) / self.num_events
            self.true_variance = sum(
                (lba - mean_lba) ** 2 for lba in self.list_lba
            ) / self.num_events

            midpoint_offset = (self.region_width - 1) / 2
            histogram_mean = sum(
                count * (index * self.region_width + midpoint_offset)
                for index, count in enumerate(self.LBA_histogram)
            ) / self.num_events
            self.histogram_approximated_variance = sum(
                count
                * (
                    index * self.region_width + midpoint_offset - histogram_mean
                ) ** 2
                for index, count in enumerate(self.LBA_histogram)
            ) / self.num_events

        return {
            "lba_variance": self.true_variance,
            "lba_histogram_variance": self.histogram_approximated_variance,
            "lba_regions_touched": self.num_nonzero_regions,
        }

    def reset_window(self) -> None:
        """TODO(Task 4): clear per-window LBA state."""
        raise NotImplementedError
