import unittest
from prime.volume_bars import VolumeBar
from research.v88_trade_path import reconstruct_path

class TradePathTests(unittest.TestCase):
    def test_long_mfe_mae(self):
        bars = [VolumeBar(0, 1, 100, 100, 100, 100, 300, 0, 0, 0, 0, 1), VolumeBar(1, 2, 100, 102, 99, 101, 300, 0, 0, 0, 0, 1)]
        path = reconstruct_path({"signal_id": "x", "bar_id": 0, "signal_ts_ns": 1, "side": "long", "side_int": 1, "entry_reference_price": 100}, bars)
        self.assertEqual(path["max_favorable_excursion_pct"], 0.02)
        self.assertEqual(path["max_adverse_excursion_pct"], 0.01)
