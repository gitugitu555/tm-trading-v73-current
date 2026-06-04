"""S4 — CVDMomentumConfirmation signal (V720: momentum, not divergence entry)."""

from __future__ import annotations

from prime.phase4_minimal import HardRegimeClassifier
from v72.contracts import SignalCandidate, V72PipelineState


class MomentumSignalStage:
    """Emit candidate signals only — no orders, no backtest."""

    stage_id = "s4"
    strategy_name = "CVDMomentumConfirmation"

    def __init__(self, *, cvd_threshold: float = 100.0) -> None:
        self._cvd_threshold = cvd_threshold

    def process(
        self,
        state: V72PipelineState,
        *,
        book=None,
    ) -> V72PipelineState:
        if state.halted or state.microstructure is None or state.regime is None or state.tick is None:
            return state

        if not HardRegimeClassifier.gate_for_signal_mode(state.regime, "momentum"):
            state.stage_trace.append(f"{self.stage_id}:REGIME_BLOCKED")
            return state

        ms = state.microstructure
        regime = state.regime
        side = self._momentum_side(regime.hard_label, ms.cvd_session)
        if side == 0:
            state.stage_trace.append(f"{self.stage_id}:NO_THRESHOLD")
            return state

        if ms.footprint_bias != side:
            state.stage_trace.append(f"{self.stage_id}:FOOTPRINT_MISMATCH")
            return state

        # V720: divergence is not the primary entry gate.
        strength = min(1.0, abs(ms.cvd_session) / (self._cvd_threshold * 2))
        if ms.footprint_stacked:
            strength = min(1.0, strength + 0.15)
        if ms.exhaustion == "NONE":
            strength = min(1.0, strength + 0.10)

        ts = int(state.tick.ts_event)
        price = float(state.tick.price)
        state.signal = SignalCandidate(
            signal_id=f"MOM_{ts}_{side}",
            timestamp_ns=ts,
            side=side,
            strength=round(strength, 6),
            price=price,
            strategy=self.strategy_name,
            reason_codes=(
                f"REGIME_{regime.hard_label}",
                "CVD_MOMENTUM",
                "FOOTPRINT_ALIGNED",
            ),
        )
        state.stage_trace.append(self.stage_id)
        return state

    def _momentum_side(self, regime_label: str, cvd_session: float) -> int:
        if regime_label == "TREND_BULL" and cvd_session > self._cvd_threshold:
            return +1
        if regime_label == "TREND_BEAR" and cvd_session < -self._cvd_threshold:
            return -1
        return 0