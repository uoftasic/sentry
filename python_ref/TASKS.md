# Implementation Tasks

Each person should take one task/file group. The shared `Event` and `FeatureTracker` interfaces should not be changed without discussing it with the team.

For all tasks, implement it in the hardware-friendly way that you will do in in RTL! Think it through. Details on implementation for many of the tasks can be found in the notion.
- Try to avoid using multipliers / dividers unless a term is a power of two
- Minimize the amount of state you need to store

## 1. RanSMAP parser

**File:** `sentry/ransmap.py`

Implement `load_ransmap()`.

It should:
- read `ata_read.csv` and `ata_write.csv`,
- create an `Event` for every row,
- set `op` to `READ` or `WRITE` based on the file,
- combine seconds + nanoseconds into `timestamp_ns`,
- convert the CSV request size in bytes into `block_count`,
- use `None` for read entropy (`-1` in RanSMAP),
- merge the two files into one chronological event list.

Do not calculate any features here.

Since RanSMAP does not give data, you can also try to find a way to get test traces that contain the actual data so we can test the entropy estimator.

---

## 2. Activity feature tracker

**File:** `sentry/features/activity.py`

Implement these whiteboard features for one window:
- number of writes,
- write fraction = `# writes / # events`,
- total bytes written,
- total bytes read,
- total time of the window.

Return them from `features()`.

---

## 3. Entropy feature tracker

**File:** `sentry/features/entropy.py`

Use the entropy value already supplied with write events.

Implement:
- average write entropy over the window,
- variance of write entropy over the window.

Ignore reads and writes where entropy is unavailable.

Do not implement the raw-data entropy estimator in this first prototype.

---

## 4. LBA feature tracker

**File:** `sentry/features/lba.py`

Implement:
- variance of LBA over the window,
- a configurable histogram of LBA regions,
- number of LBA regions touched.

The constructor receives `max_lba` and `num_regions`. Divide the usable LBA range evenly into that many regions.

The histogram itself should be available to the rest of the model because we may later derive more measurements from it.

---

## 5. Read-then-write tracker

**File:** `sentry/features/rewrite.py`

Implement the bitmap approach discussed on the whiteboard.

Use two bitmaps of recently read LBA regions:
- reads set a bit in the current bitmap,
- writes check whether the corresponding bit is present in the current or previous bitmap,
- every `rotation_events`, move the current bitmap to the previous bitmap and clear the current bitmap.

Track:
- number of writes to recently read regions,
- fraction of writes that hit recently read regions.

Use the same LBA-region mapping idea as the LBA tracker.

---

## 6. Read/write pattern tracker

**File:** `sentry/features/patterns.py`

Implement:
- read/write transition count,
- maximum number of consecutive writes in the window.

A transition happens whenever the operation changes from READ to WRITE or WRITE to READ.

---

## 7. Request-size tracker

**File:** `sentry/features/request_size.py`

Implement:
- total request size in bytes,
- average request size in bytes.

Keep this separate even if RanSMAP turns out to contain mostly 4096-byte requests.

---

## 8. Window controller

**File:** `sentry/window.py`

Implement a fixed, non-overlapping window of `N` events.

For every event:
1. send it to every feature tracker,
2. increment the event count.

When `window_size` events have been processed:
1. collect every tracker's `features()` dictionary,
2. combine them into one feature dictionary,
3. return a `WindowResult`,
4. call `reset_window()` on every tracker,
5. begin the next window.

Start with `window_size = 64`.

Do not implement overlap, sliding windows, or across-window averaging yet.

---

## 9. Classifier

**File:** `sentry/classifier.py`

Implement the weighted sum classifier

It receives a feature vector `x` and configurable weights `w` and calculates:

`score = bias + sum(w[i] * x[i])`

The classifier must not know what any feature means. It only sees an ordered list of numbers.

Implement:
- `score(feature_vector)`,
- `predict(feature_vector)` using a configurable threshold.

The initial weights can be supplied manually. Training/learning the weights can be added afterward.

Also conduct research into how we could do the decision tree classifier in hardware, and create a class for that as well.
---

## 10. Main integration

**File:** `main.py`

The structure is already written. Once Tasks 1–9 are complete, fill in any remaining TODOs so that it:
- loads one RanSMAP trace,
- creates all trackers,
- creates the window controller,
- runs every event through it,
- turns each completed window into an ordered feature vector,
- sends the vector to the weighted-sum classifier,
- prints the window number, feature values, score, and prediction.
