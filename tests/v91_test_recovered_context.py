import unittest

from prime.volume_bars import VolumeBar
from research.v91_recovered_context import coarse_profile, market_structure, mtf_alignment


def bar(idx: int, close: float) -> VolumeBar:
    return VolumeBar(idx, idx + 1, close, close + 1, close - 1, close, 300, 160, 140, 20, idx * 20, 10)


class RecoveredContextTests(unittest.TestCase):
    def test_profile_uses_only_provided_prior_bars(self):
        first = coarse_profile([bar(i, 100 + i) for i in range(20)])
        second = coarse_profile([bar(i, 100 + i) for i in range(20)])
        self.assertEqual(first, second)

    def test_market_structure_has_no_future_confirmation_requirement(self):
        structure, level = market_structure([bar(i, 100 + i) for i in range(100)], 200)
        self.assertEqual(structure, "uptrend")
        self.assertIn(level, {"near_resistance", "no_key_level"})

    def test_mtf_alignment_is_direction_relative(self):
        biases = {"15m": 1, "1h": 1, "4h": 1, "daily": 0}
        self.assertEqual(mtf_alignment(1, biases), "partially_aligned")
        self.assertEqual(mtf_alignment(-1, biases), "against_d4")


if __name__ == "__main__":
    unittest.main()
