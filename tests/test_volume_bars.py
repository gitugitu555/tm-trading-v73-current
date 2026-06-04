import unittest

from prime.nautilus_compat import AggressorSide
from prime.volume_bars import VolumeBarSampler
from tests.test_v72_phase1 import tick


class VolumeBarSamplerTest(unittest.TestCase):
    def test_emits_when_threshold_reached(self):
        sampler = VolumeBarSampler(threshold_volume=3.0)

        self.assertIsNone(sampler.update(tick(0, 100.0, size=1.0)))
        bar = sampler.update(tick(1, 101.0, size=2.0))

        self.assertIsNotNone(bar)
        self.assertEqual(bar.open, 100.0)
        self.assertEqual(bar.high, 101.0)
        self.assertEqual(bar.low, 100.0)
        self.assertEqual(bar.close, 101.0)
        self.assertEqual(bar.volume, 3.0)
        self.assertEqual(bar.ticks, 2)

    def test_tracks_buy_sell_delta_and_cumulative_delta(self):
        sampler = VolumeBarSampler(threshold_volume=2.0)

        first = sampler.update(tick(0, 100.0, size=2.0, side=AggressorSide.BUYER))
        second = sampler.update(tick(1, 99.0, size=2.0, side=AggressorSide.SELLER))

        self.assertEqual(first.buy_volume, 2.0)
        self.assertEqual(first.sell_volume, 0.0)
        self.assertEqual(first.delta, 2.0)
        self.assertEqual(first.cumulative_delta, 2.0)
        self.assertEqual(second.buy_volume, 0.0)
        self.assertEqual(second.sell_volume, 2.0)
        self.assertEqual(second.delta, -2.0)
        self.assertEqual(second.cumulative_delta, 0.0)

    def test_does_not_split_large_trade(self):
        sampler = VolumeBarSampler(threshold_volume=1.0)

        bar = sampler.update(tick(0, 100.0, size=2.5, side=AggressorSide.BUYER))

        self.assertIsNotNone(bar)
        self.assertEqual(bar.volume, 2.5)
        self.assertEqual(bar.ticks, 1)

    def test_rejects_non_positive_threshold(self):
        with self.assertRaises(ValueError):
            VolumeBarSampler(threshold_volume=0.0)


if __name__ == "__main__":
    unittest.main()
