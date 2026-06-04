"""S0 — trade signing and data quality firewall."""

from __future__ import annotations

from v72.contracts import V72PipelineState
from prime.nautilus_compat import TradeTick
from prime.phase0 import DataQualityFirewall, TradeSigner


class TruthStage:
    stage_id = "s0"

    def __init__(self, *, source: str = "BINANCE", session_id: str = "v72") -> None:
        self._signer = TradeSigner(source=source, session_id=session_id)
        self._firewall = DataQualityFirewall()

    def process(
        self,
        state: V72PipelineState,
        *,
        book=None,
    ) -> V72PipelineState:
        if state.tick is None:
            state.halted = True
            state.halt_reason = "MISSING_TICK"
            return state

        signed = self._signer.sign(state.tick)
        crossed = False
        if book is not None:
            crossed = book.bids[0][0] >= book.asks[0][0]
        quality = self._firewall.check(
            signed,
            receive_ts_ns=signed.timestamp_ns,
            crossed_book=crossed,
        )
        state.signed_trade = signed
        state.data_quality = quality
        state.stage_trace.append(self.stage_id)

        if quality.state == "HALT":
            state.halted = True
            state.halt_reason = "DATA_QUALITY_HALT"
        return state

    def reset(self) -> None:
        self._firewall = DataQualityFirewall()

    def ingest_tick(self, tick: TradeTick) -> V72PipelineState:
        state = V72PipelineState(tick=tick)
        return self.process(state)