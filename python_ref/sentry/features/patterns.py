from __future__ import annotations

from ..event import Event, Op
from ..tracker import FeatureTracker


class PatternTracker(FeatureTracker):
    """Tracks read/write ordering within the event stream."""

    def __init__(self) -> None:
        self.reset_window()

    def update(self, event: Event) -> None:
        op = event.op
        if (self._previous_op, op) in ((Op.READ, Op.WRITE), (Op.WRITE, Op.READ)):
            self._transition_count += 1

        if op == Op.WRITE:
            self._write_run += 1
            self._max_consecutive_writes = max(
                self._max_consecutive_writes, self._write_run
            )
        else:
            self._write_run = 0

        self._previous_op = op

    def features(self) -> dict[str, int | float]:
        return {
            "read_write_transition_count": self._transition_count,
            "max_consecutive_writes": self._max_consecutive_writes,
        }

    def reset_window(self) -> None:
        self._previous_op: Op | None = None
        self._transition_count = 0
        self._write_run = 0
        self._max_consecutive_writes = 0
