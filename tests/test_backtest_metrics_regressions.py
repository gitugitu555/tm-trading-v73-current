import math
import sys
import unittest
from unittest.mock import patch

from prime.chunk_b_backtest import ChunkBBacktestConfig
from prime.configs import ChunkBBacktestConfig as LegacyChunkBBacktestConfig
from prime.performance import calendar_daily_returns, infer_periods_per_year, sharpe_ratio
from scripts import chunk_b_backtest_cached, v73_backtest_6y_incremental


DAY_NS = 24 * 60 * 60 * 1_000_000_000


class BacktestMetricsRegressionTest(unittest.TestCase):
    def test_defaults_keep_reward_above_risk(self) -> None:
        typed = ChunkBBacktestConfig()
        legacy = LegacyChunkBBacktestConfig()
        self.assertGreater(typed.target_pct, typed.stop_pct)
        self.assertEqual(legacy.stop_pct, typed.stop_pct)
        self.assertEqual(legacy.target_pct, typed.target_pct)

    def test_runner_defaults_match_typed_config(self) -> None:
        typed = ChunkBBacktestConfig()
        self.assertEqual(v73_backtest_6y_incremental.STOP_PCT, typed.stop_pct)
        self.assertEqual(v73_backtest_6y_incremental.TARGET_PCT, typed.target_pct)
        with patch.object(sys, "argv", ["chunk_b_backtest_cached.py"]):
            cached_args = chunk_b_backtest_cached.parse_args()
        self.assertEqual(cached_args.stop_pct, typed.stop_pct)
        self.assertEqual(cached_args.target_pct, typed.target_pct)

    def test_infer_periods_per_year_from_trade_timestamps(self) -> None:
        periods = infer_periods_per_year(730, 0, 365.25 * DAY_NS)
        self.assertAlmostEqual(periods, 730.0, places=6)

    def test_trade_sharpe_scales_with_observation_frequency(self) -> None:
        returns = [0.01, -0.005, 0.012, -0.004, 0.009, -0.003]
        reported = sharpe_ratio(returns, periods_per_year=365.0)
        corrected = sharpe_ratio(returns, periods_per_year=730.0)
        self.assertAlmostEqual(corrected / reported, math.sqrt(2.0), places=6)

    def test_calendar_daily_returns_include_first_and_idle_days(self) -> None:
        returns = calendar_daily_returns(
            [
                (DAY_NS, 10.0),
                (3 * DAY_NS, -5.0),
            ],
            starting_equity=1_000.0,
        )
        self.assertEqual(len(returns), 3)
        self.assertAlmostEqual(returns[0], 0.01)
        self.assertEqual(returns[1], 0.0)
        self.assertAlmostEqual(returns[2], -5.0 / 1_010.0)


if __name__ == "__main__":
    unittest.main()
