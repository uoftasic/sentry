from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSchema:
    """Defines a stable feature-vector ordering for classifiers and RTL."""

    names: tuple[str, ...]

    def vectorize(self, features: dict[str, int | float]) -> list[float]:
        missing = [name for name in self.names if name not in features]
        if missing:
            raise KeyError(f"missing features: {missing}")

        return [float(features[name]) for name in self.names]

    def index_of(self, name: str) -> int:
        return self.names.index(name)
