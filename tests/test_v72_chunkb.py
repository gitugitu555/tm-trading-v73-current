from collections import deque
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from prime.chunk_b_backtest import ChunkBBacktestConfig, ChunkBBacktester
from prime.auction_state import AuctionStateEngine
from prime.chunk_b_trade_state import OpenTradeState
from prime.contracts import DataQualitySnapshot
from prime.performance import deflated_sharpe_probability, sharpe_ratio
from prime.phase4_minimal import HardRegimeClassifier, chunk_b_regime_proxy
from prime.phase5_chunkb import AlphaPermissionEngineChunkB
from prime.ic_harness import ResearchTick, iter_binance_research_ticks
from prime.nautilus_compat import AggressorSide
from tests.test_v72_phase1 import tick


class V72ChunkBTest(unittest.TestCase):
    def test_regime_proxy_trend_and_unknown(self):
        self.assertEqual(chunk_b_regime_proxy(0.003, 10.0)[0], "TREND_BULL")
        self.assertEqual(chunk_b_regime_proxy(-0.003, -10.0)[0], "TREND_BEAR")
        self.assertEqual(chunk_b_regime_proxy(0.002, -10.0)[0], "UNKNOWN")
        self.assertEqual(
            chunk_b_regime_proxy(0.0015, 10.0, trend_threshold_pct=0.001)[0],
            "TREND_BULL",
        )

    def test_regime_proxy_stress_halts_extreme_flow(self):
        self.assertEqual(chunk_b_regime_proxy(-0.006, -900.0)[0], "STRESS")
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=-0.006,
            cvd_session=-900.0,
        )
        self.assertTrue(regime.all_halted)
        self.assertFalse(HardRegimeClassifier.gate_for_signal_mode(regime, "divergence"))

    def test_alpha_permission_chunkb_short_circuits_feed_halt(self):
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.003,
            cvd_session=10.0,
        )
        quality = DataQualitySnapshot("HALT", 0.0, 0.0, 0, False, 0.0, 0.0, ["TEST"])
        permission = AlphaPermissionEngineChunkB().evaluate(
            signal_id="s1",
            timestamp_ns=1,
            trade_side=1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=True,
            cvd_5m=10.0,
        )
        self.assertEqual(permission.verdict, "HARD_DENY")
        self.assertEqual(permission.blocking_codes, ["FEED_HALT"])

    def test_alpha_permission_chunkb_approves_confirming_cvd(self):
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.003,
            cvd_session=10.0,
        )
        quality = DataQualitySnapshot("CLEAN", 0.0, 0.0, 0, False, 0.0, 1.0, [])
        permission = AlphaPermissionEngineChunkB(kq_approve=0.55).evaluate(
            signal_id="s1",
            timestamp_ns=1,
            trade_side=1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=True,
            cvd_5m=10.0,
        )
        self.assertEqual(permission.verdict, "APPROVE")
        self.assertIn("CVD_CONFIRMING", [record.code for record in permission.chain])

    def test_alpha_permission_chunkb_divergence_short_confirms_negative_cvd(self):
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0015,
            cvd_session=-10.0,
        )
        quality = DataQualitySnapshot("CLEAN", 0.0, 0.0, 0, False, 0.0, 1.0, [])
        permission = AlphaPermissionEngineChunkB(kq_approve=0.55).evaluate(
            signal_id="s1",
            timestamp_ns=1,
            trade_side=-1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=True,
            cvd_5m=-10.0,
            signal_mode="divergence",
            vwap_deviation=0.0,
        )
        self.assertEqual(permission.verdict, "APPROVE")
        self.assertIn("CVD_CONFIRMING", [record.code for record in permission.chain])
        self.assertIn("VWAP_SCORE", [record.code for record in permission.chain])

    def test_alpha_permission_chunkb_vwap_tiered_multiplier(self):
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.003,
            cvd_session=10.0,
        )
        quality = DataQualitySnapshot("CLEAN", 0.0, 0.0, 0, False, 0.0, 1.0, [])
        near = AlphaPermissionEngineChunkB(kq_approve=0.0).evaluate(
            signal_id="near",
            timestamp_ns=1,
            trade_side=1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=False,
            cvd_5m=10.0,
            vwap_deviation=0.0005,
        )
        extended = AlphaPermissionEngineChunkB(kq_approve=0.0).evaluate(
            signal_id="extended",
            timestamp_ns=1,
            trade_side=1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=False,
            cvd_5m=10.0,
            vwap_deviation=0.004,
        )
        self.assertGreater(near.kq, extended.kq)
        self.assertIn("VWAP_SCORE", [record.code for record in near.chain])
        self.assertIn("VWAP_SCORE", [record.code for record in extended.chain])

    def test_alpha_permission_chunkb_auction_state_opt_in_off_is_inert(self):
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.003,
            cvd_session=120.0,
        )
        quality = DataQualitySnapshot("CLEAN", 0.0, 0.0, 0, False, 0.0, 1.0, [])
        auction = AuctionStateEngine(hysteresis_bars=1).update(
            timestamp_ns=1,
            price_change_5m_pct=0.0032,
            cvd_session=120.0,
            value_acceptance=True,
        )

        permission = AlphaPermissionEngineChunkB(kq_approve=0.0).evaluate(
            signal_id="auction-off",
            timestamp_ns=1,
            trade_side=1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=False,
            cvd_5m=10.0,
            auction_state=auction,
        )

        self.assertIn("AUCTION_TRENDING_OPTIN_OFF", [record.code for record in permission.chain])

    def test_alpha_permission_fade_path_penalizes_trending_auction(self):
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.003,
            cvd_session=120.0,
        )
        quality = DataQualitySnapshot("CLEAN", 0.0, 0.0, 0, False, 0.0, 1.0, [])
        auction = AuctionStateEngine(hysteresis_bars=1).update(
            timestamp_ns=1,
            price_change_5m_pct=0.0032,
            cvd_session=120.0,
            value_acceptance=True,
        )
        fade = AlphaPermissionEngineChunkB(
            kq_approve=0.0,
            use_auction_state_gate=True,
        ).evaluate(
            signal_id="fade",
            timestamp_ns=1,
            trade_side=-1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=False,
            cvd_5m=50.0,
            signal_mode="divergence",
            divergence_type="volume_bar_cvd",
            auction_state=auction,
        )
        mom = AlphaPermissionEngineChunkB(
            kq_approve=0.0,
            use_auction_state_gate=True,
        ).evaluate(
            signal_id="mom",
            timestamp_ns=1,
            trade_side=1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=False,
            cvd_5m=50.0,
            signal_mode="momentum",
            auction_state=auction,
        )
        fade_mult = next(r.multiplier for r in fade.chain if r.code == "AUCTION_TRENDING")
        mom_mult = next(r.multiplier for r in mom.chain if r.code == "AUCTION_TRENDING")
        self.assertLess(fade_mult, mom_mult)

    def test_alpha_permission_chunkb_auction_state_opt_in_adjusts_kq(self):
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.003,
            cvd_session=120.0,
        )
        quality = DataQualitySnapshot("CLEAN", 0.0, 0.0, 0, False, 0.0, 1.0, [])
        auction = AuctionStateEngine(hysteresis_bars=1).update(
            timestamp_ns=1,
            price_change_5m_pct=0.0032,
            cvd_session=120.0,
            value_acceptance=True,
        )

        gated = AlphaPermissionEngineChunkB(
            kq_approve=0.0,
            use_auction_state_gate=True,
        ).evaluate(
            signal_id="auction-on",
            timestamp_ns=1,
            trade_side=1,
            raw_strength=1.0,
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=False,
            cvd_5m=10.0,
            auction_state=auction,
        )

        self.assertIn("AUCTION_TRENDING", [record.code for record in gated.chain])
        self.assertGreater(gated.kq, 0.0)

    def test_backtester_runs_synthetic_trend(self):
        stream = [tick(i, 100.0 + i * 0.02) for i in range(500)]
        report, trades = ChunkBBacktester(
            ChunkBBacktestConfig(divergence_threshold=5.0, footprint_warm_period=20)
        ).run(stream)
        self.assertEqual(report.rows_seen, 500)
        self.assertGreaterEqual(report.signals_seen, 1)
        self.assertGreaterEqual(report.trades, 1)
        self.assertEqual(len(trades), report.trades)

    def test_backtester_accepts_research_ticks(self):
        start = 1_700_000_000_000_000_000
        stream = [
            ResearchTick(
                price=100.0 + idx * 0.02,
                size=1.0,
                aggressor_side=AggressorSide.BUYER,
                ts_event=start + idx * 1_000_000_000,
            )
            for idx in range(500)
        ]
        report, trades = ChunkBBacktester(
            ChunkBBacktestConfig(divergence_threshold=5.0, footprint_warm_period=20)
        ).run(stream)
        self.assertGreaterEqual(report.trades, 1)
        self.assertEqual(len(trades), report.trades)

    def test_backtester_can_exit_on_target(self):
        stream = [tick(i, 100.0 + i * 0.05) for i in range(500)]
        report, trades = ChunkBBacktester(
            ChunkBBacktestConfig(
                divergence_threshold=5.0,
                footprint_warm_period=20,
                stop_pct=0.003,
                target_pct=0.006,
                use_tpsl=True,
            )
        ).run(stream)

        self.assertGreaterEqual(report.trades, 1)
        self.assertIn("TARGET", {trade.exit_reason for trade in trades})
        self.assertGreaterEqual(report.exit_reasons.get("TARGET", 0), 1)

    def test_backtester_divergence_mode_fades_price_cvd_disagreement(self):
        start = 1_700_000_000_000_000_000
        stream = [
            ResearchTick(
                price=100.0 + idx * 0.0003,
                size=1.0,
                aggressor_side=AggressorSide.SELLER,
                ts_event=start + idx * 1_000_000_000,
            )
            for idx in range(500)
        ]
        report, trades = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_threshold=5.0,
                price_change_threshold=0.0005,
                footprint_warm_period=20,
                use_cvd_reversal_confirm=False,
            )
        ).run(stream)

        self.assertGreaterEqual(report.signals_seen, 1)
        self.assertGreaterEqual(report.trades, 1)
        self.assertTrue(all(trade.side == -1 for trade in trades))

    def test_divergence_signal_requires_all_3_layers(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_threshold_1h=200.0,
                divergence_threshold_15m=80.0,
                divergence_threshold_5m=30.0,
                footprint_warm_period=20,
                use_cvd_quantile_filter=False,
                use_session_extreme_gate=False,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._cvd._cvd_1h = -50.0
        backtester._cvd._cvd_15m = -20.0
        backtester._cvd._cvd_5m = -40.0
        backtester._vwap._deviation = 0.0

        signal = backtester._signal(
            timestamp_ns=1,
            price=100.0,
            price_change=0.002,
            regime=regime,
            cvd_quantile_ok=True,
        )
        self.assertIsNone(signal)

    def test_divergence_signal_fires_short_when_all_3_align(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_threshold_1h=200.0,
                divergence_threshold_15m=80.0,
                divergence_threshold_5m=30.0,
                footprint_warm_period=20,
                use_cvd_quantile_filter=False,
                use_session_extreme_gate=False,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._cvd._cvd_1h = -250.0
        backtester._cvd._cvd_15m = -100.0
        backtester._cvd._cvd_5m = -40.0
        backtester._vwap._deviation = 0.0
        backtester._footprint._bias = -1

        signal = backtester._signal(
            timestamp_ns=1,
            price=100.0,
            price_change=0.002,
            regime=regime,
            cvd_quantile_ok=True,
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], -1)

    def test_divergence_signal_fires_long_when_all_3_align(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_threshold_1h=200.0,
                divergence_threshold_15m=80.0,
                divergence_threshold_5m=30.0,
                footprint_warm_period=20,
                use_cvd_quantile_filter=False,
                use_session_extreme_gate=False,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._cvd._cvd_1h = 250.0
        backtester._cvd._cvd_15m = 100.0
        backtester._cvd._cvd_5m = 40.0
        backtester._vwap._deviation = 0.0
        backtester._footprint._bias = 1

        signal = backtester._signal(
            timestamp_ns=1,
            price=100.0,
            price_change=-0.002,
            regime=regime,
            cvd_quantile_ok=True,
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], 1)

    def test_swing_divergence_fires_short_near_price_high(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_type="swing",
                divergence_threshold_15m=80.0,
                use_cvd_quantile_filter=False,
                use_session_extreme_gate=False,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._swing._price_high = 105.0
        backtester._swing._price_low = 95.0
        backtester._swing._cvd_high = 200.0
        backtester._swing._cvd_low = -100.0
        backtester._cvd._cvd_15m = 50.0
        backtester._vwap._deviation = 0.0
        backtester._footprint._bias = -1

        signal = backtester._swing_divergence_signal(
            timestamp_ns=1,
            price=104.9,
            regime=regime,
            cvd_quantile_ok=True,
        )

        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], -1)

    def test_invert_flag_flips_side(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_type="swing",
                divergence_threshold_15m=80.0,
                use_cvd_quantile_filter=False,
                invert_signal_side=True,
                use_session_extreme_gate=False,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._swing._price_high = 105.0
        backtester._swing._price_low = 95.0
        backtester._swing._cvd_high = 200.0
        backtester._swing._cvd_low = -100.0
        backtester._cvd._cvd_15m = 50.0
        backtester._vwap._deviation = 0.0
        backtester._footprint._bias = -1

        signal = backtester._swing_divergence_signal(
            timestamp_ns=1,
            price=104.9,
            regime=regime,
            cvd_quantile_ok=True,
        )

        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], 1)

    def test_swing_divergence_fires_long_near_price_low(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_type="swing",
                divergence_threshold_15m=80.0,
                use_cvd_quantile_filter=False,
                use_session_extreme_gate=False,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._swing._price_high = 105.0
        backtester._swing._price_low = 95.0
        backtester._swing._cvd_high = 100.0
        backtester._swing._cvd_low = -200.0
        backtester._cvd._cvd_15m = -50.0
        backtester._vwap._deviation = 0.0
        backtester._footprint._bias = 1

        signal = backtester._swing_divergence_signal(
            timestamp_ns=1,
            price=95.05,
            regime=regime,
            cvd_quantile_ok=True,
        )

        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], 1)

    def test_session_extreme_gate_blocks_mid_range_signal(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_type="swing",
                divergence_threshold_15m=80.0,
                use_cvd_quantile_filter=False,
                use_session_extreme_gate=True,
                session_extreme_pct=0.003,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._session_extreme.update(0, 110.0)
        backtester._session_extreme.update(1, 90.0)
        backtester._swing._price_high = 100.05
        backtester._swing._price_low = 90.0
        backtester._swing._cvd_high = 200.0
        backtester._swing._cvd_low = -100.0
        backtester._cvd._cvd_15m = 50.0
        backtester._vwap._deviation = 0.0
        backtester._footprint._bias = -1

        signal = backtester._swing_divergence_signal(
            timestamp_ns=1,
            price=100.0,
            regime=regime,
            cvd_quantile_ok=True,
        )

        self.assertIsNone(signal)

    def test_session_extreme_gate_allows_near_session_high(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                divergence_type="swing",
                divergence_threshold_15m=80.0,
                use_cvd_quantile_filter=False,
                use_session_extreme_gate=True,
                session_extreme_pct=0.003,
            )
        )
        regime = HardRegimeClassifier().classify(
            timestamp_ns=1,
            price_change_5m_pct=0.0005,
            cvd_session=0.0,
        )
        backtester._session_extreme.update(0, 100.0)
        backtester._session_extreme.update(1, 90.0)
        backtester._swing._price_high = 99.85
        backtester._swing._price_low = 90.0
        backtester._swing._cvd_high = 200.0
        backtester._swing._cvd_low = -100.0
        backtester._cvd._cvd_15m = 50.0
        backtester._vwap._deviation = 0.0
        backtester._footprint._bias = -1

        signal = backtester._swing_divergence_signal(
            timestamp_ns=1,
            price=99.8,
            regime=regime,
            cvd_quantile_ok=True,
        )

        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], -1)

    def test_cvd_reversal_confirm_delays_entry(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="divergence",
                use_cvd_reversal_confirm=True,
                cvd_confirm_ticks=2,
            )
        )
        signal = {"id": "sig", "side": -1, "strength": 1.0, "price": 100.0}

        self.assertIsNone(backtester._confirm_divergence_signal(signal, 1, 100.0))
        self.assertIsNotNone(backtester._pending_signal)

        backtester._cvd_prev_5m = 100.0
        backtester._cvd._cvd_5m = 90.0
        self.assertIsNone(backtester._confirm_divergence_signal(None, 2, 99.9))

        backtester._cvd_prev_5m = 90.0
        backtester._cvd._cvd_5m = 80.0
        confirmed = backtester._confirm_divergence_signal(None, 3, 99.8)

        self.assertIsNotNone(confirmed)
        self.assertEqual(confirmed["id"], "sig")

    def test_cvd_reversal_confirm_cancels_stale_signal(self):
        backtester = ChunkBBacktester(
            ChunkBBacktestConfig(signal_mode="divergence", use_cvd_reversal_confirm=True)
        )
        signal = {"id": "sig", "side": -1, "strength": 1.0, "price": 100.0}

        self.assertIsNone(backtester._confirm_divergence_signal(signal, 1, 100.0))
        result = backtester._confirm_divergence_signal(None, 2, 100.21)

        self.assertIsNone(result)
        self.assertIsNone(backtester._pending_signal)

    def test_cvd_exit_closes_short_when_cvd_crosses_zero(self):
        backtester = ChunkBBacktester(ChunkBBacktestConfig(use_cvd_exit=True))
        backtester._cvd._cvd_5m = 1.0
        open_trade = OpenTradeState.from_legacy_dict(
            {
                "side": -1,
                "entry_price": 100.0,
                "exit_after_ts_ns": 10_000,
            }
        )

        self.assertEqual(backtester._exit_reason(open_trade, 1, 100.0), "CVD_EXIT")

    def test_cvd_quantile_filter_uses_absolute_extremes(self):
        history = deque([-10.0, 20.0, -30.0, 40.0], maxlen=4)

        self.assertTrue(
            ChunkBBacktester._cvd_quantile_extreme(
                -40.0,
                history,
                min_samples=4,
                quantile=0.75,
            )
        )
        self.assertFalse(
            ChunkBBacktester._cvd_quantile_extreme(
                25.0,
                history,
                min_samples=4,
                quantile=0.75,
            )
        )

    def test_momentum_mode_unchanged_after_divergence_addition(self):
        stream = [tick(i, 100.0 + i * 0.02) for i in range(500)]
        report, trades = ChunkBBacktester(
            ChunkBBacktestConfig(
                signal_mode="momentum",
                divergence_threshold=5.0,
                footprint_warm_period=20,
            )
        ).run(stream)

        self.assertEqual(report.signals_seen, 14)
        self.assertEqual(report.trades, 13)
        self.assertEqual(len(trades), 13)
        self.assertEqual([trade.side for trade in trades], [1] * 13)

    def test_research_tick_iterator_applies_time_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "BTCUSDT-aggTrades-2022-05.zip"
            rows = [
                "1,100.0,1.0,1,1,1652054400000,False,True\n",
                "2,101.0,1.0,2,2,1652140800000,False,True\n",
                "3,102.0,1.0,3,3,1652227200000,False,True\n",
            ]
            with ZipFile(archive, "w") as zipped:
                zipped.writestr("BTCUSDT-aggTrades-2022-05.csv", "".join(rows))

            ticks = list(
                iter_binance_research_ticks(
                    [archive],
                    max_rows=None,
                    start_ns=1652140800000 * 1_000_000,
                    end_ns=1652227200000 * 1_000_000,
                )
            )

        self.assertEqual([float(item.price) for item in ticks], [101.0])

    def test_performance_metrics_are_bounded(self):
        returns = [0.01, 0.02, -0.005, 0.015, 0.0, 0.03]
        sharpe = sharpe_ratio(returns)
        dsr = deflated_sharpe_probability(sharpe, n_trials=4, skew=0.0, kurt=3.0, n_obs=len(returns))
        self.assertTrue(0.0 <= dsr <= 1.0)


if __name__ == "__main__":
    unittest.main()
