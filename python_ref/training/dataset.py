"""Load the feature columns and run labels shared by all classifiers."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from export_ransmap import FEATURE_NAMES


def read_dataset(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read the features in Sentry's order, followed by the run label."""
    names = (*FEATURE_NAMES, "run_label")
    with path.open(newline="", encoding="utf-8-sig") as file:
        header = next(csv.reader(file), [])
        missing = [name for name in names if header.count(name) != 1]
        if missing:
            raise ValueError(f"{path}: expected one column for each of {', '.join(missing)}")
        # Use column names to keep features aligned if the CSV columns move.
        columns = [header.index(name) for name in names]
        rows = np.loadtxt(file, delimiter=",", usecols=columns, ndmin=2, comments=None, quotechar='"')

    if not rows.size or not np.isfinite(rows).all():
        raise ValueError(f"{path}: expected at least one row with finite numeric values")
    labels = rows[:, -1]
    if not np.isin(labels, (0, 1)).all():
        raise ValueError(f"{path}: run_label must be 0 or 1")
    return rows[:, :-1], labels.astype(int)
