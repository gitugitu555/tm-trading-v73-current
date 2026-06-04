import unittest

from prime.ic_harness import run_ic_on_ticks, signed_to_tick
from prime.ic_validation import check_collinearity, validate_engine
from prime.nautilus_compat import AggressorSide, InstrumentId, Price, Quantity, TradeId, TradeTick
from prime.phase1 import (
    CVDEngine,
    FootprintEngine,
    SessionExtremeTracker,
    SwingDivergenceEngine,
    VolumeProfileEngine,
    VWAPEngine,
)
from tests.helpers import trade as legacy_trade


def tick(idx: int, price: float, size: float = 1.0, side=AggressorSide.BUYER) -> TradeTick:
    ts = 1_700_000_000_000_000_000 + idx * 1_000_000_000
    return TradeTick(
        instrument_id=InstrumentId.from_str("BTCUSDT.BINANCE"),
        price=Price(price, precision=2),
        size=Quantity(size, precision=8),
        aggressor_side=side,
        trade_id=TradeId(str(idx)),
        ts_event=ts,
        ts_init=ts,
    )


def tick_at(
    ts_event: int,
    price: float,
    size: float = 1.0,
    side=AggressorSide.BUYER,
) -> TradeTick:
    return TradeTick(
        instrument_id=InstrumentId.from_str("BTCUSDT.BINANCE"),
        price=Price(price, precision=2),
        size=Quantity(size, precision=8),
        aggressor_side=side,
        trade_id=TradeId(str(ts_event)),
        ts_event=ts_event,
        ts_init=ts_event,
    )


class V72Phase1Test(unittest.TestCase):
    def test_cvd_determinism(self):
        stream = [tick(i, 100 + i * 0.01, side=AggressorSide.BUYER) for i in range(20)]
        results = []
        for _ in range(3):
            engine = CVDEngine(divergence_threshold=100.0)
            for item in stream:
                engine.handle_trade_tick(item)
            results.append(round(engine.cvd_session, 8))
        self.assertEqual(len(set(results)), 1)

    def test_cvd_buffers_all_zero_at_init(self):
        engine = CVDEngine()
        self.assertEqual(engine.cvd_5m, 0.0)
        self.assertEqual(engine.cvd_15m, 0.0)
        self.assertEqual(engine.cvd_1h, 0.0)
        self.assertEqual(engine.cvd_4h, 0.0)

    def test_cvd_15m_accumulates_correctly(self):
        base = 1_700_000_000_000_000_000
        engine = CVDEngine()
        for item in [
            tick_at(base, 100.0, side=AggressorSide.BUYER),
            tick_at(base + 10 * 60 * 1_000_000_000, 101.0, side=AggressorSide.BUYER),
            tick_at(base + 20 * 60 * 1_000_000_000, 102.0, side=AggressorSide.SELLER),
            tick_at(base + 25 * 60 * 1_000_000_000, 103.0, side=AggressorSide.BUYER),
        ]:
            engine.handle_trade_tick(item)

        self.assertEqual(engine.cvd_5m, 1.0)
        self.assertEqual(engine.cvd_15m, 0.0)
        self.assertEqual(engine.cvd_1h, 2.0)
        self.assertEqual(engine.cvd_4h, 2.0)

    def test_cvd_1h_excludes_old_ticks(self):
        base = 1_700_000_000_000_000_000
        engine = CVDEngine()
        for item in [
            tick_at(base, 100.0, side=AggressorSide.BUYER),
            tick_at(base + 30 * 60 * 1_000_000_000, 101.0, side=AggressorSide.SELLER),
            tick_at(base + 70 * 60 * 1_000_000_000, 102.0, side=AggressorSide.BUYER),
        ]:
            engine.handle_trade_tick(item)

        self.assertEqual(engine.cvd_5m, 1.0)
        self.assertEqual(engine.cvd_1h, 0.0)

    def test_cvd_reset_session_clears_rolling_windows(self):
        engine = CVDEngine()
        for idx in range(20):
            engine.handle_trade_tick(tick(idx, 100.0 + idx, side=AggressorSide.BUYER))

        self.assertTrue(engine.initialized)
        self.assertNotEqual(engine.cvd_5m, 0.0)

        engine.reset_session()

        self.assertEqual(engine.cvd_5m, 0.0)
        self.assertEqual(engine.cvd_15m, 0.0)
        self.assertEqual(engine.cvd_1h, 0.0)
        self.assertTrue(engine.initialized)

    def test_swing_engine_tracks_price_high_and_low(self):
        engine = SwingDivergenceEngine(warm_period=1)
        prices = [100.0, 103.0, 99.0, 101.0]
        for idx, price in enumerate(prices):
            engine.update(idx * 1_000_000_000, price, float(idx))

        self.assertEqual(engine.price_high, max(prices))
        self.assertEqual(engine.price_low, min(prices))
        self.assertEqual(engine.cvd_high, 3.0)
        self.assertEqual(engine.cvd_low, 0.0)

    def test_swing_engine_initializes_after_warm_period(self):
        engine = SwingDivergenceEngine(warm_period=3)

        engine.update(1, 100.0, 1.0)
        engine.update(2, 101.0, 2.0)
        self.assertFalse(engine.initialized)

        engine.update(3, 102.0, 3.0)
        self.assertTrue(engine.initialized)

    def test_swing_engine_prunes_old_extrema(self):
        engine = SwingDivergenceEngine(window_ns=30 * 60 * 1_000_000_000, warm_period=1)
        engine.update(0, 110.0, 10.0)
        engine.update(31 * 60 * 1_000_000_000, 100.0, -5.0)

        self.assertEqual(engine.price_high, 100.0)
        self.assertEqual(engine.price_low, 100.0)
        self.assertEqual(engine.cvd_high, -5.0)
        self.assertEqual(engine.cvd_low, -5.0)

    def test_session_tracker_resets_on_new_day(self):
        tracker = SessionExtremeTracker()
        tracker.update(0, 100.0)
        tracker.update(86_400_000_000_001, 90.0)

        self.assertEqual(tracker.session_high, 90.0)
        self.assertEqual(tracker.session_low, 90.0)

    def test_session_tracker_tracks_high_low_intraday(self):
        tracker = SessionExtremeTracker()
        for price in [100.0, 105.0, 98.0, 103.0]:
            tracker.update(1_000_000, price)

        self.assertEqual(tracker.session_high, 105.0)
        self.assertEqual(tracker.session_low, 98.0)

    def test_session_near_high_true_within_pct(self):
        tracker = SessionExtremeTracker()
        tracker.update(0, 100.0)

        self.assertTrue(tracker.near_high(99.8, 0.003))
        self.assertFalse(tracker.near_high(99.6, 0.003))

    def test_footprint_dominant_correct(self):
        stream = [
            tick(0, 100.0, size=1.0, side=AggressorSide.BUYER),
            tick(1, 100.0, size=2.0, side=AggressorSide.BUYER),
            tick(2, 101.0, size=1.0, side=AggressorSide.SELLER),
        ]
        engine = FootprintEngine(tick_size=0.5, warm_period=1)
        for item in stream:
            engine.handle_trade_tick(item)
        self.assertEqual(engine.dominant_level, 100.0)
        self.assertEqual(engine.footprint_bias, 1)

    def test_footprint_prunes_expired_events_and_levels(self):
        engine = FootprintEngine(
            tick_size=0.5,
            window_ns=3_000_000_000,
            stack_threshold=2,
            warm_period=1,
        )
        for item in [
            tick(0, 100.0, size=1.0, side=AggressorSide.BUYER),
            tick(1, 100.5, size=2.0, side=AggressorSide.BUYER),
            tick(2, 101.0, size=1.0, side=AggressorSide.SELLER),
        ]:
            engine.handle_trade_tick(item)

        self.assertEqual(engine.dominant_level, 100.5)
        self.assertEqual(engine.footprint_bias, 1)
        self.assertTrue(engine.stacked)

        engine.handle_trade_tick(tick(4, 101.0, size=1.0, side=AggressorSide.SELLER))

        self.assertEqual(engine.dominant_level, 101.0)
        self.assertEqual(engine.footprint_bias, -1)
        self.assertFalse(engine.stacked)

    def test_ic_gate_deletes_noise(self):
        signal = [0.0 for _ in range(500)]
        prices = [50_000 + idx * 0.1 for idx in range(500)]
        timestamps = [idx * 60_000_000_000 for idx in range(500)]
        result = validate_engine("noise", signal, prices, timestamps)
        self.assertEqual(result["verdict"], "DELETE")

    def test_ic_harness_skips_warmup(self):
        stream = [tick(i, 100 + i * 0.1) for i in range(10)]
        result = run_ic_on_ticks(
            FootprintEngine,
            {"tick_size": 0.5, "warm_period": 5},
            lambda engine: float(engine.footprint_bias),
            stream,
        )
        self.assertEqual(result["sample_size"], 6)

    def test_vp_poc_stability(self):
        engine = VolumeProfileEngine(tick_size=0.5, warm_period=5)
        pocs = []
        for idx in range(20):
            engine.handle_trade_tick(tick(idx, 100.0 + (idx % 2) * 0.5))
            if engine.initialized and engine.poc is not None:
                pocs.append(engine.poc)
        max_shift = max(abs(pocs[i] - pocs[i - 1]) for i in range(1, len(pocs)))
        self.assertLessEqual(max_shift, 1.0)

    def test_vwap_tracks_inside_price_range(self):
        stream = [tick(i, 100.0 + (i % 5), size=1.0 + i * 0.1) for i in range(20)]
        engine = VWAPEngine(warm_period=5)
        prices = []
        for item in stream:
            engine.handle_trade_tick(item)
            prices.append(float(item.price))
        self.assertTrue(engine.initialized)
        self.assertGreater(engine.vwap, min(prices))
        self.assertLess(engine.vwap, max(prices))
        self.assertIsInstance(engine.deviation, float)

    def test_collinearity_detects_duplicate_signal(self):
        values = [float(idx) for idx in range(50)]
        self.assertEqual(check_collinearity(values, values), 1.0)

    def test_signed_to_tick_maps_legacy_signed_trade(self):
        converted = signed_to_tick(legacy_trade(side="SELL", price=101.0, size=2.0))
        self.assertEqual(converted.aggressor_side, AggressorSide.SELLER)
        self.assertEqual(float(converted.price), 101.0)


if __name__ == "__main__":
    unittest.main()
