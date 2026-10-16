from __future__ import annotations

from ..event import Event, Op
from ..tracker import FeatureTracker


class RewriteTracker(FeatureTracker):
    """Approximate read-then-write detection with rotating region bitmaps."""

    def __init__(
        self,
        max_lba_exclusive: int,
        num_regions: int = 32,
        rotation_events: int = 32,
        high_entropy_threshold: float = 0.90,
    ) -> None:
        if max_lba_exclusive <= 0:
            raise ValueError("max_lba_exclusive must be positive")
        if num_regions <= 0:
            raise ValueError("num_regions must be positive")
        if rotation_events <= 0:
            raise ValueError("rotation_events must be positive")

        self.max_lba_exclusive = max_lba_exclusive
        self.num_regions = num_regions
        self.rotation_events = rotation_events
        self.high_entropy_threshold = high_entropy_threshold

        self.current_bitmap = 0
        self.previous_bitmap = 0
        self.events_since_rotation = 0

        self.reset_window()

    def _region(self, lba: int) -> int:
        region = (lba * self.num_regions) // self.max_lba_exclusive
        return min(region, self.num_regions - 1)

    def _rotate_if_needed(self) -> None:
        if self.events_since_rotation < self.rotation_events:
            return

        self.previous_bitmap = self.current_bitmap
        self.current_bitmap = 0
        self.events_since_rotation = 0

    def update(self, event: Event) -> None:
        self._rotate_if_needed()

        region = self._region(event.lba)
        mask = 1 << region

        if event.op == Op.READ:
            self.current_bitmap |= mask

        elif event.op == Op.WRITE:
            self.write_count += 1

            if (self.current_bitmap | self.previous_bitmap) & mask:
                self.read_then_write_count += 1

                if (
                    event.entropy is not None
                    and event.entropy >= self.high_entropy_threshold
                ):
                    self.high_entropy_rewrite_count += 1

        self.events_since_rotation += 1

    def features(self) -> dict[str, int | float]:
        rewrite_fraction = (
            self.read_then_write_count / self.write_count
            if self.write_count
            else 0.0
        )

        return {
            "read_then_write_count": self.read_then_write_count,
            "read_then_write_fraction": rewrite_fraction,
            "high_entropy_rewrite_count": self.high_entropy_rewrite_count,
        }

    def reset_window(self) -> None:
        self.write_count = 0
        self.read_then_write_count = 0
        self.high_entropy_rewrite_count = 0
        # rotating bitmaps intentionally survive the feature-window boundary
