# Sentry Python Prototype

This is a deliberately small starter template for the Python prototype discussed on the whiteboard.

The shared structure is already defined so everyone can work in parallel, but the actual feature algorithms, window controller, parser, and classifier are left unimplemented.

The first prototype is:

```text
RanSMAP read/write CSVs
        ↓
load_ransmap()
        ↓
Event objects
        ↓
Feature Trackers
        ↓
WindowController (N events per window)
        ↓
feature vector
        ↓
WeightedSumClassifier
        ↓
score
```

Run the completed prototype with:

```bash
python main.py path/to/ata_read.csv path/to/ata_write.csv
```

Start with `WINDOW_SIZE = 64`. The point of this version is to get the agreed whiteboard design working in Python before deciding what should become RTL.
