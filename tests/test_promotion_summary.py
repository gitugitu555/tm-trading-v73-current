import json
import tempfile
import unittest
from pathlib import Path

from research.promotion_summary import build_promotion_summary


class PromotionSummaryTests(unittest.TestCase):
    def test_summary_marks_promotable_mae_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            trade_db = tmp_path / "trade_path.jsonl"
            trade_db.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "trade_id": "t1",
                                "signal_id": "s1",
                                "symbol": "BTCUSDT",
                                "side": 1,
                                "entry_ts_ns": 1_000_000_000,
                                "exit_ts_ns": 4_600_000_000,
                                "entry_price": 100.0,
                                "exit_price": 101.0,
                                "pnl": 1.0,
                                "return_pct": 0.01,
                                "win": True,
                                "exit_reason": "TARGET",
                                "signal_family": "volume_bar_cvd",
                                "regime": "UNKNOWN",
                                "session_hour_utc": 0,
                                "volatility_bucket": "LOW",
                                "mae": 0.01,
                                "mfe": 0.03,
                                "mae_r": 1.0,
                                "mfe_r": 3.0,
                                "bars_held": 4,
                                "max_hold_bars": 24,
                                "target_pct": 0.02,
                                "stop_pct": 0.01,
                            }
                        ),
                        json.dumps(
                            {
                                "trade_id": "t2",
                                "signal_id": "s2",
                                "symbol": "BTCUSDT",
                                "side": -1,
                                "entry_ts_ns": 2_000_000_000,
                                "exit_ts_ns": 5_600_000_000,
                                "entry_price": 100.0,
                                "exit_price": 99.0,
                                "pnl": 1.0,
                                "return_pct": 0.01,
                                "win": True,
                                "exit_reason": "TARGET",
                                "signal_family": "volume_bar_cvd",
                                "regime": "UNKNOWN",
                                "session_hour_utc": 0,
                                "volatility_bucket": "LOW",
                                "mae": 0.02,
                                "mfe": 0.04,
                                "mae_r": 2.0,
                                "mfe_r": 4.0,
                                "bars_held": 4,
                                "max_hold_bars": 24,
                                "target_pct": 0.02,
                                "stop_pct": 0.01,
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            baseline = {
                "report": {
                    "trades": 2,
                    "win_rate": 1.0,
                    "total_pnl": 2.0,
                    "sharpe": 2.0,
                    "dsr_passed": True,
                    "ending_equity": 102000.0,
                    "lookahead_safe": True,
                    "entry_lag_bars": 1,
                }
            }
            mae_mfe = {
                "shadow_gates": {
                    "mae_p85_gate": {
                        "mae_threshold": 0.02,
                        "mfe_threshold": None,
                        "trades_evaluated": 2,
                        "would_exit_early": 1,
                        "early_exits_that_were_winners": 0,
                        "early_exits_that_were_losers": 1,
                        "counterfactual_win_rate": 1.0,
                        "counterfactual_pnl_delta": 0.5,
                        "winner_loser_ratio": 2.0,
                    }
                }
            }

            summary = build_promotion_summary(
                baseline_report=baseline,
                trade_path_db_path=trade_db,
                mae_mfe_report=mae_mfe,
            )
            self.assertTrue(summary["eligible"])
            self.assertEqual(summary["promotion_label"], "PROMOTE_MAE_GATE")
            self.assertEqual(summary["trade_path_db"]["n_trades"], 2)


if __name__ == "__main__":
    unittest.main()
