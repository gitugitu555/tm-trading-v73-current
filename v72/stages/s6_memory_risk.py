"""S6 — kill switch gate and setup memory export."""

from __future__ import annotations

from datetime import datetime, timezone

from core.types import FeatureSnapshot
from memory.setup_summary import build_setup_memory_object
from risk.kill_switch import KillSwitch
from v72.contracts import TradeIntentV72, V72PipelineState


def _to_feature_snapshot(state: V72PipelineState) -> FeatureSnapshot | None:
    if state.signed_trade is None:
        return None
    st = state.signed_trade
    bi = state.book_intel
    ms = state.microstructure
    ts = datetime.fromtimestamp(st.timestamp_ns / 1_000_000_000, tz=timezone.utc)
    return FeatureSnapshot(
        ts_event=ts,
        instrument=st.symbol,
        cvd=ms.cvd_session if ms else 0.0,
        delta_velocity=ms.delta_velocity if ms else 0.0,
        delta_acceleration=ms.delta_acceleration if ms else 0.0,
        vpin=bi.vpin if bi else 0.0,
        microprice=bi.microprice,
        book_imbalance=bi.book_imbalance if bi else 0.0,
        absorption=bi.absorption if bi else "NONE",
        spoof_regime=bi.spoof_regime if bi else "NONE",
        iceberg_side="NONE",
        whale_pressure=bi.whale_pressure if bi else 0.0,
        reason_codes=bi.reason_codes if bi else (),
        regime=state.regime.hard_label if state.regime else "UNKNOWN",
    )


class MemoryRiskStage:
    stage_id = "s6"

    def __init__(self, *, trade_notional_usdt: float = 1000.0) -> None:
        self._kill = KillSwitch()
        self._notional = trade_notional_usdt

    def process(
        self,
        state: V72PipelineState,
        *,
        book=None,
    ) -> V72PipelineState:
        if state.halted:
            state.stage_trace.append(f"{self.stage_id}:HALTED")
            return state

        dq_state = state.data_quality.state if state.data_quality else "CLEAN"
        spoof_extreme = bool(
            state.book_intel and state.book_intel.spoof_regime == "SPOOFING_ACTIVE"
        )
        risk = self._kill.evaluate(
            data_quality_status=dq_state,
            spoofing_extreme=spoof_extreme,
            model_confidence=state.signal.strength if state.signal else 0.0,
        )

        if not risk.allow:
            state.halted = True
            state.halt_reason = "RISK_KILL_SWITCH"
            state.stage_trace.append(f"{self.stage_id}:KILL")
            return state

        if state.signal and state.permission:
            perm = state.permission
            if perm.verdict in {"APPROVE", "REDUCED"} and perm.permitted_size > 0:
                codes = tuple(
                    dict.fromkeys(
                        (
                            *state.signal.reason_codes,
                            f"PERM_{perm.verdict}",
                            *(perm.blocking_codes or []),
                        )
                    )
                )
                state.trade_intent = TradeIntentV72(
                    instrument_id=state.signed_trade.symbol if state.signed_trade else "UNKNOWN",
                    direction=state.signal.side,
                    urgency="NORMAL" if perm.verdict == "APPROVE" else "REDUCED",
                    max_notional=self._notional * perm.size_scalar,
                    entry_type="LIMIT",
                    permission_verdict=perm.verdict,
                    permission_kq=perm.kq,
                    reason_codes=codes,
                )

        snapshot = _to_feature_snapshot(state)
        if snapshot and state.signal:
            mem = build_setup_memory_object(
                snapshot=snapshot,
                setup_type=state.signal.strategy,
                outcome="pending",
            )
            state.memory_object = mem.to_json_ready()

        state.stage_trace.append(self.stage_id)
        return state