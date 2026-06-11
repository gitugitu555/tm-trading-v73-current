import unittest

from research.v90_cost_model import apply_explicit_costs, explicit_cost_replay


class CostModelTests(unittest.TestCase):
    def test_explicit_costs_reduce_net_return(self):
        trades = [{"signal_id": "a", "gross_return_pct": 0.01, "net_return_pct": 0.01, "pnl_net": 1.0, "pnl": 1.0, "signal_ts_ns": 0}]
        adjusted = apply_explicit_costs(trades, fee_bps_per_side=2, slippage_bps_per_side=2)
        self.assertLess(adjusted[0]["net_return_pct"], adjusted[0]["gross_return_pct"])

    def test_explicit_cost_replay_reports_break_even(self):
        signals = [{"signal_id": "a", "signal_ts_ns": 0, "cvd_slope": 1.0, "cvd_accel": 1.0}]
        paths = {"a": {"signal_id": "a", "gross_return_pct": 0.01, "net_return_pct": 0.01, "pnl_net": 1.0, "pnl": 1.0, "signal_ts_ns": 0, "entry_price": 100.0, "side": "long", "side_int": 1, "bars": [], "max_favorable_excursion_pct": 0.02, "max_adverse_excursion_pct": 0.01}}
        policy = {"name": "demo", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24}
        result = explicit_cost_replay(signals, paths, policy, fee_bps_per_side=1, slippage_bps_per_side=1)
        self.assertIn("cost_break_even_threshold_bps", result)
        self.assertGreaterEqual(result["cost_break_even_threshold_bps"], 0.0)


if __name__ == "__main__":
    unittest.main()
