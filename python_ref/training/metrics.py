"""Report held-out accuracy and errors by class."""

import numpy as np


def print_evaluation(labels: np.ndarray, predictions: np.ndarray) -> None:
    tn = np.count_nonzero((labels == 0) & (predictions == 0))
    fp = np.count_nonzero((labels == 0) & (predictions == 1))
    fn = np.count_nonzero((labels == 1) & (predictions == 0))
    tp = np.count_nonzero((labels == 1) & (predictions == 1))
    total_windows = len(labels)
    benign_total = tn + fp
    ransomware_total = fn + tp
    benign_rate = f"{fp / benign_total:.2%}" if benign_total else "n/a"
    ransomware_rate = f"{fn / ransomware_total:.2%}" if ransomware_total else "n/a"

    print(f"Test accuracy: {(tn + tp) / total_windows:.2%} ({total_windows:,} windows)")
    print()
    print("Confusion matrix (rows = actual, columns = predicted)")
    print(f"{'':28}{'Predicted 0':>14}{'Predicted 1':>14}{'Mispredict rate':>18}")
    print(f"{'Actual 0 (benign)':28}{tn:>14,}{fp:>14,}{benign_rate:>18}")
    print(f"{'Actual 1 (ransomware run)':28}{fn:>14,}{tp:>14,}{ransomware_rate:>18}")
    print(f"Overall mispredict rate: {(fp + fn) / total_windows:.2%}")
