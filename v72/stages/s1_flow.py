"""S1 — Phase 1 microstructure engines (CVD, footprint, delta, VWAP)."""

from __future__ import annotations

from prime.contracts import MicrostructureSnapshot, hash_dict
from prime.nautilus_compat import TradeTick
from prime.phase1 import CVDEngine, DeltaVelocityEngine, FootprintEngine, VWAPEngine
from v72.contracts import V72PipelineState


class FlowStage:
    stage_id = "s1"

    def __init__(
        self,
        *,
        footprint_tick_size: float = 0.5,
        divergence_threshold: float = 100.0,
        vwap_warm_period: int = 50,
    ) -> None:
        self._cvd = CVDEngine(divergence_threshold=divergence_threshold)
        self._footprint = FootprintEngine(tick_size=footprint_tick_size)
        self._delta = DeltaVelocityEngine()
        self._vwap = VWAPEngine(warm_period=vwap_warm_period)
        self._tick_count = 0

    def reset(self) -> None:
        tick_size = self._footprint._tick_size
        warm = self._vwap._min_ticks
        self._cvd.reset_session()
        self._footprint = FootprintEngine(tick_size=tick_size)
        self._delta = DeltaVelocityEngine()
        self._vwap = VWAPEngine(warm_period=warm)
        self._tick_count = 0

    def process(
        self,
        state: V72PipelineState,
        *,
        book=None,
    ) -> V72PipelineState:
        if state.halted or state.tick is None:
            return state

        tick = state.tick
        self._cvd.handle_trade_tick(tick)
        self._footprint.handle_trade_tick(tick)
        self._delta.handle_trade_tick(tick)
        self._vwap.handle_trade_tick(tick)
        self._tick_count += 1

        state.microstructure = self._build_snapshot(tick)
        state.stage_trace.append(self.stage_id)
        return state

    def _build_snapshot(self, tick: TradeTick) -> MicrostructureSnapshot:
        ts = int(tick.ts_event)
        payload = {
            "cvd": self._cvd.cvd_session,
            "cvd_5m": self._cvd.cvd_5m,
            "div": self._cvd.divergence,
            "fp": self._footprint.footprint_bias,
        }
        return MicrostructureSnapshot(
            timestamp_ns=ts,
            input_hash=hash_dict(payload),
            cvd_session=self._cvd.cvd_session,
            cvd_1m=self._cvd.cvd_1m,
            cvd_5m=self._cvd.cvd_5m,
            cvd_divergence=self._cvd.divergence,
            cvd_trend=self._cvd.trend,
            delta_velocity=self._delta.velocity,
            delta_acceleration=self._delta.acceleration,
            exhaustion=self._delta.exhaustion,
            dominant_level=self._footprint.dominant_level,
            footprint_bias=self._footprint.footprint_bias,
            footprint_stacked=self._footprint.stacked,
            vp_poc=self._footprint.dominant_level,
            vp_vah=None,
            vp_val=None,
            vp_position=0.0,
            confidence_scalar=1.0 if self._cvd.initialized else 0.5,
            trade_count=self._tick_count,
        )

    @property
    def vwap_deviation(self) -> float | None:
        if not self._vwap.initialized:
            return None
        return self._vwap.deviation