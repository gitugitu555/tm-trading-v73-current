import unittest
from research.v88_policy_replay import replay_policy

class OccupancyContaminationTests(unittest.TestCase):
    def test_candidate_count_does_not_change_with_occupancy(self):
        signals = [{"signal_id": "a", "signal_ts_ns": 1}, {"signal_id": "b", "signal_ts_ns": 2}]
        path = {"side": "long", "side_int": 1, "entry_price": 100, "signal_ts_ns": 1, "max_favorable_excursion_pct": 0, "max_adverse_excursion_pct": 0, "bars": [{"index": 1, "end_ts_ns": 10, "favorable_pct": 0, "adverse_pct": 0, "close_return_pct": 0}]}
        paths = {"a": {**path, "signal_id": "a"}, "b": {**path, "signal_id": "b"}}
        result = replay_policy(signals, paths, {"bar_exit": 1}, occupancy_mode="single", max_concurrent=1)
        self.assertEqual(result["total_candidate_signals"], 2)
        self.assertEqual(result["tradable_signals"], 1)
