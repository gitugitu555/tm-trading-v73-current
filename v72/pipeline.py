"""Composable V7.2 pipeline — stages can be reordered or disabled."""

from __future__ import annotations

from core.types import BookSnapshot
from prime.nautilus_compat import TradeTick
from v72.contracts import V72PipelineConfig, V72PipelineState
from v72.stages.s0_truth import TruthStage
from v72.stages.s1_flow import FlowStage
from v72.stages.s2_book import BookIntelligenceStage
from v72.stages.s3_regime import RegimeStage
from v72.stages.s4_signal import MomentumSignalStage
from v72.stages.s5_permission import PermissionStage
from v72.stages.s6_memory_risk import MemoryRiskStage


class V72Pipeline:
    """Run trade ticks through enabled stages without backtest coupling."""

    def __init__(self, config: V72PipelineConfig | None = None) -> None:
        self.config = config or V72PipelineConfig()
        self._stages = self._build_stages()
        self._flow = self._stages["s1"]

    def _build_stages(self) -> dict[str, object]:
        cfg = self.config
        return {
            "s0": TruthStage(source=cfg.source, session_id=cfg.session_id),
            "s1": FlowStage(
                footprint_tick_size=cfg.footprint_tick_size,
                divergence_threshold=cfg.cvd_threshold,
            ),
            "s2": BookIntelligenceStage(tick_size=cfg.footprint_tick_size),
            "s3": RegimeStage(),
            "s4": MomentumSignalStage(cvd_threshold=cfg.cvd_threshold),
            "s5": PermissionStage(
                kq_approve=cfg.kq_approve,
                base_position_size=cfg.base_position_size,
                use_auction_state_gate=cfg.use_auction_state_gate,
            ),
            "s6": MemoryRiskStage(trade_notional_usdt=cfg.trade_notional_usdt),
        }

    def reset(self) -> None:
        if "s0" in self._stages and hasattr(self._stages["s0"], "reset"):
            self._stages["s0"].reset()
        if hasattr(self._flow, "reset"):
            self._flow.reset()
        if "s2" in self._stages and hasattr(self._stages["s2"], "reset"):
            self._stages["s2"].reset()

    def on_trade_tick(
        self,
        tick: TradeTick,
        *,
        book: BookSnapshot | None = None,
    ) -> V72PipelineState:
        state = V72PipelineState(tick=tick)
        for stage_id in self.config.stage_order:
            if not self._enabled(stage_id):
                continue
            stage = self._stages[stage_id]
            state = stage.process(state, book=book)
            if stage_id == "s1" and isinstance(stage, FlowStage):
                state.vwap_deviation = stage.vwap_deviation
            if state.halted:
                break
        return state

    def _enabled(self, stage_id: str) -> bool:
        if stage_id == "s2":
            return self.config.enable_s2_book
        if stage_id == "s3":
            return self.config.enable_s3_regime
        if stage_id == "s4":
            return self.config.enable_s4_signal
        if stage_id == "s5":
            return self.config.enable_s5_permission
        if stage_id == "s6":
            return self.config.enable_s6_memory_risk
        return True