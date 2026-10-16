from __future__ import annotations

from ..event import Event, Op
from ..tracker import FeatureTracker


class EntropyTracker(FeatureTracker):
    """Aggregates normalized per-write entropy values."""

    def __init__(self, high_entropy_threshold: float = 0.90) -> None:
        if not (0.0 <= high_entropy_threshold <= 1.0):
            raise ValueError("high_entropy_threshold must be in [0, 1]")

        self.high_entropy_threshold = high_entropy_threshold
        self.reset_window()

    def update(self, event: Event) -> None:
        if event.op != Op.WRITE or event.entropy is None:
            return

        x = event.entropy
        self.count += 1
        self.sum_entropy += x
        self.sum_entropy_sq += x * x

        if x >= self.high_entropy_threshold:
            self.high_entropy_count += 1

        if x < 0.25:
            self.histogram[0] += 1
        elif x < 0.50:
            self.histogram[1] += 1
        elif x < 0.75:
            self.histogram[2] += 1
        else:
            self.histogram[3] += 1

    def features(self) -> dict[str, int | float]:
        if self.count == 0:
            mean = 0.0
            variance = 0.0
            high_fraction = 0.0
        else:
            mean = self.sum_entropy / self.count
            variance = max(
                0.0,
                self.sum_entropy_sq / self.count - mean * mean,
            )
            high_fraction = self.high_entropy_count / self.count

        return {
            "write_entropy_mean": mean,
            "write_entropy_variance": variance,
            "high_entropy_write_count": self.high_entropy_count,
            "high_entropy_write_fraction": high_fraction,
            "entropy_bin_0": self.histogram[0],
            "entropy_bin_1": self.histogram[1],
            "entropy_bin_2": self.histogram[2],
            "entropy_bin_3": self.histogram[3],
        }

    def reset_window(self) -> None:
        self.count = 0
        self.sum_entropy = 0.0
        self.sum_entropy_sq = 0.0
        self.high_entropy_count = 0
        self.histogram = [0, 0, 0, 0]
