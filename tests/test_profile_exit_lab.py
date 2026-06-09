import unittest
from features.market_profile import MarketProfileSnapshot
from research.profile_exit_lab import ProfileExitLab, ProfileExitDecision

class ProfileExitLabTests(unittest.TestCase):
    def test_profile_exit_lab_logic(self) -> None:
        lab = ProfileExitLab()

        # Incomplete profile fallback test
        empty_profile = MarketProfileSnapshot(
            poc=None, vah=None, val=None, lvn_zones=(), profile_type="UNKNOWN",
            current_value_context="UNKNOWN", atr_current=0.0, session_range=0.0,
            atr_used_pct=0.0, range_remaining=0.0, can_trade_more=True,
            session_tier="SKIP", value_area_width=0.0, profile_target_poc=None,
            profile_target_vah=None, profile_target_val=None, profile_target_lvn=None
        )

        fallback_res = lab.evaluate_exit(
            entry_price=100.0,
            current_price=100.0,
            side=1,
            profile=empty_profile,
            base_target_pct=0.01,
            base_stop_pct=0.02
        )
        self.assertEqual(fallback_res.context, "FALLBACK_BPS")
        self.assertEqual(fallback_res.target_price, 101.0)
        self.assertEqual(fallback_res.stop_price, 98.0)

        # Active profile test: Long entry below POC
        active_profile = MarketProfileSnapshot(
            poc=100.5, vah=101.0, val=99.0, lvn_zones=(), profile_type="BALANCED",
            current_value_context="INSIDE_VALUE", atr_current=1.0, session_range=1.5,
            atr_used_pct=50.0, range_remaining=0.5, can_trade_more=True,
            session_tier="HIGH", value_area_width=2.0, profile_target_poc=100.5,
            profile_target_vah=101.0, profile_target_val=99.0, profile_target_lvn=None
        )

        res_long = lab.evaluate_exit(
            entry_price=99.5,
            current_price=99.6,
            side=1,
            profile=active_profile
        )
        self.assertEqual(res_long.context, "MEAN_REVERSION_TO_POC")
        self.assertEqual(res_long.target_price, 100.5)
        self.assertLess(res_long.stop_price, 99.0)
        self.assertFalse(res_long.exit_recommended)

        # Price hits target
        res_target = lab.evaluate_exit(
            entry_price=99.5,
            current_price=100.6,
            side=1,
            profile=active_profile
        )
        self.assertTrue(res_target.exit_recommended)

if __name__ == "__main__":
    unittest.main()
