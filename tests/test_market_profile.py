import unittest

from features.market_profile import MarketProfileEngine
from prime.volume_bars import VolumeBar


class MarketProfileTests(unittest.TestCase):
    def test_profile_identifies_poc_and_value_context(self) -> None:
        bars = [
            VolumeBar(0, 1, 100.0, 101.0, 99.5, 100.5, 100.0, 60.0, 40.0, 20.0, 20.0, 10),
            VolumeBar(1, 2, 100.5, 101.5, 100.0, 101.0, 120.0, 70.0, 50.0, 20.0, 40.0, 10),
            VolumeBar(2, 3, 101.0, 101.5, 100.5, 101.2, 110.0, 60.0, 50.0, 10.0, 50.0, 10),
        ]
        snap = MarketProfileEngine(tick_size=0.5).update(bars, current_price=101.2)
        self.assertIsNotNone(snap.poc)
        self.assertIn(snap.current_value_context, {"IN_VALUE", "ABOVE_VALUE", "BELOW_VALUE"})
        self.assertGreaterEqual(snap.atr_current, 0.0)
        self.assertGreaterEqual(snap.atr_used_pct, 0.0)

    def test_profile_can_detect_lvn(self) -> None:
        bars = [
            VolumeBar(0, 1, 100.0, 100.5, 99.5, 100.0, 100.0, 60.0, 40.0, 20.0, 20.0, 10),
            VolumeBar(1, 2, 101.0, 101.5, 100.5, 101.0, 20.0, 10.0, 10.0, 0.0, 20.0, 10),
            VolumeBar(2, 3, 102.0, 102.5, 101.5, 102.0, 100.0, 60.0, 40.0, 20.0, 40.0, 10),
        ]
        snap = MarketProfileEngine(tick_size=0.5).update(bars, current_price=101.0)
        self.assertTrue(snap.lvn_zones)


if __name__ == "__main__":
    unittest.main()
