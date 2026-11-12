from __future__ import annotations

from collections.abc import Sequence
from random import Random

from ..classifier import Classifier


class TsetlinClassifier(Classifier):
    """Binary Tsetlin machine over thermometer-encoded features.

    Like the weighted-sum classifier, it only sees an ordered numeric feature
    vector. The per-feature cutoffs are configuration, not feature logic.

    Inference:
    1. Thermometer encoding turns feature i into one bit per cutoff, where
       each bit is ``feature_vector[i] > cutoff``.
    2. The literals are every bit followed by every inverted bit.
    3. Each clause is the AND of the literals it includes. In hardware a
       clause is ``(literals & mask) == mask`` with one include mask per
       clause, so no adders or multipliers are needed.
    4. Even-numbered clauses vote for "suspicious", odd-numbered clauses vote
       against. score = positive votes - negative votes, and predict is
       score > threshold.

    Training uses one saturating counter (a Tsetlin automaton) per clause per
    literal. A literal is included when its counter is in the upper half of
    its range. Every probability is an integer compare against a random
    number, so an LFSR can supply the randomness on chip. Python's Random
    with a fixed seed stands in for it here.
    """

    def __init__(
        self,
        cutoffs: list[list[float]],
        num_clauses: int = 4,
        vote_margin: int = 4,
        specificity: int = 3,
        state_bits: int = 4,
        threshold: int = 0,
        seed: int = 0,
    ) -> None:
        """Create an untrained machine.

        cutoffs: ascending thermometer cutoffs for each feature, in order.
        num_clauses: total clauses, half positive and half negative.
        vote_margin: the T parameter. Votes are clamped to [-T, T] during
            training, which stops learning once a sample is classified with
            enough margin.
        specificity: the s parameter. Larger values make clauses include
            more literals, so they match narrower patterns.
        state_bits: width of each saturating counter.
        """
        if not cutoffs:
            raise ValueError("cutoffs must describe at least one feature")
        for feature_cutoffs in cutoffs:
            if not feature_cutoffs:
                raise ValueError("every feature needs at least one cutoff")
            if any(a >= b for a, b in zip(feature_cutoffs, feature_cutoffs[1:])):
                raise ValueError("cutoffs must be strictly ascending")
        if num_clauses < 2 or num_clauses % 2:
            raise ValueError("num_clauses must be an even number of at least 2")
        if vote_margin < 1:
            raise ValueError("vote_margin must be at least 1")
        if specificity < 2:
            raise ValueError("specificity must be at least 2")
        if not 1 <= state_bits <= 8:
            raise ValueError("state_bits must be between 1 and 8")

        self.cutoffs = [[float(cutoff) for cutoff in c] for c in cutoffs]
        self.num_clauses = num_clauses
        self.vote_margin = vote_margin
        self.specificity = specificity
        self.state_bits = state_bits
        self.threshold = threshold

        self.num_bits = sum(len(c) for c in self.cutoffs)
        self.num_literals = 2 * self.num_bits
        self._include_state = 1 << (state_bits - 1)
        self._max_state = (1 << state_bits) - 1
        self._rng = Random(seed)
        self.states = [
            [self._include_state - 1] * self.num_literals
            for _ in range(num_clauses)
        ]

    @property
    def num_features(self) -> int:
        return len(self.cutoffs)

    def _check_vector(self, feature_vector: Sequence[float]) -> None:
        if len(feature_vector) != len(self.cutoffs):
            raise ValueError(
                f"expected {len(self.cutoffs)} features, "
                f"got {len(feature_vector)}"
            )

    def encode(self, feature_vector: Sequence[float]) -> list[int]:
        """Thermometer-encode a feature vector into bits."""
        self._check_vector(feature_vector)
        return [
            int(feature > cutoff)
            for feature, feature_cutoffs in zip(feature_vector, self.cutoffs)
            for cutoff in feature_cutoffs
        ]

    def _literals(self, feature_vector: Sequence[float]) -> list[int]:
        bits = self.encode(feature_vector)
        return bits + [1 - bit for bit in bits]

    @property
    def clause_masks(self) -> list[int]:
        """Include mask per clause, bit k set when literal k is included."""
        return [
            sum(
                1 << k
                for k, state in enumerate(clause_states)
                if state >= self._include_state
            )
            for clause_states in self.states
        ]

    def _clause_outputs(self, literals: list[int], training: bool) -> list[int]:
        """Evaluate every clause."""
        literal_word = sum(bit << k for k, bit in enumerate(literals))
        return [
            int(training) if mask == 0 else int((literal_word & mask) == mask)
            for mask in self.clause_masks
        ]

    @staticmethod
    def _vote(clause_outputs: list[int]) -> int:
        return sum(
            output if index % 2 == 0 else -output
            for index, output in enumerate(clause_outputs)
        )

    def score(self, feature_vector: Sequence[float]) -> int:
        """Return positive clause votes minus negative clause votes."""
        literals = self._literals(feature_vector)
        return self._vote(self._clause_outputs(literals, training=False))

    def predict(self, feature_vector: Sequence[float]) -> bool:
        """Return True when the vote is strictly above the threshold."""
        return self.score(feature_vector) > self.threshold

    def update(self, feature_vector: Sequence[float], label: bool) -> None:
        """Train on one labelled sample, as on-chip learning would."""
        literals = self._literals(feature_vector)
        outputs = self._clause_outputs(literals, training=True)
        margin = self.vote_margin
        vote = max(-margin, min(margin, self._vote(outputs)))

        for clause, output in enumerate(outputs):
            positive = clause % 2 == 0
            if label:
                chance = margin - vote
                type_i = positive
            else:
                chance = margin + vote
                type_i = not positive
            if self._rng.randrange(2 * margin) >= chance:
                continue
            if type_i:
                self._type_i_feedback(clause, literals, output)
            else:
                self._type_ii_feedback(clause, literals, output)

    def fit(
        self,
        feature_vectors: list[list[float]],
        labels: list[bool],
        epochs: int = 10,
    ) -> TsetlinClassifier:
        """Train for several passes over a labelled dataset."""
        if len(feature_vectors) != len(labels):
            raise ValueError("feature_vectors and labels must be the same length")
        for _ in range(epochs):
            for feature_vector, label in zip(feature_vectors, labels):
                self.update(feature_vector, bool(label))
        return self

    def _type_i_feedback(
        self, clause: int, literals: list[int], output: int
    ) -> None:
        """Make the clause match the current input more tightly."""
        states = self.states[clause]
        for k, literal in enumerate(literals):
            if output and literal:
                if self._rng.randrange(self.specificity) != 0:
                    states[k] = min(states[k] + 1, self._max_state)
            elif self._rng.randrange(self.specificity) == 0:
                states[k] = max(states[k] - 1, 0)

    def _type_ii_feedback(
        self, clause: int, literals: list[int], output: int
    ) -> None:
        """Stop the clause from firing on the current input."""
        if not output:
            return
        states = self.states[clause]
        for k, literal in enumerate(literals):
            if not literal and states[k] < self._include_state:
                states[k] += 1
