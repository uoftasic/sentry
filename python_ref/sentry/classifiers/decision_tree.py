from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..classifier import Classifier


@dataclass(frozen=True)
class TreeNode:
    """One node in a flat decision-tree array.

    Internal node (``is_leaf`` False):
        feature_idx : which feature-vector element to test
        threshold   : traverse left if feature[feature_idx] <= threshold
        left        : node index taken when the test is True
        right       : node index taken when the test is False

    Leaf node (``is_leaf`` True):
        value       : constant contribution added to the ensemble score

    Field layout is fixed-width on purpose: in RTL every node is one ROM word
    with the same bit fields, whether it is a leaf or an internal node.
    """

    is_leaf: bool
    feature_idx: int = 0
    threshold: float = 0.0
    left: int = 0
    right: int = 0
    value: float = 0.0


class DecisionTreeClassifier(Classifier):
    """LightGBM-style gradient-boosted decision tree classifier.

    This class is feature-agnostic: it only ever sees an ordered numeric
    feature vector. The model is a list of flat ``TreeNode`` arrays. Scoring
    sums the leaf value reached in every tree, then applies the boosting bias.
    """

    def __init__(
        self,
        forest: list[list[TreeNode]],
        bias: float = 0.0,
        threshold: float = 0.0,
    ) -> None:
        self.fit(forest, bias=bias, threshold=threshold)

    def fit(
        self,
        forest: list[list[TreeNode]],
        bias: float = 0.0,
        threshold: float = 0.0,
    ) -> None:
        if not forest:
            raise ValueError("forest must contain at least one tree")
        for tree_index, tree in enumerate(forest):
            self._validate_tree(tree_index, tree)
        self.forest = forest
        self.bias = float(bias)
        self.threshold = float(threshold)

    @staticmethod
    def _validate_tree(tree_index: int, tree: list[TreeNode]) -> None:
        if not tree:
            raise ValueError(f"tree {tree_index} is empty")
        n = len(tree)
        for node_index, node in enumerate(tree):
            if node.is_leaf:
                continue
            if node.feature_idx < 0:
                raise ValueError(
                    f"tree {tree_index} node {node_index}: feature_idx must be >= 0"
                )
            for child in (node.left, node.right):
                if not 0 <= child < n:
                    raise ValueError(
                        f"tree {tree_index} node {node_index}: child index {child} "
                        f"out of range [0, {n})"
                    )
                if child == node_index:
                    raise ValueError(
                        f"tree {tree_index} node {node_index}: node points to itself"
                    )

    def _eval_tree(self, tree: list[TreeNode], feature_vector: Sequence[float]) -> float:
        """Walk one tree from the root (index 0) to a leaf."""
        idx = 0
        for _ in range(len(tree) + 1):
            node = tree[idx]
            if node.is_leaf:
                return node.value
            if feature_vector[node.feature_idx] <= node.threshold:
                idx = node.left
            else:
                idx = node.right
        raise RuntimeError("tree traversal did not terminate at a leaf")

    def score(self, feature_vector: Sequence[float]) -> float:
        """Return the ensemble margin: bias + sum of every tree's leaf value."""
        total = self.bias
        for tree in self.forest:
            total += self._eval_tree(tree, feature_vector)
        return total

    def predict(self, feature_vector: Sequence[float]) -> bool:
        """Positive prediction when the summed margin meets the threshold."""
        return self.score(feature_vector) >= self.threshold

    @classmethod
    def from_lightgbm(
        cls,
        booster,
        threshold: float = 0.0,
    ) -> DecisionTreeClassifier:
        """Build a classifier from a trained LightGBM Booster or dump."""
        model = booster.dump_model() if hasattr(booster, "dump_model") else booster

        forest: list[list[TreeNode]] = []
        for tree_info in model["tree_info"]:
            forest.append(cls._flatten_lgbm_tree(tree_info["tree_structure"]))

        bias = float(model.get("init_score", 0.0) or 0.0)
        return cls(forest=forest, bias=bias, threshold=threshold)

    @staticmethod
    def _flatten_lgbm_tree(root: dict) -> list[TreeNode]:
        """Flatten a LightGBM nested tree dict into a node array."""
        nodes: list[TreeNode] = []

        def add(subtree: dict) -> int:
            if "leaf_value" in subtree or "leaf_index" in subtree:
                nodes.append(
                    TreeNode(is_leaf=True, value=float(subtree.get("leaf_value", 0.0)))
                )
                return len(nodes) - 1

            decision = subtree.get("decision_type", "<=")
            if decision not in ("<=", "<"):
                raise ValueError(
                    f"unsupported LightGBM decision_type {decision!r}; "
                    "only numeric <= splits are supported"
                )

            my_idx = len(nodes)
            nodes.append(TreeNode(is_leaf=False))
            left_idx = add(subtree["left_child"])
            right_idx = add(subtree["right_child"])
            nodes[my_idx] = TreeNode(
                is_leaf=False,
                feature_idx=int(subtree["split_feature"]),
                threshold=float(subtree["threshold"]),
                left=left_idx,
                right=right_idx,
            )
            return my_idx

        add(root)
        return nodes

    def to_rom_rows(self) -> list[dict]:
        """Flatten the whole forest into ROM rows for RTL export."""
        rows: list[dict] = []
        base = 0
        for tree_id, tree in enumerate(self.forest):
            root_addr = base
            for local_idx, node in enumerate(tree):
                rows.append(
                    {
                        "addr": base + local_idx,
                        "tree_id": tree_id,
                        "root_addr": root_addr,
                        "is_leaf": int(node.is_leaf),
                        "feature_idx": node.feature_idx,
                        "threshold": node.threshold,
                        "left_addr": root_addr + node.left,
                        "right_addr": root_addr + node.right,
                        "value": node.value,
                    }
                )
            base += len(tree)
        return rows
