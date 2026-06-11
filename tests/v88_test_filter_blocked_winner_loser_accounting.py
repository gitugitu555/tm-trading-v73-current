import unittest
from research.v88_signal_filters import filter_value

class FilterValueTests(unittest.TestCase):
    def test_blocked_value(self):
        signals = [{"signal_id": "w", "keep": False}, {"signal_id": "l", "keep": False}]
        trades = {"w": {"net_return_pct": .01}, "l": {"net_return_pct": -.03}}
        self.assertAlmostEqual(filter_value(signals, trades, lambda s: s["keep"])["net_filter_value"], .02)
