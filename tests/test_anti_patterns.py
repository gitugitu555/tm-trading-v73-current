import unittest

from features.anti_patterns import AntiPatternEngine


class AntiPatternTests(unittest.TestCase):
    def test_bull_trap_and_mid_value_chase(self) -> None:
        snap = AntiPatternEngine().evaluate(
            setup_side=-1,
            profile_context="IN_VALUE",
            toxicity_state="BENIGN",
            mlofi_zscore=0.1,
            spread_bps=2.0,
            session_tier="A",
            breakout_strength=0.2,
            atr_used_pct=40.0,
            value_area_context="ABOVE_VALUE",
        )
        self.assertTrue(snap.should_block)
        self.assertIn("PROFILE_MID_VALUE_CHASE", snap.labels)

    def test_toxic_spread_breakout(self) -> None:
        snap = AntiPatternEngine().evaluate(
            setup_side=1,
            profile_context="TRENDING",
            toxicity_state="HIGH_TOXICITY",
            mlofi_zscore=1.5,
            spread_bps=8.0,
            session_tier="A",
            breakout_strength=0.8,
            atr_used_pct=30.0,
            value_area_context="BELOW_VALUE",
        )
        self.assertTrue(snap.should_block)
        self.assertIn("LOW_LIQUIDITY_BREAKOUT", snap.labels)


if __name__ == "__main__":
    unittest.main()
