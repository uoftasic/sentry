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
        if (
            self.expand_requests_to_blocks
            and event.lba + event.block_count > self.max_lba
        ):
            raise ValueError("request extends beyond LBATracker's max_lba")

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
        self.num_blocks = 0


if __name__ == "__main__":
    import argparse
    import math
    import random
    import secrets
    import statistics

    parser = argparse.ArgumentParser(description="Demonstrate LBA tracking patterns")
    parser.add_argument(
        "--seed", type=int, help="reuse a seed to generate the same requests"
    )
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbits(64)
    rng = random.Random(seed)

    max_lba = 1 << 20
    num_regions = 32
    region_width = max_lba // num_regions
    requests_per_case = 4096

    def make_requests(pattern: str) -> list[tuple[int, int]]:
        requests = []
        scan_lba = rng.randrange(0, max_lba // 4)
        hotspot_region = rng.randrange(1, num_regions - 1)
        for i in range(requests_per_case):
            block_count = rng.randint(1, 128)
            if pattern == "Sequential scan":
                lba = scan_lba
                scan_lba += block_count + rng.randint(0, 8)
            elif pattern == "One-region hotspot":
                lba = (
                    hotspot_region * region_width
                    + region_width // 2
                    + rng.randint(-2048, 2048)
                )
            elif pattern == "Two distant clusters":
                region = 4 if i % 2 == 0 else 26
                lba = region * region_width + region_width // 2 + rng.randint(-2048, 2048)
            elif pattern == "Boundary crossings":
                boundary = rng.randrange(1, num_regions) * region_width
                before = rng.randint(1, 64)
                lba = boundary - before
                block_count = before + rng.randint(1, 64)
            else:  # Scattered requests
                lba = rng.randrange(0, max_lba - block_count + 1)
            requests.append((lba, block_count))
        return requests

    def check_tracker(
        tracker: LBATracker,
        requests: list[tuple[int, int]],
        expand: bool,
    ) -> dict[str, int | float]:
        expected_lbas = [
            lba
            for start, count in requests
            for lba in (range(start, start + count) if expand else (start,))
        ]
        expected_histogram = [0] * num_regions
        for lba in expected_lbas:
            expected_histogram[lba // region_width] += 1

        result = tracker.features()
        assert tracker.num_events == len(requests)
        assert tracker.num_blocks == sum(count for _, count in requests)
        assert tracker.LBA_histogram == expected_histogram
        assert tracker.num_nonzero_regions == sum(bool(n) for n in expected_histogram)
        assert result["lba_regions_touched"] == tracker.num_nonzero_regions
        assert math.isclose(
            result["lba_variance"], statistics.pvariance(expected_lbas), rel_tol=1e-12
        )
        return result

    print(f"Seed: {seed}  (repeat with --seed {seed})")
    print(f"{requests_per_case:,} requests per case; {num_regions} regions")

    for pattern in (
        "Sequential scan",
        "One-region hotspot",
        "Two distant clusters",
        "Boundary crossings",
        "Scattered requests",
    ):
        requests = make_requests(pattern)
        starts = LBATracker(max_lba=max_lba, num_regions=num_regions)
        blocks = LBATracker(
            max_lba=max_lba,
            num_regions=num_regions,
            expand_requests_to_blocks=True,
        )
        for i, (lba, block_count) in enumerate(requests):
            event = Event(Op.READ, i, lba, block_count)
            starts.update(event)
            blocks.update(event)

        start_features = check_tracker(starts, requests, expand=False)
        block_features = check_tracker(blocks, requests, expand=True)

        print(f"\n{pattern}")
        print("First requests (start LBA, blocks): " + ", ".join(
            f"({lba:,}, {count})" for lba, count in requests[:5]
        ))
        print(
            f"{'Mode':<12} {'Samples':>9} {'Exact variance':>18} "
            f"{'Histogram variance':>20} {'Error':>9} {'Regions':>8}"
        )
        for label, tracker, features in (
            ("Starts", starts, start_features),
            ("Blocks", blocks, block_features),
        ):
            exact = features["lba_variance"]
            approximate = features["lba_histogram_variance"]
            error = f"{abs(approximate - exact) / exact:.1%}" if exact else "n/a"
            samples = tracker.num_blocks if tracker.expand_requests_to_blocks else tracker.num_events
            print(
                f"{label:<12} {samples:>9,} {exact:>18,.1f} "
                f"{approximate:>20,.1f} {error:>9} "
                f"{features['lba_regions_touched']:>8}"
            )

        print("\nHistogram (counts by region):")
        column_width = max(
            5,
            *(len(f"{count:,}") for count in starts.LBA_histogram + blocks.LBA_histogram),
        )
        for first in range(0, num_regions, 16):
            region_slice = range(first, first + 16)
            print("Region " + " ".join(f"{i:>{column_width}}" for i in region_slice))
            print("Starts " + " ".join(
                f"{starts.LBA_histogram[i]:>{column_width},}" for i in region_slice
            ))
            print("Blocks " + " ".join(
                f"{blocks.LBA_histogram[i]:>{column_width},}" for i in region_slice
            ))
            if first + 16 < num_regions:
                print()
