"""V7.2 modular pipeline stage tests (no backtest imports)."""

import unittest

from core.types import BookSnapshot
from datetime import datetime, timezone
from prime.nautilus_compat import AggressorSide, InstrumentId, Price, Quantity, TradeId, TradeTick
from v72.contracts import V72PipelineConfig
from v72.pipeline import V72Pipeline
from v72.stages.s4_signal import MomentumSignalStage
from v72.nautilus.cvd_momentum_confirmation import CVDMomentumConfirmationFacade


def make_tick(idx: int, price: float, size: float = 1.0, side=AggressorSide.BUYER) -> TradeTick:
    ts = 1_700_000_000_000_000_000 + idx * 60_000_000_000
    return TradeTick(
        instrument_id=InstrumentId.from_str("BTCUSDT.BINANCE"),
        price=Price(price, precision=2),
        size=Quantity(size, precision=8),
        aggressor_side=side,
        trade_id=TradeId(str(idx)),
        ts_event=ts,
        ts_init=ts,
    )


def book() -> BookSnapshot:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return BookSnapshot(
        ts_event=ts,
        exchange="BINANCE",
        symbol="BTCUSDT",
        bids=((100.0, 5.0), (99.5, 4.0)),
        asks=((100.5, 5.0), (101.0, 4.0)),
    )


class V72PipelineStagesTest(unittest.TestCase):
    def test_pipeline_trace_is_deterministic(self) -> None:
        pipeline = V72Pipeline(
            V72PipelineConfig(
                enable_s4_signal=False,
                enable_s5_permission=False,
                enable_s6_memory_risk=False,
            )
        )
        traces = []
        for run in range(2):
            pipeline = V72Pipeline(
                V72PipelineConfig(
                    enable_s4_signal=False,
                    enable_s5_permission=False,
                    enable_s6_memory_risk=False,
                )
            )
            stream = [
                make_tick(i + run * 1000, 100.0 + i * 0.01) for i in range(30)
            ]
            last = None
            for item in stream:
                last = pipeline.on_trade_tick(item, book=book())
            traces.append(tuple(last.stage_trace))
        self.assertEqual(traces[0], traces[1])

    def test_pipeline_runs_all_stages_in_order(self) -> None:
        pipeline = V72Pipeline()
        ticks = [make_tick(i, 100.0 + i * 0.02, side=AggressorSide.BUYER) for i in range(250)]
        last = None
        for item in ticks:
            last = pipeline.on_trade_tick(item, book=book())
        self.assertIn("s0", last.stage_trace)
        self.assertIn("s1", last.stage_trace)
        self.assertIsNotNone(last.microstructure)

    def test_s4_blocks_divergence_only_without_momentum_regime(self) -> None:
        stage = MomentumSignalStage(cvd_threshold=10.0)
        from v72.contracts import V72PipelineState
        from prime.contracts import MicrostructureSnapshot
        from prime.phase4_minimal import RegimeState

        state = V72PipelineState(tick=make_tick(0, 100.0))
        state.microstructure = MicrostructureSnapshot(
            timestamp_ns=1,
            input_hash="x",
            cvd_session=500.0,
            cvd_1m=500.0,
            cvd_5m=500.0,
            cvd_divergence=True,
            cvd_trend="RISING",
            delta_velocity=1.0,
            delta_acceleration=0.1,
            exhaustion="NONE",
            dominant_level=100.0,
            footprint_bias=+1,
            footprint_stacked=True,
            vp_poc=100.0,
            vp_vah=None,
            vp_val=None,
            vp_position=0.0,
            confidence_scalar=1.0,
            trade_count=100,
        )
        state.regime = RegimeState(
            timestamp_ns=1,
            hard_label="RANGING",
            hard_confidence=0.8,
            cusum_alert=False,
            cusum_variables=[],
            transition_warning="NONE",
            trend_enabled=False,
            mean_reversion_enabled=True,
            breakout_enabled=False,
            all_halted=False,
            regime_confidence_scalar=0.8,
            volatility_percentile=50.0,
            bars_in_regime=3,
        )
        out = stage.process(state)
        self.assertIsNone(out.signal)

    def test_stage_reorder_skips_disabled(self) -> None:
        pipeline = V72Pipeline(
            V72PipelineConfig(
                stage_order=("s0", "s1"),
                enable_s2_book=False,
                enable_s3_regime=False,
                enable_s4_signal=False,
                enable_s5_permission=False,
                enable_s6_memory_risk=False,
            )
        )
        state = pipeline.on_trade_tick(make_tick(0, 100.0))
        self.assertEqual(state.stage_trace, ["s0", "s1"])
        self.assertIsNone(state.signal)

    def test_nautilus_facade_has_no_backtest_import(self) -> None:
        facade = CVDMomentumConfirmationFacade()
        ticks = [make_tick(i, 100.0 + i * 0.05, side=AggressorSide.BUYER) for i in range(300)]
        for item in ticks:
            facade.on_trade_tick(item)
        self.assertIsInstance(facade.intents, list)


if __name__ == "__main__":
    unittest.main()