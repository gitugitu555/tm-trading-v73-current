import unittest

from features.atr_context import ATRContextEngine
from prime.volume_bars import VolumeBar


class ATRContextTests(unittest.TestCase):
    def test_atr_context_identifies_exhaustion_and_trend_stack(self) -> None:
        bars = []
        for idx in range(120):
            base = 100.0 + idx * 0.5
            bars.append(
                VolumeBar(
                    idx,
                    idx + 1,
                    base - 0.25,
                    base + 0.75,
                    base - 0.75,
                    base + 0.25,
                    100.0,
                    60.0,
                    40.0,
                    20.0,
                    20.0,
                    10,
                )
            )

        snap = ATRContextEngine().update(bars, current_price=bars[-1].close)
        self.assertGreater(snap.atr_current, 0.0)
        self.assertGreater(snap.atr_used_pct, 0.0)
        self.assertEqual(snap.trend_stack, "BULL_STACK")
        self.assertGreater(snap.realized_volatility, 0.0)
        self.assertGreater(snap.atr_percentile, 0.0)

    def test_empty_sequence_returns_defaults(self) -> None:
        snap = ATRContextEngine().update([])
        self.assertEqual(snap.atr_current, 0.0)
        self.assertEqual(snap.trend_stack, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
