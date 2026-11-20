"""Train Sentry's weighted-sum classifier."""

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.weighted_sum.train import main, read_dataset, train_model


if __name__ == "__main__":
    main()
