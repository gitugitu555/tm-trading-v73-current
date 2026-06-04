"""Deterministic AlphaPermission fallback."""

from __future__ import annotations

from dataclasses import dataclass

from core.types import FeatureSnapshot


@dataclass(frozen=True)
class AlphaPermission:
    direction: int
    strength: float
    confidence: float
    regime_scalar: float
    whale_scalar: float
    execution_scalar: float
    risk_scalar: float
    reason_codes: tuple[str, ...]

    @property
    def permission(self) -> float:
        return (
            self.direction
            * self.strength
            * self.confidence
            * self.regime_scalar
            * self.whale_scalar
            * self.execution_scalar
            * self.risk_scalar
        )

    @property
    def allow_trade(self) -> bool:
        return self.direction != 0 and self.risk_scalar > 0.0 and self.confidence >= 0.35


class AlphaPermissionEngine:
    def compute(self, snapshot: FeatureSnapshot) -> AlphaPermission:
        score = 0.0
        reason_codes: list[str] = []

        if snapshot.absorption == "BID_ABSORPTION":
            score += 25.0
            reason_codes.append("BID_ABSORPTION_LONG")
        elif snapshot.absorption == "ASK_ABSORPTION":
            score -= 25.0
            reason_codes.append("ASK_ABSORPTION_SHORT")

        if snapshot.delta_velocity > 0:
            score += 20.0
            reason_codes.append("CVD_VELOCITY_UP")
        elif snapshot.delta_velocity < 0:
            score -= 20.0
            reason_codes.append("CVD_VELOCITY_DOWN")

        if snapshot.delta_acceleration > 0:
            score += 15.0
            reason_codes.append("DELTA_ACCELERATION_UP")
        elif snapshot.delta_acceleration < 0:
            score -= 15.0
            reason_codes.append("DELTA_ACCELERATION_DOWN")

        score += max(-15.0, min(15.0, snapshot.book_imbalance * 15.0))
        if abs(snapshot.book_imbalance) >= 0.25:
            reason_codes.append("L2_IMBALANCE")

        score += max(-15.0, min(15.0, snapshot.whale_pressure * 0.15))
        if abs(snapshot.whale_pressure) >= 10.0:
            reason_codes.append("WHALE_PRESSURE")

        regime_scalar = 0.7 if snapshot.regime in {"STRESS", "SPOOFING_ACTIVE"} else 1.0
        execution_scalar = 0.4 if snapshot.spoof_regime == "SPOOFING_ACTIVE" else 1.0
        risk_scalar = 0.0 if snapshot.spoof_regime == "SPOOFING_ACTIVE" and abs(score) < 70 else 1.0
        if risk_scalar == 0.0:
            reason_codes.append("BLOCKED_BY_SPOOFING")

        if abs(score) < 25.0:
            return AlphaPermission(
                direction=0,
                strength=abs(score),
                confidence=0.0,
                regime_scalar=regime_scalar,
                whale_scalar=1.0,
                execution_scalar=execution_scalar,
                risk_scalar=risk_scalar,
                reason_codes=tuple(reason_codes or ["NO_EDGE_THRESHOLD"]),
            )

        direction = 1 if score > 0 else -1
        confidence = min(1.0, abs(score) / 100.0)
        whale_scalar = 1.15 if direction * snapshot.whale_pressure > 15.0 else 1.0
        if direction * snapshot.whale_pressure < -15.0:
            whale_scalar = 0.4
            reason_codes.append("WHALE_AGAINST_TRADE")

        return AlphaPermission(
            direction=direction,
            strength=abs(score),
            confidence=confidence,
            regime_scalar=regime_scalar,
            whale_scalar=whale_scalar,
            execution_scalar=execution_scalar,
            risk_scalar=risk_scalar,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
        )
