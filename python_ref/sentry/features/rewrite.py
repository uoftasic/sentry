from __future__ import annotations

from ..event import Event, Op
from ..tracker import FeatureTracker


class RewriteTracker(FeatureTracker):
    """Tracks writes to recently read LBA regions using rotating bitmaps."""

    def __init__(
        self,
        max_lba: int,
        num_regions: int = 32,
        rotation_events: int = 32,
    ) -> None:
        if max_lba <= 0:
            raise ValueError("max_lba must be positive")
        if num_regions <= 0:
            raise ValueError("num_regions must be positive")
        if rotation_events <= 0:
            raise ValueError("rotation_events must be positive")

        self.max_lba = max_lba
        self.num_regions = num_regions
        self.rotation_events = rotation_events
        self.current_bitmap = 0
        self.previous_bitmap = 0
        self.events_since_rotation = 0
        self.reset_window()

    def update(self, event: Event) -> None:
        """Record reads, detect matching writes, and rotate read history."""
        region = min(
            max(event.lba, 0) * self.num_regions // self.max_lba,
            self.num_regions - 1,
        )
        region_bit = 1 << region

        if event.op == Op.READ: # Set the bit corresponding to the region
            self.current_bitmap |= region_bit
        elif event.op == Op.WRITE:
            self._write_count += 1
            # If the region was read in one of the previous bitmaps, add to the counter
            if (self.current_bitmap | self.previous_bitmap) & region_bit:
                self._recent_read_write_count += 1

        self.events_since_rotation += 1
        # Rotate the bitmaps
        if self.events_since_rotation == self.rotation_events:
            self.previous_bitmap = self.current_bitmap
            self.current_bitmap = 0
            self.events_since_rotation = 0

    def features(self) -> dict[str, int | float]:
        """Return read-then-write count and fraction for this window."""
        return {
            "read_then_write_count": self._recent_read_write_count,
            "read_then_write_fraction": (
                self._recent_read_write_count / self._write_count
                if self._write_count
                else 0.0
            ),
        }

    def reset_window(self) -> None:
        """Reset statistics. Don't reset history since it would work across windows"""
        self._write_count = 0
        self._recent_read_write_count = 0


if __name__ == "__main__":
    tracker = RewriteTracker(max_lba=100, num_regions=4, rotation_events=3)
    test_events = (
        Event(Op.READ, 0, 10, 1),
        Event(Op.WRITE, 1, 10, 1),  # Current-bitmap hit.
        Event(Op.OTHER, 2, 90, 1),  # Rotates current into previous.
        Event(Op.WRITE, 3, 10, 1),  # Previous-bitmap hit.
        Event(Op.WRITE, 4, 60, 1),  # Different-region miss.
        Event(Op.OTHER, 5, 0, 1),   # Second rotation expires the read.
        Event(Op.WRITE, 6, 10, 1),  # Expired-region miss.
    )

    for event in test_events:
        tracker.update(event)
        print(
            f"op={event.op.name}, lba={event.lba}, "
            f"current={tracker.current_bitmap:04b}, "
            f"previous={tracker.previous_bitmap:04b}, "
            f"features={tracker.features()}"
        )

    assert tracker.features() == {
        "read_then_write_count": 2,
        "read_then_write_fraction": 0.5,
    }
    tracker.reset_window()
    assert tracker.features() == {
        "read_then_write_count": 0,
        "read_then_write_fraction": 0.0,
    }
    print("RewriteTracker tests passed")
