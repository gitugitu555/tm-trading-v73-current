import math
import unittest

from research.v86_recovery import summarize_trades


class SummaryAccountingTests(unittest.TestCase):
    def test_summary_reconstructs_actual_ledger_equity(self):
        trades = [
            {"notional": 500, "pnl": 10, "return_pct": 0.02, "fees": 1, "slippage": 0.2},
            {"notional": 510, "pnl": -4, "return_pct": -4 / 510, "fees": 1.02, "slippage": 0.2},
        ]
        summary = summarize_trades(trades, starting_equity=500)
        self.assertTrue(math.isclose(summary["ending_equity_actual"], 506))
        self.assertTrue(math.isclose(summary["net_pnl"], 6))
        self.assertTrue(math.isclose(summary["fees_paid"], 2.02))
        self.assertNotEqual(summary["ending_equity_actual"], summary["ending_equity_synthetic_1pct"])
