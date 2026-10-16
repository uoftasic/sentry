from __future__ import annotations

import math

from ..event import Event
from ..tracker import FeatureTracker


class LBATracker(FeatureTracker):
    """Tracks LBA spread using variance and coarse address regions."""

    def __init__(
        self,
        max_lba_exclusive: int,
        num_regions: int = 32,
    ) -> None:
        if max_lba_exclusive <= 0:
            raise ValueError("max_lba_exclusive must be positive")
        if num_regions <= 0:
            raise ValueError("num_regions must be positive")

        self.max_lba_exclusive = max_lba_exclusive
        self.num_regions = num_regions
        self.previous_lba: int | None = None
        self.reset_window()

    def _region(self, lba: int) -> int:
        region = (lba * self.num_regions) // self.max_lba_exclusive
        return min(region, self.num_regions - 1)

    def update(self, event: Event) -> None:
        lba = event.lba

        self.count += 1
        self.sum_lba += lba
        self.sum_lba_sq += lba * lba

        region = self._region(lba)
        self.histogram[region] += 1

        if self.previous_lba is not None:
            self.jump_sum += abs(lba - self.previous_lba)
            self.jump_count += 1

        self.previous_lba = lba

    def features(self) -> dict[str, int | float]:
        if self.count == 0:
            variance = 0.0
            regions_touched = 0
            max_region_fraction = 0.0
            region_entropy = 0.0
        else:
            mean = self.sum_lba / self.count
            variance = max(
                0.0,
                self.sum_lba_sq / self.count - mean * mean,
            )

            regions_touched = sum(1 for c in self.histogram if c > 0)
            max_region_fraction = max(self.histogram) / self.count

            raw_entropy = 0.0
            for c in self.histogram:
                if c == 0:
                    continue
                p = c / self.count
                raw_entropy -= p * math.log2(p)

            max_entropy = math.log2(self.num_regions)
            region_entropy = (
                raw_entropy / max_entropy if max_entropy > 0 else 0.0
            )

        average_jump = (
            self.jump_sum / self.jump_count
            if self.jump_count
            else 0.0
        )

        result: dict[str, int | float] = {
            "lba_variance": variance,
            "lba_regions_touched": regions_touched,
            "lba_max_region_fraction": max_region_fraction,
            "lba_region_entropy": region_entropy,
            "lba_average_jump": average_jump,
        }

        for i, count in enumerate(self.histogram):
            result[f"lba_region_{i}_count"] = count

        return result

    def reset_window(self) -> None:
        self.count = 0
        self.sum_lba = 0
        self.sum_lba_sq = 0
        self.histogram = [0 for _ in range(self.num_regions)]
        self.jump_sum = 0
        self.jump_count = 0
        # previous_lba intentionally survives the window boundary
