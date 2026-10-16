from __future__ import annotations

from dataclasses import dataclass

from .event import Event
from .tracker import FeatureTracker, FeatureValue


@dataclass(frozen=True, slots=True)
class WindowResult:
    window_index: int
    start_timestamp_ns: int
    end_timestamp_ns: int
    features: dict[str, FeatureValue]


class WindowController:
    """Non-overlapping, fixed event-count window controller."""

    def __init__(
        self,
        trackers: list[FeatureTracker],
        window_size: int = 64,
    ) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")

        self.trackers = trackers
        self.window_size = window_size

        self._event_count = 0
        self._window_index = 0
        self._start_timestamp_ns: int | None = None
        self._last_timestamp_ns: int | None = None

    def update(self, event: Event) -> WindowResult | None:
        """Process one event.

        Returning a WindowResult is the Python equivalent of asserting
        feature_valid in RTL.
        """
        if (
            self._last_timestamp_ns is not None
            and event.timestamp_ns < self._last_timestamp_ns
        ):
            raise ValueError("events must be supplied in chronological order")

        if self._event_count == 0:
            self._start_timestamp_ns = event.timestamp_ns

        self._last_timestamp_ns = event.timestamp_ns

        for tracker in self.trackers:
            tracker.update(event)

        self._event_count += 1

        if self._event_count < self.window_size:
            return None

        assert self._start_timestamp_ns is not None
        assert self._last_timestamp_ns is not None

        merged: dict[str, FeatureValue] = {
            "window_event_count": self._event_count,
            "window_duration_ns": (
                self._last_timestamp_ns - self._start_timestamp_ns
            ),
        }

        for tracker in self.trackers:
            tracker_features = tracker.features()
            duplicate = merged.keys() & tracker_features.keys()
            if duplicate:
                raise ValueError(
                    f"duplicate feature names: {sorted(duplicate)}"
                )
            merged.update(tracker_features)

        result = WindowResult(
            window_index=self._window_index,
            start_timestamp_ns=self._start_timestamp_ns,
            end_timestamp_ns=self._last_timestamp_ns,
            features=merged,
        )

        for tracker in self.trackers:
            tracker.reset_window()

        self._window_index += 1
        self._event_count = 0
        self._start_timestamp_ns = None

        return result
