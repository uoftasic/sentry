from __future__ import annotations

from ..event import Event, Op
from ..tracker import FeatureTracker


class LBATracker(FeatureTracker):
    """Tracks LBA variance and an LBA-region histogram."""

    def __init__(
        self,
        max_lba: int,
        num_regions: int = 32,
        condition = None, # bool = foo(Event), to filter events 
        expand_requests_to_blocks: bool = False 
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
        self.num_blocks = 0
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

        self.expand_requests_to_blocks = expand_requests_to_blocks

    def update(self, event: Event) -> None:
        if event.lba < 0:
            raise ValueError("event lba must not be negative")
        if event.lba >= self.max_lba:
            raise ValueError("event lba must be less than LBATracker's max_lba")

        if self.condition(event):
            # update counters
            self.num_blocks += event.block_count
            self.num_events += 1
            
            # update list of LBAs
            if self.expand_requests_to_blocks:
                for lba in range(event.lba, event.lba + event.block_count):
                    self.list_lba.append(lba)
            else:
                self.list_lba.append(event.lba)

            # update histogram
            if self.expand_requests_to_blocks:
                end_lba = event.lba + event.block_count  # Exclusive.
                first_region = event.lba // self.region_width
                last_region = (end_lba - 1) // self.region_width

                for region_index in range(first_region, last_region + 1):
                    region_start = region_index * self.region_width
                    region_end = region_start + self.region_width
                    blocks_in_region = min(end_lba, region_end) - max(
                        event.lba, region_start
                    )
                    if self.LBA_histogram[region_index] == 0:
                        self.num_nonzero_regions += 1
                    self.LBA_histogram[region_index] += blocks_in_region
            else:
                region_index = event.lba // self.region_width
                if self.LBA_histogram[region_index] == 0:
                    self.num_nonzero_regions += 1
                self.LBA_histogram[region_index] += 1

    def features(self) -> dict[str, int | float]:
        """Return population variance and the number of occupied LBA regions.

        The histogram approximation uses region indices, then scales their
        variance by the square of the region width.
        """
        if self.expand_requests_to_blocks:
            N = self.num_blocks
        else:
            N = self.num_events
        
        if N == 0:
            self.true_variance = 0.0
            self.histogram_approximated_variance = 0.0
        else:
            # calculate true variance
            mean_lba = sum(self.list_lba) / N
            self.true_variance = sum(
                (lba - mean_lba) ** 2 for lba in self.list_lba
            ) / N

            # calculate histogram approximated variance by assuming that:
            # 1. all LBAs in a region are at the lower bound of the region
            #   (translation of distribution does not affect variance)
            # 2. all regions have region_width of 1
            #   (stretching distribution by factor r increases variance by r^2)
            # then multiply that variance by a factor to account for assumption #2
            mean_region = sum(
                count * index
                for index, count in enumerate(self.LBA_histogram)
            ) / N
            region_variance = sum(
                count * (index - mean_region) ** 2
                for index, count in enumerate(self.LBA_histogram)
            ) / N
            self.histogram_approximated_variance = (
                region_variance * self.region_width**2
            )

        return {
            "lba_variance": self.true_variance,
            "lba_histogram_variance": self.histogram_approximated_variance,
            "lba_regions_touched": self.num_nonzero_regions,
        }

    def reset_window(self) -> None:
        """Clear measurements for the next window, keeping the configuration."""
        self.list_lba.clear()
        self.num_events = 0
        self.true_variance = 0.0
        self.histogram_approximated_variance = 0.0
        self.LBA_histogram[:] = [0] * len(self.LBA_histogram)
        self.num_nonzero_regions = 0


if __name__ == "__main__":
    print("LBATracker demo: usable LBAs 0-15, four regions of width four")
    print("Regions: 0=[0-3], 1=[4-7], 2=[8-11], 3=[12-15]")
    print("Only WRITE events are counted in these examples.")

    tracker = LBATracker(16, 4, condition=lambda event: event.op == Op.WRITE)

    def show_case(
        title: str,
        expected_histogram: list[int],
        expected_features: dict[str, int | float],
    ) -> None:
        result = tracker.features()
        print(f"\n{title}")
        print(f"  Tracked LBAs: {tracker.list_lba}")
        print(f"  Histogram (events per region): {tracker.LBA_histogram}")
        print(f"  Exact LBA variance: {result['lba_variance']}")
        print(f"  Histogram midpoint variance: {result['lba_histogram_variance']}")
        print(f"  Regions touched: {result['lba_regions_touched']}")
        assert tracker.LBA_histogram == expected_histogram
        assert result == expected_features
        print("  Expected values confirmed.")

    show_case(
        "Case 1: empty window",
        [0, 0, 0, 0],
        {"lba_variance": 0.0, "lba_histogram_variance": 0.0, "lba_regions_touched": 0},
    )

    for lba in (0, 3):
        tracker.update(Event(Op.WRITE, 0, lba, 1))
    show_case(
        "Case 2: two writes within region 0; the histogram loses their separation",
        [2, 0, 0, 0],
        {"lba_variance": 2.25, "lba_histogram_variance": 0.0, "lba_regions_touched": 1},
    )

    tracker.reset_window()
    tracker.update(Event(Op.READ, 0, 0, 1))
    for lba in (0, 3, 4, 7):
        tracker.update(Event(Op.WRITE, 0, lba, 1))
    show_case(
        "Case 3: a filtered-out read and four writes across two regions",
        [2, 2, 0, 0],
        {"lba_variance": 6.25, "lba_histogram_variance": 4.0, "lba_regions_touched": 2},
    )

    tracker.reset_window()
    show_case(
        "Case 4: reset clears the window but keeps the region configuration",
        [0, 0, 0, 0],
        {"lba_variance": 0.0, "lba_histogram_variance": 0.0, "lba_regions_touched": 0},
    )
    tracker.update(Event(Op.WRITE, 0, 15, 1))
    show_case(
        "Case 5: LBA 15 is the last valid address, in region 3",
        [0, 0, 0, 1],
        {"lba_variance": 0.0, "lba_histogram_variance": 0.0, "lba_regions_touched": 1},
    )

    print("\nCase 6: invalid LBAs are rejected")
    for lba in (-1, 16):
        try:
            tracker.update(Event(Op.WRITE, 0, lba, 1))
        except ValueError as error:
            print(f"  LBA {lba}: {error}")
        else:
            raise AssertionError(f"LBA {lba} should have been rejected")

    print("\nend of demo.")
