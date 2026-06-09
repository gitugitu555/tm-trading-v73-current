import unittest

from risk.risk_state import RiskStateEngine


class RiskStateTests(unittest.TestCase):
    def test_halt_on_drawdown_and_loss_streak(self) -> None:
        engine = RiskStateEngine()
        snap = engine.evaluate(
            daily_pnl_r=-4.0,
            weekly_pnl_r=-9.0,
            consecutive_losses=5,
            gross_exposure=0.5,
        )
        self.assertEqual(snap.state, "HALT")
        self.assertFalse(snap.allow)
        self.assertIn("DAILY_HALT", snap.reason_codes)

    def test_reduce_size_on_toxicity_or_exposure(self) -> None:
        engine = RiskStateEngine()
        snap = engine.evaluate(
            daily_pnl_r=-0.1,
            weekly_pnl_r=-0.2,
            consecutive_losses=0,
            gross_exposure=1.5,
            toxicity_state="RISING_TOXICITY",
        )
        self.assertEqual(snap.state, "REDUCE_SIZE")
        self.assertLess(snap.position_scalar, 1.0)


if __name__ == "__main__":
    unittest.main()
