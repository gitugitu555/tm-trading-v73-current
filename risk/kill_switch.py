"""Minimal kill switch gate."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskGateDecision:
    allow: bool
    risk_scalar: float
    reason_codes: tuple[str, ...]


class KillSwitch:
    def evaluate(
        self,
        *,
        data_quality_status: str = "CLEAN",
        daily_loss_hit: bool = False,
        spoofing_extreme: bool = False,
        model_confidence: float = 1.0,
    ) -> RiskGateDecision:
        reasons: list[str] = []
        if daily_loss_hit:
            reasons.append("MAX_DAILY_LOSS")
        if data_quality_status in {"QUARANTINE", "HALT"}:
            reasons.append("DATA_QUALITY_HALT")
        if spoofing_extreme:
            reasons.append("SPOOFING_EXTREME")
        if model_confidence < 0.2:
            reasons.append("MODEL_CONFIDENCE_COLLAPSE")
        return RiskGateDecision(
            allow=not reasons,
            risk_scalar=0.0 if reasons else 1.0,
            reason_codes=tuple(reasons),
        )
