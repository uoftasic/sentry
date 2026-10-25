from __future__ import annotations

from math import log2

from ..event import Event, Op
from ..tracker import FeatureTracker


class EntropyTracker(FeatureTracker):
    """Estimates write entropy and tracks entropy statistics over a window."""

    def __init__(
        self,
        sample_size: int = 256,
        symbol_bits: int = 8,
        log_method: str = "lut",
        fraction_bits: int = 3,
    ) -> None:
        if sample_size <= 0 or sample_size & (sample_size - 1):
            raise ValueError("sample_size must be a positive power of two")
        if symbol_bits not in (4, 8):
            raise ValueError("symbol_bits must be 4 or 8")
        if log_method not in ("lut", "priority"):
            raise ValueError("log_method must be 'lut' or 'priority'")
        if not 1 <= fraction_bits <= 8:
            raise ValueError("fraction_bits must be between 1 and 8")

        self.sample_size = sample_size
        self.symbol_bits = symbol_bits
        self.log_method = log_method
        self.fraction_bits = fraction_bits
        symbol_count = sample_size if symbol_bits == 8 else sample_size * 2
        # In hardware this is a ROM indexed by a histogram counter value.
        self._count_log2_lut = (
            tuple(
                0.0 if count == 0 else count * log2(count)
                for count in range(symbol_count + 1)
            )
            if log_method == "lut"
            else ()
        )
        # The priority path needs only 2**fraction_bits fractional-log entries.
        self._fraction_log2_lut = (
            tuple(
                log2(1 + index / (1 << fraction_bits))
                for index in range(1 << fraction_bits)
            )
            if log_method == "priority"
            else ()
        )
        self.reset_window()

    def estimate_entropy(self, data_sample: bytes) -> float:
        """Estimate Shannon entropy in bits per byte from one write sample."""
        if len(data_sample) < self.sample_size:
            raise ValueError(
                f"data_sample must contain at least {self.sample_size} bytes"
            )

        histogram = [0] * (1 << self.symbol_bits)
        for value in data_sample[:self.sample_size]:
            if self.symbol_bits == 8:
                histogram[value] += 1
            else:
                histogram[value >> 4] += 1
                histogram[value & 0x0F] += 1

        symbol_count = (
            self.sample_size if self.symbol_bits == 8 else self.sample_size * 2
        )
        if self.log_method == "lut":
            weighted_logs = sum(
                self._count_log2_lut[count] for count in histogram
            )
        else:
            weighted_logs = 0.0
            fraction_mask = (1 << self.fraction_bits) - 1
            for count in histogram:
                if count == 0:
                    continue
                msb = count.bit_length() - 1
                shift = msb - self.fraction_bits
                fraction_index = (
                    count >> shift if shift >= 0 else count << -shift
                ) & fraction_mask
                weighted_logs += count * (
                    msb + self._fraction_log2_lut[fraction_index]
                )

        entropy = (symbol_count.bit_length() - 1) - weighted_logs / symbol_count
        # Two nibbles approximate one byte while requiring only 16 counters.
        return entropy if self.symbol_bits == 8 else entropy * 2

    def update(self, event: Event) -> None:
        """Add a write's sampled or precomputed entropy to this window."""
        if event.op != Op.WRITE:
            return

        entropy = (
            self.estimate_entropy(event.data_sample)
            if event.data_sample is not None
            else event.entropy
        )
        if entropy is None:
            return

        self._write_count += 1
        self._entropy_sum += entropy
        self._entropy_squared_sum += entropy * entropy

    def features(self) -> dict[str, int | float]:
        """Return average and population variance of available write entropy."""
        if self._write_count == 0:
            return {
                "average_write_entropy": 0.0,
                "write_entropy_variance": 0.0,
            }

        average = self._entropy_sum / self._write_count
        return {
            "average_write_entropy": average,
            "write_entropy_variance": max(
                0.0,
                self._entropy_squared_sum / self._write_count - average * average,
            ),
        }

    def reset_window(self) -> None:
        """Clear per-window entropy state."""
        self._write_count = 0
        self._entropy_sum = 0.0
        self._entropy_squared_sum = 0.0


if __name__ == "__main__":
    constant_sample = bytes(256)
    biased_sample = bytes(180) + bytes([0xFF]) * 76
    biased_entropy = -(180 / 256 * log2(180 / 256) + 76 / 256 * log2(76 / 256))
    samples = (
        ("constant", constant_sample, 0.0),
        ("biased two values", biased_sample, biased_entropy),
        ("two values", bytes((0x00, 0xFF)) * 128, 1.0),
        ("four values", bytes((0x00, 0x55, 0xAA, 0xFF)) * 64, 2.0),
        ("sixteen values", bytes(range(16)) * 16, 4.0),
        ("all byte values", bytes(range(256)), 8.0),
    )

    for log_method in ("lut", "priority"):
        for bits in (8, 4):
            tracker = EntropyTracker(symbol_bits=bits, log_method=log_method)
            entropies = []
            for name, data, expected_byte_entropy in samples:
                entropy = tracker.estimate_entropy(data)
                entropies.append(entropy)
                print(
                    f"{log_method}, {bits}-bit histogram ({name}): "
                    f"data={data}, entropy={entropy}"
                )
                if bits == 8:
                    tolerance = 1e-12 if log_method == "lut" else 0.1
                    assert abs(entropy - expected_byte_entropy) < tolerance
            assert entropies == sorted(entropies)
            assert entropies[0] == 0.0 and entropies[-1] == 8.0

    tracker = EntropyTracker()
    tracker.update(Event(Op.READ, 0, 0, 1, entropy=8.0))
    tracker.update(Event(Op.WRITE, 1, 0, 1))
    tracker.update(Event(Op.WRITE, 2, 0, 1, entropy=8.0))
    tracker.update(Event(Op.WRITE, 3, 0, 1, data_sample=constant_sample))
    assert tracker.features() == {
        "average_write_entropy": 4.0,
        "write_entropy_variance": 16.0,
    }

    tracker.reset_window()
    assert tracker.features() == {
        "average_write_entropy": 0.0,
        "write_entropy_variance": 0.0,
    }
    print("EntropyTracker tests passed")
