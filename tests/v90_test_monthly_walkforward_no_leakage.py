import unittest
from unittest.mock import patch

from research.v90_walkforward import build_monthly_walkforward_report


class MonthlyWalkForwardNoLeakageTests(unittest.TestCase):
    def test_train_and_test_months_do_not_overlap(self):
        signals = []
        paths = {}
        for idx, month in enumerate(["2020-01", "2020-02", "2020-03", "2020-04", "2020-05", "2020-06"]):
            ts = 1577836800000000000 + idx * 30 * 24 * 3600 * 1_000_000_000
            signal_id = f"s{idx}"
            signals.append({"signal_id": signal_id, "signal_ts_ns": ts})
            paths[signal_id] = {"signal_id": signal_id, "signal_ts_ns": ts, "gross_return_pct": 0.01, "net_return_pct": 0.01, "pnl_net": 1.0, "pnl": 1.0, "bars": []}

        fake_policy = {"name": "demo", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24}
        with patch("research.v90_walkforward.policy_space", return_value=[fake_policy]), patch(
            "research.v90_walkforward.replay_policy",
            side_effect=lambda signals, paths, policy, occupancy_mode="independent", max_concurrent=1: {
                "trades": [
                    {**paths[signal["signal_id"]], "signal_id": signal["signal_id"], "gross_return_pct": 0.01, "net_return_pct": 0.01, "pnl_net": 1.0, "pnl": 1.0, "signal_ts_ns": signal["signal_ts_ns"]}
                    for signal in signals
                ],
                "summary": {"sharpe": 1.0},
            },
        ):
            report = build_monthly_walkforward_report(signals, paths, protocols=[(2, 1)])
        folds = report["protocols"][0]["folds"]
        self.assertTrue(all(set(fold["train_months"]).isdisjoint(fold["test_months"]) for fold in folds))


if __name__ == "__main__":
    unittest.main()

