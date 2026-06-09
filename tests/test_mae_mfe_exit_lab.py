import json
import tempfile
import unittest
from pathlib import Path

from research.mae_mfe_exit_lab import MAEMFEExitLab, TradePath, PercentileExitResult, MAEMFEReport

class MAEMFEExitLabTests(unittest.TestCase):
    def test_mae_mfe_exit_lab_flow(self) -> None:
        lab = MAEMFEExitLab()
        self.assertEqual(len(lab), 0)

        # Ingestion tests
        p1 = lab.add_from_paper_trade(
            trade_id="t1",
            signal_id="s1",
            symbol="BTCUSDT",
            side=1,
            entry_ts_ns=1_000_000_000,
            exit_ts_ns=4_600_000_000,
            entry_price=100.0,
            exit_price=101.0,
            max_adverse=0.001,
            max_favorable=0.005,
            pnl=10.0,
            exit_reason="TARGET",
            signal_family="volume_bar_cvd",
            regime="TREND_BULL",
            bars_held=5,
            max_hold_bars=24,
            target_pct=0.02,
            stop_pct=0.01,
        )

        p2 = lab.add_from_paper_trade(
            trade_id="t2",
            signal_id="s2",
            symbol="BTCUSDT",
            side=-1,
            entry_ts_ns=2_000_000_000,
            exit_ts_ns=5_600_000_000,
            entry_price=100.0,
            exit_price=102.0,
            max_adverse=0.025,
            max_favorable=0.001,
            pnl=-20.0,
            exit_reason="STOP",
            signal_family="volume_bar_cvd",
            regime="RANGING",
            bars_held=10,
            max_hold_bars=24,
            target_pct=0.02,
            stop_pct=0.01,
        )

        self.assertEqual(len(lab), 2)
        self.assertTrue(p1.win)
        self.assertFalse(p2.win)
        self.assertEqual(p1.volatility_bucket, "MED")
        self.assertEqual(p2.volatility_bucket, "HIGH")

        # Report tests
        by_regime = lab.report_by_regime()
        self.assertIn("TREND_BULL", by_regime)
        self.assertIn("RANGING", by_regime)
        self.assertEqual(by_regime["TREND_BULL"].n_trades, 1)

        by_signal = lab.report_by_signal_family()
        self.assertIn("volume_bar_cvd", by_signal)

        by_hour = lab.report_by_session_hour()
        self.assertGreater(len(by_hour), 0)

        by_toxicity = lab.report_by_toxicity()
        self.assertIn("UNKNOWN", by_toxicity)

        by_exit = lab.report_by_exit_reason()
        self.assertIn("TARGET", by_exit)
        self.assertIn("STOP", by_exit)

        full = lab.full_report()
        self.assertIn("all", full)
        self.assertIn("by_regime", full)
        self.assertIn("shadow_gates", full)

        # Shadow gates tests
        shadow_mae = lab.shadow_mae_gate(0.85)
        self.assertIsInstance(shadow_mae, PercentileExitResult)
        self.assertEqual(shadow_mae.trades_evaluated, 2)

        shadow_mfe = lab.shadow_mfe_gate(0.50)
        self.assertIsInstance(shadow_mfe, PercentileExitResult)
        self.assertEqual(shadow_mfe.trades_evaluated, 2)

        # Export & Import tests
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            jsonl_file = tmp_path / "trade_paths.jsonl"
            report_file = tmp_path / "report.json"

            lab.export_jsonl(jsonl_file)
            lab.export_report_json(report_file)

            self.assertTrue(jsonl_file.exists())
            self.assertTrue(report_file.exists())

            # Load it back
            loaded = MAEMFEExitLab.load_jsonl(jsonl_file)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded._paths[0].trade_id, "t1")

if __name__ == "__main__":
    unittest.main()
