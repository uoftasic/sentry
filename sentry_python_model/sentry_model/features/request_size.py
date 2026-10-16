from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class RequestSizeTracker(FeatureTracker):
    """Tracks request-size statistics using configurable byte thresholds."""

    def __init__(
        self,
        thresholds_bytes: tuple[int, ...] = (
            4 * 1024,
            16 * 1024,
            64 * 1024,
        ),
    ) -> None:
        if any(x <= 0 for x in thresholds_bytes):
            raise ValueError("request-size thresholds must be positive")
        if tuple(sorted(thresholds_bytes)) != thresholds_bytes:
            raise ValueError("request-size thresholds must be sorted")

        self.thresholds_bytes = thresholds_bytes
        self.reset_window()

    def update(self, event: Event) -> None:
        size = event.size_bytes
        self.count += 1
        self.total_bytes += size

        bucket = 0
        while (
            bucket < len(self.thresholds_bytes)
            and size > self.thresholds_bytes[bucket]
        ):
            bucket += 1

        self.histogram[bucket] += 1

    def features(self) -> dict[str, int | float]:
        average = self.total_bytes / self.count if self.count else 0.0

        result: dict[str, int | float] = {
            "request_size_mean_bytes": average,
        }

        for i, count in enumerate(self.histogram):
            result[f"request_size_bin_{i}_count"] = count

        return result

    def reset_window(self) -> None:
        self.count = 0
        self.total_bytes = 0
        self.histogram = [0] * (len(self.thresholds_bytes) + 1)
