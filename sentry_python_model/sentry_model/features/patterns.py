from __future__ import annotations

from ..event import Event, Op
from ..tracker import FeatureTracker


class OperationPatternTracker(FeatureTracker):
    """Tracks ordering information that averages and histograms lose."""

    def __init__(self) -> None:
        self.previous_op: Op | None = None
        self.current_write_run = 0
        self.reset_window()

    def update(self, event: Event) -> None:
        if self.previous_op is not None and event.op != self.previous_op:
            self.transition_count += 1

        if event.op == Op.WRITE:
            self.current_write_run += 1
            self.max_consecutive_writes = max(
                self.max_consecutive_writes,
                self.current_write_run,
            )
        else:
            self.current_write_run = 0

        self.previous_op = event.op

    def features(self) -> dict[str, int | float]:
        return {
            "operation_transition_count": self.transition_count,
            "max_consecutive_writes": self.max_consecutive_writes,
        }

    def reset_window(self) -> None:
        self.transition_count = 0
        current_run = getattr(self, "current_write_run", 0)
        self.max_consecutive_writes = current_run
