from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TreeNode:
    """One generic decision-tree node."""

    feature_index: int | None = None
    threshold: float | None = None
    left: int | None = None
    right: int | None = None
    value: float | None = None

    @property
    def is_leaf(self) -> bool:
        return self.value is not None


class DecisionTree:
    """Generic tree evaluator suitable for later RTL translation."""

    def __init__(self, nodes: list[TreeNode], root_index: int = 0) -> None:
        if not nodes:
            raise ValueError("tree must contain at least one node")

        self.nodes = nodes
        self.root_index = root_index

    def score(self, vector: list[float]) -> float:
        index = self.root_index

        for _ in range(len(self.nodes) + 1):
            node = self.nodes[index]

            if node.is_leaf:
                assert node.value is not None
                return node.value

            if (
                node.feature_index is None
                or node.threshold is None
                or node.left is None
                or node.right is None
            ):
                raise ValueError(f"malformed internal node at index {index}")

            value = vector[node.feature_index]
            index = node.left if value <= node.threshold else node.right

        raise ValueError("tree appears to contain a cycle")

    def predict(self, vector: list[float], threshold: float = 0.5) -> bool:
        return self.score(vector) >= threshold
