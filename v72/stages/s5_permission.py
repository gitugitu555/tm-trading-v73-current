"""S5 — AlphaPermission multiplier chain (decoupled from backtester)."""

from __future__ import annotations

from prime.phase5_chunkb import AlphaPermissionEngineChunkB
from v72.contracts import V72PipelineState


class PermissionStage:
    stage_id = "s5"

    def __init__(
        self,
        *,
        kq_approve: float = 0.55,
        base_position_size: float = 0.01,
        use_auction_state_gate: bool = False,
    ) -> None:
        self._engine = AlphaPermissionEngineChunkB(
            kq_approve=kq_approve,
            base_position_size=base_position_size,
            use_auction_state_gate=use_auction_state_gate,
        )

    def process(
        self,
        state: V72PipelineState,
        *,
        book=None,
    ) -> V72PipelineState:
        if state.halted or state.signal is None or state.regime is None or state.data_quality is None:
            return state

        ms = state.microstructure
        permission = self._engine.evaluate(
            signal_id=state.signal.signal_id,
            timestamp_ns=state.signal.timestamp_ns,
            trade_side=state.signal.side,
            raw_strength=state.signal.strength,
            quality_snapshot=state.data_quality,
            regime=state.regime,
            cvd_divergence=bool(ms and ms.cvd_divergence),
            cvd_5m=ms.cvd_5m if ms else 0.0,
            signal_mode="momentum",
            vwap_deviation=state.vwap_deviation,
            auction_state=None,
        )
        state.permission = permission
        state.stage_trace.append(self.stage_id)
        return state