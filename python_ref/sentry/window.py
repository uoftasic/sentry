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
        """TODO(Task 8): initialize window state."""
        raise NotImplementedError

    def update(self, event: Event) -> WindowResult | None:
        """Process one event and return a result when a window completes.

        TODO(Task 8): implement exactly as described in TASKS.md.
        """
        raise NotImplementedError
