# Sentry Python Reference Model

This folder is the shared Python framework for feature research before RTL implementation.

The intended workflow is:

1. Convert a storage trace into the shared `Event` format.
2. Feed every event to the same `WindowController`.
3. Each feature owner implements a `FeatureTracker`.
4. At the end of each fixed-size event window, the controller collects all feature outputs.
5. Export those feature vectors for classifier experiments.
6. Once an algorithm is approved, implement the same behavior in RTL and compare the RTL against this model.

The first version uses non-overlapping fixed event-count windows. Individual trackers are allowed to keep selected state across window boundaries when the algorithm requires longer-term history.

## Layout

```text
sentry_python_model/
├── sentry_model/
│   ├── event.py
│   ├── tracker.py
│   ├── window.py
│   ├── pipeline.py
│   ├── ransmap.py
│   ├── vector.py
│   ├── features/
│   │   ├── activity.py
│   │   ├── entropy.py
│   │   ├── lba.py
│   │   ├── patterns.py
│   │   ├── request_size.py
│   │   └── rewrite.py
│   └── classifiers/
│       ├── weighted_sum.py
│       └── decision_tree.py
├── scripts/
│   └── run_ransmap.py
└── tests/
    ├── test_features.py
    └── test_window.py
```

## Shared event format

The Python model uses `op`, `timestamp_ns`, `lba`, `block_count`, and optional normalized `entropy`.

The exact serialized TinyTapeout input protocol can be different. The important part is that every feature module sees the same decoded event representation.

## Running RanSMAP

```bash
python -m scripts.run_ransmap     --reads path/to/ata_read.csv     --writes path/to/ata_write.csv     --output features.csv     --window-size 64     --max-lba 100000000
```

`--max-lba` should represent the usable LBA range of the emulated/device configuration. It is used to divide the device into LBA regions.

## Tests

```bash
python -m pytest
```
