# Sentry classifier training

Run these commands from `python_ref` with NumPy installed. Weighted-sum and ANN training also use scikit-learn, and decision-tree training also uses LightGBM.

All classifiers use the same CSV format. The shared loader selects Sentry's 16 scalar features by name and uses `run_label` as the target for each window.

| Module | Purpose |
| --- | --- |
| `training.dataset` | Shared CSV loading and feature order |
| `training.metrics` | Shared held-out accuracy and confusion matrix |
| `training.weighted_sum` | Train and evaluate the weighted-sum baseline |
| `training.tsetlin` | Train, save, and evaluate the reference Tsetlin machine |
| `training.decision_tree` | Train, save, and evaluate boosted trees using the reference classifier |
| `training.ann` | Train, save, and evaluate a small neural network |
| `training.ann_deep` | Train, save, and evaluate a network with four hidden layers |

## Weighted sum

```sh
python -m training.weighted_sum.train training/train.csv --test training/test.csv --output build/weights.json
python -m training.weighted_sum.evaluate training/test.csv --weights build/weights.json
```

The original `training/train_sentry.py` and `training/evaluate_sentry.py` commands also work with their existing arguments and weight files.

## Tsetlin machine

```sh
python -m training.tsetlin.train training/train.csv --test training/test.csv --output build/tsetlin.json
python -m training.tsetlin.evaluate training/test.csv --model build/tsetlin.json
```

Training derives thermometer cutoffs from the training CSV and shuffles the training windows before each pass. The model JSON records the cutoffs, automaton states, classifier settings, and training accuracy by epoch. Use `python -m training.tsetlin.train --help` for training options.

## Decision tree

```sh
python -m pip install numpy lightgbm
python -m training.decision_tree.train training/train.csv --test training/test.csv --output ../build/decision-tree.json
python -m training.decision_tree.evaluate training/test.csv --model ../build/decision-tree.json
```

LightGBM learns the trees from the training CSV. The saved model contains the reference classifier's flat tree nodes, and the evaluation command uses those nodes with NumPy. Use `python -m training.decision_tree.train --help` to set the tree count, depth, and other training options.

## Small neural network

```sh
python -m pip install numpy scikit-learn
python -m training.ann.train ../build/ransmap-128/train.csv --test ../build/ransmap-128/test.csv --output ../build/ann-128.json
python -m training.ann.evaluate ../build/ransmap-128/test.csv --model ../build/ann-128.json
```

The default network has one hidden layer with four ReLU units and 73 learned weights and biases. The trainer folds feature scaling into the saved first layer, so the saved model takes the original Sentry features. Use `python -m training.ann.train --help` for the layer width, epoch count, batch size, learning rate, L2 penalty, decision threshold, and seed.

## Four-hidden-layer neural network

```sh
python -m training.ann_deep.train ../build/ransmap-128/train.csv \
  --test ../build/ransmap-128/test.csv \
  --hidden-units 32 16 8 4 --epochs 24 \
  --output ../build/ann-deep-128.json
python -m training.ann_deep.evaluate ../build/ransmap-128/test.csv --model ../build/ann-deep-128.json
```

Each of the four hidden layers uses ReLU, and the output layer produces one score per window. Training uses scikit-learn and evaluation uses NumPy. The saved first layer includes feature scaling, so the scorer accepts the original 16 features.

For tuning, split the training CSV by hardware setup or by whole `run_id` groups. Pass the resulting fit CSV as the training input and use `--validation` for the validation CSV. The trainer saves the epoch with the highest validation accuracy, picking the earliest epoch when scores tie. Keep the original test CSV for the final evaluation. Use `python -m training.ann_deep.train --help` for the optimizer and decision threshold options.
