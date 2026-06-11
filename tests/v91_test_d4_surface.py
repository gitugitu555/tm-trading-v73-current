import unittest

from prime.volume_bars import VolumeBar
from research.v91_d4_surface import rebar_volume_bars, surface_metrics


def bar(idx: int) -> VolumeBar:
    return VolumeBar(idx, idx + 1, 100, 101, 99, 100 + idx, 100, 60, 40, 20, (idx + 1) * 20, 10)


class D4SurfaceTests(unittest.TestCase):
    def test_rebar_is_deterministic(self):
        bars = [bar(i) for i in range(10)]
        self.assertEqual(rebar_volume_bars(bars, 500), rebar_volume_bars(bars, 500))
        self.assertEqual(len(rebar_volume_bars(bars, 500)), 2)

    def test_cost_ladder_is_subtracted_from_mean(self):
        metrics = surface_metrics([(1, 0.001), (-1, -0.001)], bootstrap_samples=20, seed=1)
        self.assertAlmostEqual(metrics["mean_signed_return_bps"], 10.0)
        self.assertAlmostEqual(metrics["net_expectancy_bps"]["5"], 5.0)


if __name__ == "__main__":
    unittest.main()
