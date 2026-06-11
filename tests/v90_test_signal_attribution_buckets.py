import unittest

from research.v90_signal_attribution import signal_attribution


class SignalAttributionTests(unittest.TestCase):
    def test_bucket_report_contains_robust_section(self):
        signals = [{"signal_id": "a", "signal_ts_ns": 1590000000000000000, "signal_strength": 0.5, "divergence_score": 0.4, "volume": 10.0, "delta": 2.0, "bar_start_ts_ns": 0, "bar_end_ts_ns": 10, "bar_open": 100.0, "bar_close": 101.0, "side": "long"}]
        paths = {"a": {"signal_id": "a", "signal_ts_ns": 1590000000000000000, "max_favorable_excursion_pct": 0.02, "max_adverse_excursion_pct": 0.01, "return_at_bar_exit": {"24": 0.005}, "gross_return_pct": 0.01, "net_return_pct": 0.01, "pnl_net": 1.0, "pnl": 1.0, "bars": []}}
        report = signal_attribution(signals, paths)
        self.assertIn("buckets", report)
        self.assertIn("robust_buckets", report)


if __name__ == "__main__":
    unittest.main()

