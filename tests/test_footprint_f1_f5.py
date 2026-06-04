import unittest

from prime.footprint_research import (
    FootprintConfig,
    absorption_confirmation,
    build_snapshot_from_ticks,
    detect_stacked_imbalance,
    evaluate_footprint_bar,
    rejection_confirmation,
    round_level,
    structure_confluence,
)
from prime.volume_bars import VolumeBar


class FootprintF1F5Test(unittest.TestCase):
    def test_round_level_matches_tick_rounding(self):
        self.assertEqual(round_level(100.24, 0.5), 100.0)
        self.assertEqual(round_level(100.26, 0.5), 100.5)

    def test_detects_stacked_short_imbalance(self):
        snapshot = build_snapshot_from_ticks(
            [
                (100.0, 5.0, "SELL"),
                (100.0, 1.0, "BUY"),
                (100.5, 6.0, "SELL"),
                (100.5, 1.0, "BUY"),
                (101.0, 7.0, "SELL"),
                (101.0, 1.0, "BUY"),
            ],
            tick_size=0.5,
        )
        result = detect_stacked_imbalance(
            snapshot,
            tick_size=0.5,
            stack_levels=3,
            imbalance_ratio=3.0,
            min_level_total_volume=5.0,
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["side"], -1)
        self.assertEqual(result["boundary_level"], 101.0)
        self.assertEqual(result["cluster_levels"], (100.0, 100.5, 101.0))

    def test_rejection_confirmation_short(self):
        self.assertTrue(
            rejection_confirmation(
                bar_high=101.0,
                bar_low=100.0,
                bar_close=100.25,
                boundary_level=101.0,
                side=-1,
                tick_size=0.5,
                max_extension_ticks=1,
            )
        )
        self.assertFalse(
            rejection_confirmation(
                bar_high=102.0,
                bar_low=100.0,
                bar_close=100.25,
                boundary_level=101.0,
                side=-1,
                tick_size=0.5,
                max_extension_ticks=1,
            )
        )

    def test_absorption_confirmation_short(self):
        row = {"total_volume": 60.0, "delta": -6.0}
        self.assertTrue(
            absorption_confirmation(
                row=row,
                bar_high=101.0,
                bar_low=100.0,
                boundary_level=101.0,
                side=-1,
                tick_size=0.5,
                absorption_delta_share=0.15,
                volume_floor=50.0,
                max_price_extension_ticks=1,
            )
        )
        self.assertFalse(
            absorption_confirmation(
                row={"total_volume": 60.0, "delta": -30.0},
                bar_high=101.0,
                bar_low=100.0,
                boundary_level=101.0,
                side=-1,
                tick_size=0.5,
                absorption_delta_share=0.15,
                volume_floor=50.0,
                max_price_extension_ticks=1,
            )
        )

    def test_structure_confluence_near_session_high(self):
        self.assertTrue(
            structure_confluence(
                level=101.0,
                session_high=101.1,
                session_low=98.0,
                vwap=100.0,
                tick_size=0.5,
                structure_tick_radius=2,
                vwap_deviation_pct=0.003,
                session_extreme_pct=0.003,
            )
        )
        self.assertFalse(
            structure_confluence(
                level=110.0,
                session_high=101.1,
                session_low=98.0,
                vwap=100.0,
                tick_size=0.5,
                structure_tick_radius=2,
                vwap_deviation_pct=0.003,
                session_extreme_pct=0.003,
            )
        )

    def test_final_gate_passes_with_f1_f2_f4(self):
        snapshot = build_snapshot_from_ticks(
            [
                (100.0, 5.0, "SELL"),
                (100.0, 1.0, "BUY"),
                (100.5, 6.0, "SELL"),
                (100.5, 1.0, "BUY"),
                (101.0, 7.0, "SELL"),
                (101.0, 1.0, "BUY"),
            ],
            tick_size=0.5,
        )
        result = evaluate_footprint_bar(
            snapshot=snapshot,
            bar_high=101.0,
            bar_low=100.0,
            bar_close=100.25,
            session_high=101.1,
            session_low=98.0,
            vwap=100.0,
            config=FootprintConfig(),
        )
        self.assertTrue(result.f1)
        self.assertTrue(result.f2)
        self.assertFalse(result.f3)
        self.assertTrue(result.f4)
        self.assertTrue(result.f5)

    def test_final_gate_requires_structure(self):
        snapshot = build_snapshot_from_ticks(
            [
                (100.0, 5.0, "SELL"),
                (100.0, 1.0, "BUY"),
                (100.5, 6.0, "SELL"),
                (100.5, 1.0, "BUY"),
                (101.0, 7.0, "SELL"),
                (101.0, 1.0, "BUY"),
            ],
            tick_size=0.5,
        )
        result = evaluate_footprint_bar(
            snapshot=snapshot,
            bar_high=101.0,
            bar_low=100.0,
            bar_close=100.25,
            session_high=105.0,
            session_low=95.0,
            vwap=90.0,
            config=FootprintConfig(),
        )
        self.assertTrue(result.f1)
        self.assertTrue(result.f2)
        self.assertFalse(result.f4)
        self.assertFalse(result.f5)


if __name__ == "__main__":
    unittest.main()
