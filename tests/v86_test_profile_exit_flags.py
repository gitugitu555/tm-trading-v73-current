import sys
import unittest
from unittest.mock import patch

from scripts.chunk_b_backtest_cached import parse_args


class ProfileExitFlagTests(unittest.TestCase):
    def test_profile_exit_ablation_flags_parse(self):
        argv = [
            "chunk_b_backtest_cached.py",
            "--use-profile-exit",
            "--disable-profile-poc-reclaim-exit",
            "--disable-profile-hard-stop",
            "--profile-exit-min-bars",
            "8",
            "--profile-exit-min-profit-pct",
            "0.001",
            "--profile-exit-require-cvd-confirm",
            "--profile-exit-require-pressure-confirm",
        ]
        with patch.object(sys, "argv", argv):
            args = parse_args()
        self.assertTrue(args.use_profile_exit)
        self.assertTrue(args.disable_profile_poc_reclaim_exit)
        self.assertTrue(args.disable_profile_hard_stop)
        self.assertEqual(args.profile_exit_min_bars, 8)
        self.assertEqual(args.profile_exit_min_profit_pct, 0.001)
        self.assertTrue(args.profile_exit_require_cvd_confirm)
        self.assertTrue(args.profile_exit_require_pressure_confirm)
