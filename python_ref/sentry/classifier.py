from __future__ import annotations

from math import floor
from random import Random


def _quantize(value: float, fraction_bits: int) -> int:
    """Convert a real value to a signed fixed-point integer.

    Rounds half up (add half an LSB, then truncate), as RTL usually does.
    Python's round() would send halves to the even integer instead.
    """
    return floor(value * (1 << fraction_bits) + 0.5)


def _check_fraction_bits(fraction_bits: int | None) -> None:
    if fraction_bits is not None and not 0 <= fraction_bits <= 16:
        raise ValueError("fraction_bits must be None or between 0 and 16")


class WeightedSumClassifier:
    """Generic weighted-sum classifier.

    This class must only see an ordered numeric feature vector. It must not
    contain feature-specific logic.

    score = bias + sum(weights[i] * feature_vector[i])
    predict = score > threshold

    In hardware this is one multiply-accumulate unit stepping through the
    feature vector, followed by one comparator. With ``fraction_bits`` set,
    weights, bias, threshold and features are rounded to fixed-point integers
    so the Python result matches an integer RTL datapath bit for bit.
    Products of two Q.f values have 2f fraction bits, so the bias and the
    threshold are aligned to that scale with a left shift, not a multiply.
    """

    def __init__(
        self,
        weights: list[float],
        bias: float = 0.0,
        threshold: float = 0.0,
        fraction_bits: int | None = None,
    ) -> None:
        if not weights:
            raise ValueError("weights must contain at least one value")
        _check_fraction_bits(fraction_bits)

        self.weights = [float(weight) for weight in weights]
        self.bias = float(bias)
        self.threshold = float(threshold)
        self.fraction_bits = fraction_bits

        if fraction_bits is not None:
            # These are the constants that would be stored in registers/ROM.
            self.quantized_weights = [
                _quantize(weight, fraction_bits) for weight in self.weights
            ]
            self.quantized_bias = _quantize(self.bias, fraction_bits)
            self.quantized_threshold = _quantize(self.threshold, fraction_bits)

    @property
    def num_features(self) -> int:
        return len(self.weights)

    def _check_vector(self, feature_vector: list[float]) -> None:
        if len(feature_vector) != len(self.weights):
            raise ValueError(
                f"expected {len(self.weights)} features, "
                f"got {len(feature_vector)}"
            )

    def _accumulate(self, feature_vector: list[float]) -> int:
        """Integer accumulator value at 2 * fraction_bits fraction bits."""
        fraction_bits = self.fraction_bits
        assert fraction_bits is not None
        accumulator = self.quantized_bias << fraction_bits
        for weight, feature in zip(self.quantized_weights, feature_vector):
            accumulator += weight * _quantize(feature, fraction_bits)
        return accumulator

    def score(self, feature_vector: list[float]) -> float:
        """Return bias + sum(weight * feature)."""
        self._check_vector(feature_vector)
        if self.fraction_bits is None:
            return self.bias + sum(
                weight * feature
                for weight, feature in zip(self.weights, feature_vector)
            )
        return self._accumulate(feature_vector) / (1 << (2 * self.fraction_bits))

    def predict(self, feature_vector: list[float]) -> bool:
        """Return True when the score is strictly above the threshold."""
        self._check_vector(feature_vector)
        if self.fraction_bits is None:
            return self.score(feature_vector) > self.threshold
        threshold = self.quantized_threshold << self.fraction_bits
        return self._accumulate(feature_vector) > threshold


class TsetlinClassifier:
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
        # Every counter starts one step below "include", so every clause is
        # empty and the untrained machine scores 0.
        self.states = [
            [self._include_state - 1] * self.num_literals
            for _ in range(num_clauses)
        ]

    @property
    def num_features(self) -> int:
        return len(self.cutoffs)

    def _check_vector(self, feature_vector: list[float]) -> None:
        if len(feature_vector) != len(self.cutoffs):
            raise ValueError(
                f"expected {len(self.cutoffs)} features, "
                f"got {len(feature_vector)}"
            )

    def encode(self, feature_vector: list[float]) -> list[int]:
        """Thermometer-encode a feature vector into bits."""
        self._check_vector(feature_vector)
        return [
            int(feature > cutoff)
            for feature, feature_cutoffs in zip(feature_vector, self.cutoffs)
            for cutoff in feature_cutoffs
        ]

    def _literals(self, feature_vector: list[float]) -> list[int]:
        bits = self.encode(feature_vector)
        return bits + [1 - bit for bit in bits]

    @property
    def clause_masks(self) -> list[int]:
        """Include mask per clause, bit k set when literal k is included.

        These are the constants an inference-only RTL block would store.
        """
        return [
            sum(
                1 << k
                for k, state in enumerate(clause_states)
                if state >= self._include_state
            )
            for clause_states in self.states
        ]

    def _clause_outputs(self, literals: list[int], training: bool) -> list[int]:
        """Evaluate every clause.

        An empty clause outputs 1 while training so it can start learning,
        and 0 at inference so it cannot vote.
        """
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

    def score(self, feature_vector: list[float]) -> int:
        """Return positive clause votes minus negative clause votes."""
        literals = self._literals(feature_vector)
        return self._vote(self._clause_outputs(literals, training=False))

    def predict(self, feature_vector: list[float]) -> bool:
        """Return True when the vote is strictly above the threshold."""
        return self.score(feature_vector) > self.threshold

    def update(self, feature_vector: list[float], label: bool) -> None:
        """Train on one labelled sample, as on-chip learning would."""
        literals = self._literals(feature_vector)
        outputs = self._clause_outputs(literals, training=True)
        margin = self.vote_margin
        vote = max(-margin, min(margin, self._vote(outputs)))

        for clause, output in enumerate(outputs):
            positive = clause % 2 == 0
            if label:
                # Push the vote up: grow positive clauses, block negative ones.
                chance = margin - vote
                type_i = positive
            else:
                # Push the vote down: grow negative clauses, block positive ones.
                chance = margin + vote
                type_i = not positive
            # Feedback probability is chance / (2T).
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
        """Make the clause match the current input more tightly.

        When the clause fires, literals that are 1 move toward include with
        chance (s-1)/s. Every other literal moves toward exclude with
        chance 1/s, which keeps clauses from growing too specific.
        """
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
        """Stop the clause from firing on the current input.

        When the clause fires, every excluded literal that is 0 moves toward
        include. Including any one of them makes the clause output 0 here.
        """
        if not output:
            return
        states = self.states[clause]
        for k, literal in enumerate(literals):
            if not literal and states[k] < self._include_state:
                states[k] += 1


if __name__ == "__main__":
    # Weighted sum: 1 + 2*3 + (-1)*4 = 3.
    weighted = WeightedSumClassifier([2.0, -1.0], bias=1.0, threshold=2.5)
    assert weighted.score([3.0, 4.0]) == 3.0
    assert weighted.predict([3.0, 4.0])
    assert not weighted.predict([1.0, 4.0])

    quantized_weighted = WeightedSumClassifier(
        [2.0, -1.0], bias=1.0, threshold=2.5, fraction_bits=4
    )
    assert quantized_weighted.score([3.0, 4.0]) == 3.0
    assert quantized_weighted.predict([3.0, 4.0])
    # 0.3 rounds to 5/16, so the quantized score differs slightly from float.
    assert abs(quantized_weighted.score([0.3, 0.0]) - 1.6) < 1 / 16

    try:
        weighted.score([1.0])
    except ValueError:
        pass
    else:
        raise AssertionError("wrong vector length must be rejected")

    # Thermometer encoding matches the table in the design notes.
    entropy_cutoffs = [[5.0, 6.0, 7.0, 7.5]]
    assert TsetlinClassifier(entropy_cutoffs).encode([4.2]) == [0, 0, 0, 0]
    assert TsetlinClassifier(entropy_cutoffs).encode([6.3]) == [1, 1, 0, 0]
    assert TsetlinClassifier(entropy_cutoffs).encode([7.2]) == [1, 1, 1, 0]
    assert TsetlinClassifier(entropy_cutoffs).encode([7.9]) == [1, 1, 1, 1]

    # Hand-set clauses. Bits are x0>5, x0>6, x0>7, x1>0.5, so literal 2 is
    # "x0>7", literal 3 is "x1>0.5" and literal 4 + 2 = 6 is "not x0>7".
    cutoffs = [[5.0, 6.0, 7.0], [0.5]]
    tsetlin = TsetlinClassifier(cutoffs, num_clauses=2)
    assert tsetlin.score([7.9, 0.9]) == 0  # Empty clauses never vote.
    include = tsetlin._include_state
    tsetlin.states[0][2] = include  # Positive clause: x0>7 and x1>0.5.
    tsetlin.states[0][3] = include
    tsetlin.states[1][6] = include  # Negative clause: not x0>7.
    assert tsetlin.clause_masks == [0b1100, 0b0100_0000]
    assert tsetlin.score([7.5, 0.9]) == 1 and tsetlin.predict([7.5, 0.9])
    assert tsetlin.score([7.5, 0.1]) == 0 and not tsetlin.predict([7.5, 0.1])
    assert tsetlin.score([3.0, 0.9]) == -1 and not tsetlin.predict([3.0, 0.9])

    # Training learns "x0 > 7 and x1 > 0.5" from examples.
    vectors = [[x0, x1] for x0 in (3.0, 5.5, 6.5, 7.5, 7.9) for x1 in (0.1, 0.9)]
    labels = [x0 > 7 and x1 > 0.5 for x0, x1 in vectors]
    trained = TsetlinClassifier(cutoffs, num_clauses=8, seed=1)
    trained.fit(vectors, labels, epochs=200)
    correct = sum(
        trained.predict(vector) == label
        for vector, label in zip(vectors, labels)
    )
    assert correct >= 9, f"trained Tsetlin machine got {correct}/10 right"

    print("Classifier tests passed")
