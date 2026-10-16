from sentry_model.event import Event, Op
from sentry_model.features import ActivityTracker
from sentry_model.window import WindowController


def test_window_controller_emits_after_n_events() -> None:
    controller = WindowController(
        trackers=[ActivityTracker()],
        window_size=4,
    )

    outputs = []

    for i in range(4):
        result = controller.update(
            Event(
                op=Op.WRITE if i >= 2 else Op.READ,
                timestamp_ns=i * 10,
                lba=i,
                block_count=8,
            )
        )
        outputs.append(result)

    assert outputs[0] is None
    assert outputs[1] is None
    assert outputs[2] is None
    assert outputs[3] is not None

    result = outputs[3]
    assert result is not None
    assert result.features["window_event_count"] == 4
    assert result.features["window_duration_ns"] == 30
    assert result.features["write_count"] == 2
