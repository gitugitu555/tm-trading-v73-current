import unittest
from research.v88_policy_replay import replay_policy

class PolicyOccupancyTests(unittest.TestCase):
    def test_independent_executes_overlapping_signals(self):
        signals = [{"signal_id": x, "signal_ts_ns": i} for i, x in enumerate(("a", "b"), 1)]
        base = {"side": "long", "side_int": 1, "entry_price": 100, "max_favorable_excursion_pct": 0, "max_adverse_excursion_pct": 0, "bars": [{"index": 1, "end_ts_ns": 10, "favorable_pct": 0, "adverse_pct": 0, "close_return_pct": 0}]}
        paths = {x: {**base, "signal_id": x, "signal_ts_ns": i} for i, x in enumerate(("a", "b"), 1)}
        self.assertEqual(replay_policy(signals, paths, {"bar_exit": 1}, occupancy_mode="independent")["executed_trades"], 2)
