import pytest

from sentry_model.event import Event, Op
from sentry_model.features import (
    ActivityTracker,
    EntropyTracker,
    RewriteTracker,
)


def event(
    op: Op,
    *,
    t: int,
    lba: int = 0,
    blocks: int = 8,
    entropy: float | None = None,
) -> Event:
    return Event(
        op=op,
        timestamp_ns=t,
        lba=lba,
        block_count=blocks,
        entropy=entropy,
    )


def test_activity_tracker() -> None:
    tracker = ActivityTracker()

    tracker.update(event(Op.READ, t=0))
    tracker.update(event(Op.WRITE, t=1))
    tracker.update(event(Op.WRITE, t=2))

    features = tracker.features()

    assert features["write_count"] == 2
    assert features["write_fraction"] == 2 / 3
    assert features["bytes_written"] == 8192


def test_entropy_tracker() -> None:
    tracker = EntropyTracker(high_entropy_threshold=0.90)

    tracker.update(event(Op.WRITE, t=0, entropy=0.95))
    tracker.update(event(Op.WRITE, t=1, entropy=0.85))
    tracker.update(event(Op.READ, t=2))

    features = tracker.features()

    assert features["write_entropy_mean"] == pytest.approx(0.90)
    assert features["high_entropy_write_count"] == 1
    assert features["high_entropy_write_fraction"] == 0.5


def test_rewrite_bitmap() -> None:
    tracker = RewriteTracker(
        max_lba_exclusive=1600,
        num_regions=16,
        rotation_events=8,
    )

    tracker.update(event(Op.READ, t=0, lba=100))
    tracker.update(event(Op.WRITE, t=1, lba=120))

    features = tracker.features()

    assert features["read_then_write_count"] == 1
    assert features["read_then_write_fraction"] == 1.0
