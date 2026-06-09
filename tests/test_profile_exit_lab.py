"""Tests for V8.5 ProfileExitLab — signal-driven exits with POC/VWAP."""

import unittest
from features.market_profile import MarketProfileSnapshot
from research.profile_exit_lab import (
    ExitSignal,
    EntryQuality,
    ProfileExitDecision,
    ProfileExitLab,
    score_entry,
)


def _make_profile(
    poc=100.0,
    vah=102.0,
    val=98.0,
    atr=1.5,
    lvn_zones=(),
    context="IN_VALUE",
    profile_type="BALANCED",
):
    return MarketProfileSnapshot(
        poc=poc,
        vah=vah,
        val=val,
        lvn_zones=lvn_zones,
        profile_type=profile_type,
        current_value_context=context,
        atr_current=atr,
        session_range=4.0,
        atr_used_pct=40.0,
        range_remaining=1.5,
        can_trade_more=True,
        session_tier="A",
        value_area_width=4.0,
        profile_target_poc=poc,
        profile_target_vah=vah,
        profile_target_val=val,
        profile_target_lvn=None,
    )


class TestExitSignalDetection(unittest.TestCase):
    """Tests for ProfileExitLab.detect_exit_signal."""

    def setUp(self):
        self.lab = ProfileExitLab(hard_stop_atr_multiple=2.5)

    def test_hard_stop_long(self):
        profile = _make_profile(atr=1.0)
        # Hard stop at 3% adverse
        sig = self.lab.detect_exit_signal(
            current_price=96.9,   # > 3% adverse on entry=100
            entry_price=100.0,
            side=1,
            profile=profile,
            base_stop_pct=0.03,
        )
        self.assertEqual(sig, ExitSignal.HARD_STOP)

    def test_hard_stop_short(self):
        profile = _make_profile(atr=1.0)
        sig = self.lab.detect_exit_signal(
            current_price=103.1,   # > 3% adverse on entry=100 short
            entry_price=100.0,
            side=-1,
            profile=profile,
            base_stop_pct=0.03,
        )
        self.assertEqual(sig, ExitSignal.HARD_STOP)

    def test_poc_reclaimed_long(self):
        profile = _make_profile(poc=100.5, atr=0.1)
        sig = self.lab.detect_exit_signal(
            current_price=100.6,
            entry_price=99.0,   # entered below POC
            side=1,
            profile=profile,
        )
        self.assertEqual(sig, ExitSignal.POC_RECLAIMED)

    def test_poc_reclaimed_short(self):
        profile = _make_profile(poc=100.5, atr=0.1)
        sig = self.lab.detect_exit_signal(
            current_price=100.4,
            entry_price=101.0,   # entered above POC
            side=-1,
            profile=profile,
        )
        self.assertEqual(sig, ExitSignal.POC_RECLAIMED)

    def test_vah_break_long(self):
        profile = _make_profile(poc=100.0, vah=102.0, val=98.0, atr=0.1)
        sig = self.lab.detect_exit_signal(
            current_price=102.1,
            entry_price=100.5,
            side=1,
            profile=profile,
        )
        self.assertEqual(sig, ExitSignal.VAH_BREAK)

    def test_val_break_short(self):
        profile = _make_profile(poc=100.0, vah=102.0, val=98.0, atr=0.1)
        sig = self.lab.detect_exit_signal(
            current_price=97.9,
            entry_price=99.5,
            side=-1,
            profile=profile,
        )
        self.assertEqual(sig, ExitSignal.VAL_BREAK)

    def test_vwap_flip_adverse_not_fired(self):
        profile = _make_profile(poc=101.0, atr=0.1)
        # Long, price has crossed VWAP adversely (deviation now > 0.5%)
        # But VWAP_FLIP_ADVERSE was removed from auto-exit path, so it should return NONE
        sig = self.lab.detect_exit_signal(
            current_price=100.0,
            entry_price=99.0,
            side=1,
            profile=profile,
            vwap_deviation=0.006,   # price is 0.6% above VWAP → adverse for long
        )
        self.assertEqual(sig, ExitSignal.NONE)

    def test_none_when_no_signal(self):
        profile = _make_profile(poc=100.5, vah=102.0, val=98.0, atr=0.1)
        # Long entered below POC, price rising but hasn't reclaimed POC yet
        sig = self.lab.detect_exit_signal(
            current_price=100.2,   # below poc=100.5, no signal yet
            entry_price=99.0,
            side=1,
            profile=profile,
            vwap_deviation=-0.001,  # comfortably below VWAP (good for long)
        )
        self.assertEqual(sig, ExitSignal.NONE)

    def test_lvn_reject_not_fired(self):
        # LVN_REJECT was removed from detect_exit_signal because at 24-bar volume-bar
        # resolution, LVN zones are touched constantly (67% of exits were false LVN
        # triggers). The signal is kept in the enum but no longer auto-exits.
        profile = _make_profile(
            poc=101.0, vah=103.0, val=97.0, atr=0.1,
            lvn_zones=(100.7,),
        )
        sig = self.lab.detect_exit_signal(
            current_price=100.7,
            entry_price=99.0,
            side=1,
            profile=profile,
        )
        # LVN touch should NOT trigger an exit — price hasn't hit POC/VAH yet
        self.assertEqual(sig, ExitSignal.NONE)


class TestEvaluateExit(unittest.TestCase):
    """Integration tests for ProfileExitLab.evaluate_exit."""

    def setUp(self):
        self.lab = ProfileExitLab()

    def test_fallback_on_empty_profile(self):
        empty = _make_profile(poc=None, vah=None, val=None, atr=0.0)
        # Manually patch the None fields
        from dataclasses import replace
        empty = replace(empty, poc=None, vah=None, val=None)
        result = self.lab.evaluate_exit(
            entry_price=100.0,
            current_price=100.0,
            side=1,
            profile=empty,
            base_target_pct=0.01,
            base_stop_pct=0.02,
        )
        self.assertEqual(result.context, "FALLBACK_BPS")
        self.assertAlmostEqual(result.target_price, 101.0, places=4)
        self.assertAlmostEqual(result.stop_price, 98.0, places=4)

    def test_long_below_poc_no_exit(self):
        profile = _make_profile(poc=100.5, vah=102.0, val=98.0)
        # Long entered below POC, price slowly rising but POC not yet reclaimed
        result = self.lab.evaluate_exit(
            entry_price=99.5,
            current_price=100.2,   # below poc=100.5, no exit signal
            side=1,
            profile=profile,
        )
        self.assertEqual(result.context, "MEAN_REVERSION_TO_POC")
        self.assertAlmostEqual(result.target_price, 100.5, places=4)
        self.assertFalse(result.exit_recommended)
        self.assertEqual(result.signal, ExitSignal.NONE)

    def test_long_reaches_poc_exits(self):
        profile = _make_profile(poc=100.5, vah=102.0, val=98.0)
        result = self.lab.evaluate_exit(
            entry_price=99.5,
            current_price=100.6,  # past POC
            side=1,
            profile=profile,
        )
        self.assertTrue(result.exit_recommended)

    def test_short_reaches_poc_exits(self):
        profile = _make_profile(poc=100.5, vah=102.0, val=98.0)
        result = self.lab.evaluate_exit(
            entry_price=101.0,
            current_price=100.4,  # at POC
            side=-1,
            profile=profile,
        )
        self.assertTrue(result.exit_recommended)

    def test_hard_stop_pct_override(self):
        profile = _make_profile(poc=100.5, vah=102.0, val=98.0, atr=0.01)
        result = self.lab.evaluate_exit(
            entry_price=100.0,
            current_price=96.5,   # past 3% stop
            side=1,
            profile=profile,
            base_stop_pct=0.03,
        )
        self.assertTrue(result.exit_recommended)
        self.assertEqual(result.signal, ExitSignal.HARD_STOP)


class TestScoreEntry(unittest.TestCase):
    """Tests for the entry quality scorer."""

    def test_score_increases_near_poc(self):
        profile = _make_profile(poc=100.0)
        close_score = score_entry(100.2, side=1, profile=profile, vwap_deviation=-0.001)
        far_score   = score_entry(115.0, side=1, profile=profile, vwap_deviation=-0.001)
        self.assertGreater(close_score.entry_score, far_score.entry_score)

    def test_vwap_aligned_long(self):
        profile = _make_profile()
        quality = score_entry(99.0, side=1, profile=profile, vwap_deviation=-0.003)
        self.assertTrue(quality.vwap_side_aligned)

    def test_vwap_misaligned_penalises_score(self):
        profile = _make_profile()
        aligned   = score_entry(99.0, side=1, profile=profile, vwap_deviation=-0.003)
        misaligned = score_entry(99.0, side=1, profile=profile, vwap_deviation=0.005)
        self.assertGreater(aligned.entry_score, misaligned.entry_score)

    def test_score_bounded(self):
        profile = _make_profile()
        quality = score_entry(100.0, side=1, profile=profile)
        self.assertGreaterEqual(quality.entry_score, 0.0)
        self.assertLessEqual(quality.entry_score, 1.0)


if __name__ == "__main__":
    unittest.main()
