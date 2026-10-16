from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeAlias

from .event import Event

FeatureValue: TypeAlias = int | float


class FeatureTracker(ABC):
    """Base class implemented by every feature module."""

    @abstractmethod
    def update(self, event: Event) -> None:
        """Process one valid decoded storage event."""
        raise NotImplementedError

    @abstractmethod
    def features(self) -> dict[str, FeatureValue]:
        """Return feature values for the current window."""
        raise NotImplementedError

    @abstractmethod
    def reset_window(self) -> None:
        """Reset state belonging only to the completed window.

        A tracker may intentionally preserve longer-term state here.
        """
        raise NotImplementedError
