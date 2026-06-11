import unittest

from prime.volume_bars import VolumeBarSampler
from research.v87_execution import classify_partial_predictions, decay_filter_value


class Tick:
    def __init__(self, price, size, side, ts):
        self.price = price
        self.size = size
        self.aggressor_side = side
        self.ts_event = ts


class ExecutionTimingTests(unittest.TestCase):
    def test_partial_snapshot_does_not_emit_or_reset_bar(self):
        sampler = VolumeBarSampler(10)
        sampler.update(Tick(100, 4, "BUYER", 1))
        partial = sampler.partial_snapshot()
        self.assertEqual(partial.volume, 4)
        self.assertEqual(sampler.progress, 0.4)
        emitted = sampler.update(Tick(101, 6, "SELLER", 2))
        self.assertEqual(emitted.volume, 10)

    def test_partial_precision_recall(self):
        result = classify_partial_predictions(
            [
                {"partial_fraction": 0.5, "partial_signal": True, "final_signal": True, "partial_side": 1, "final_side": 1},
                {"partial_fraction": 0.5, "partial_signal": True, "final_signal": False, "partial_side": 1, "final_side": None},
            ]
        )["0.5"]
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 1.0)

    def test_partial_threshold_keys_do_not_collide(self):
        result = classify_partial_predictions(
            [
                {"partial_fraction": 0.2, "partial_signal": False, "final_signal": False, "partial_side": None, "final_side": None},
                {"partial_fraction": 0.25, "partial_signal": False, "final_signal": False, "partial_side": None, "final_side": None},
            ]
        )
        self.assertIn("0.2", result)
        self.assertIn("0.25", result)

    def test_decay_filter_accounts_for_blocked_pnl(self):
        rows = [
            {"lag0_close": 100, "lag1_open": 100.01, "pnl": 2},
            {"lag0_close": 100, "lag1_open": 101, "pnl": -5},
        ]
        result = decay_filter_value(rows, max_move_pct=0.001)
        self.assertEqual(result["trades_allowed"], 1)
        self.assertEqual(result["net_filter_value"], 5)
