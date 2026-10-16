from __future__ import annotations

from ..event import Event
from ..tracker import FeatureTracker


class EntropyTracker(FeatureTracker):
    """Estimates write entropy and tracks entropy statistics over a window."""

    def __init__(self) -> None:
        """TODO: initialize entropy state."""
        raise NotImplementedError

    def estimate_entropy(self, data_sample: bytes) -> float:
        """TODO:
        Estimate normalized Shannon entropy from sampled write data.
        Details on notion
        """
        raise NotImplementedError

    def update(self, event: Event) -> None:
        """TODO:
        For a write:
        - if data_sample exists, estimate entropy from it;
        - otherwise, if precomputed entropy exists, use that;
        - update the window's entropy statistics.
        """
        raise NotImplementedError

    def features(self) -> dict[str, int | float]:
        """TODO:
        Return:
        - average write entropy,
        - variance of write entropy.
        """
        raise NotImplementedError

    def reset_window(self) -> None:
        """TODO: clear per-window entropy state."""
        raise NotImplementedError