from __future__ import annotations

from collections.abc import Iterable

from .event import Event
from .window import WindowController, WindowResult


def run_pipeline(
    events: Iterable[Event],
    controller: WindowController,
) -> list[WindowResult]:
    """Run a complete trace through the model.

    An incomplete final window is intentionally ignored in v0.
    """
    results: list[WindowResult] = []

    for event in events:
        result = controller.update(event)
        if result is not None:
            results.append(result)

    return results
