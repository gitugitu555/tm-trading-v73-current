import unittest

from research.v86_recovery import gate_shadow_value


class GateShadowValueTests(unittest.TestCase):
    def test_gate_value_accounts_for_blocked_winners_and_losers(self):
        baseline = [
            {"signal_id": "keep", "notional": 100, "pnl": 2, "return_pct": 0.02},
            {"signal_id": "winner", "notional": 100, "pnl": 4, "return_pct": 0.04},
            {"signal_id": "loser", "notional": 100, "pnl": -10, "return_pct": -0.10},
        ]
        result = gate_shadow_value(baseline, {"keep"})
        self.assertEqual(result["blocked_winners"], 1)
        self.assertEqual(result["blocked_losers"], 1)
        self.assertEqual(result["net_gate_value"], 6)
