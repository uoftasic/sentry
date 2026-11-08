"""Self-contained sanity check for the decision tree classifier.

Run: python sentry/_demo_tree.py
This does not need the rest of the pipeline (parser, trackers, window).
"""
from __future__ import annotations

from classifier import DecisionTreeClassifier, TreeNode, WeightedSumClassifier


def build_demo_forest() -> list[list[TreeNode]]:
    # Tree 0: tests feature[0] (e.g. "write fraction") <= 0.5
    #   root(0) -- feature 0 <= 0.5 --> leaf(1) value -1.0
    #           -- else               --> node(2): feature 1 <= 100 ?
    #                                        leaf(3) +0.3 : leaf(4) +1.2
    tree0 = [
        TreeNode(is_leaf=False, feature_idx=0, threshold=0.5, left=1, right=2),
        TreeNode(is_leaf=True, value=-1.0),
        TreeNode(is_leaf=False, feature_idx=1, threshold=100.0, left=3, right=4),
        TreeNode(is_leaf=True, value=0.3),
        TreeNode(is_leaf=True, value=1.2),
    ]
    # Tree 1: a second booster tree on feature[2] (e.g. "rewrite fraction")
    tree1 = [
        TreeNode(is_leaf=False, feature_idx=2, threshold=0.25, left=1, right=2),
        TreeNode(is_leaf=True, value=-0.4),
        TreeNode(is_leaf=True, value=0.9),
    ]
    return [tree0, tree1]


def main() -> None:
    clf = DecisionTreeClassifier(build_demo_forest(), bias=0.0, threshold=0.5)

    cases = [
        # (feature_vector, human description)
        ([0.1, 50.0, 0.0], "mostly reads, low rewrite -> benign"),
        ([0.9, 50.0, 0.0], "lots of writes, low rewrite"),
        ([0.9, 150.0, 0.8], "lots of writes + high rewrite -> ransomware-like"),
    ]
    print("=== DecisionTreeClassifier (LightGBM-style ensemble) ===")
    for fv, desc in cases:
        s = clf.score(fv)
        p = clf.predict(fv)
        print(f"  {fv!s:<22} score={s:+.3f}  predict={p}   # {desc}")

    print("\n=== ROM export (to_rom_rows) -- this is the HDL bridge ===")
    for row in clf.to_rom_rows():
        kind = "LEAF " if row["is_leaf"] else "SPLIT"
        if row["is_leaf"]:
            detail = f"value={row['value']:+.3f}"
        else:
            detail = (
                f"feat[{row['feature_idx']}] <= {row['threshold']:.3f} "
                f"? L={row['left_addr']} : R={row['right_addr']}"
            )
        print(f"  addr={row['addr']:<2} tree={row['tree_id']} {kind} {detail}")

    print("\n=== WeightedSumClassifier (for comparison) ===")
    ws = WeightedSumClassifier(weights=[2.0, 0.01, 1.5], bias=-1.0, threshold=0.5)
    for fv, desc in cases:
        print(f"  {fv!s:<22} score={ws.score(fv):+.3f}  predict={ws.predict(fv)}")


if __name__ == "__main__":
    main()
