from __future__ import annotations

from abc import ABC, abstractmethod

from .event import Event


class FeatureTracker(ABC):
    """Common interface for every feature tracker."""

    @abstractmethod
    def update(self, event: Event) -> None:
        """Process one storage event."""
        raise NotImplementedError

    @abstractmethod
    def features(self) -> dict[str, int | float]:
        """Return the current window's feature values."""
        raise NotImplementedError

    @abstractmethod
    def reset_window(self) -> None:
        """Clear state that belongs to the completed window."""
        raise NotImplementedError
