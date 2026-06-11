import unittest
from research.v88_tpsl_policies import replay_tpsl

class FirstTouchTests(unittest.TestCase):
    def test_target_first(self):
        path = {"signal_id": "x", "signal_ts_ns": 1, "side": "long", "side_int": 1, "entry_price": 100, "max_favorable_excursion_pct": .01, "max_adverse_excursion_pct": 0, "bars": [{"index": 1, "end_ts_ns": 2, "favorable_pct": .01, "adverse_pct": 0, "close_return_pct": .005}]}
        self.assertEqual(replay_tpsl(path, {"target_pct": .005, "stop_pct": .01, "bar_exit": 1})["exit_reason"], "TARGET")

    def test_ambiguous_same_bar_defaults_stop_first(self):
        path = {"signal_id": "x", "signal_ts_ns": 1, "side": "long", "side_int": 1, "entry_price": 100, "max_favorable_excursion_pct": .01, "max_adverse_excursion_pct": .01, "bars": [{"index": 1, "end_ts_ns": 2, "favorable_pct": .01, "adverse_pct": .01, "close_return_pct": 0}]}
        self.assertEqual(replay_tpsl(path, {"target_pct": .005, "stop_pct": .005, "bar_exit": 1})["exit_reason"], "STOP")
