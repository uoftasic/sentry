from __future__ import annotations

from dataclasses import dataclass

from .event import Event
from .tracker import FeatureTracker


@dataclass(frozen=True, slots=True)
class WindowResult:
    window_index: int
    features: dict[str, int | float]


class WindowController:
    """Fixed event-count window controller."""

    def __init__(
        self,
        trackers: list[FeatureTracker],
        window_size: int = 64,
    ) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")

        self.trackers = trackers
        self.window_size = window_size
        self.event_count = 0
        self.window_index = 0

    def update(self, event: Event) -> WindowResult | None:
        """Process one event and return a result when a window completes."""
        for tracker in self.trackers:
            tracker.update(event)

        self.event_count += 1
        if self.event_count != self.window_size:
            return None

        features: dict[str, int | float] = {}
        for tracker in self.trackers:
            features.update(tracker.features())

        result = WindowResult(self.window_index, features)
        for tracker in self.trackers:
            tracker.reset_window()

        self.event_count = 0
        self.window_index += 1
        return result
