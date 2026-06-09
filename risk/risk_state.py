"""Deterministic capital-protection state machine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskStateSnapshot:
    state: str
    allow: bool
    risk_scalar: float
    reason_codes: tuple[str, ...]
    position_scalar: float


class RiskStateEngine:
    """Simple drawdown/streak/exposure governor."""

    def __init__(
        self,
        *,
        daily_halt_r: float = -3.0,
        weekly_halt_r: float = -8.0,
        reduce_r: float = -1.5,
        consecutive_loss_halt: int = 4,
        max_exposure: float = 1.0,
    ) -> None:
        self.daily_halt_r = daily_halt_r
        self.weekly_halt_r = weekly_halt_r
        self.reduce_r = reduce_r
        self.consecutive_loss_halt = consecutive_loss_halt
        self.max_exposure = max_exposure

    def evaluate(
        self,
        *,
        daily_pnl_r: float,
        weekly_pnl_r: float,
        consecutive_losses: int,
        gross_exposure: float,
        toxicity_state: str = "BENIGN",
    ) -> RiskStateSnapshot:
        reasons: list[str] = []
        if daily_pnl_r <= self.daily_halt_r:
            reasons.append("DAILY_HALT")
        if weekly_pnl_r <= self.weekly_halt_r:
            reasons.append("WEEKLY_HALT")
        if consecutive_losses >= self.consecutive_loss_halt:
            reasons.append("LOSS_STREAK_HALT")
        if gross_exposure > self.max_exposure:
            reasons.append("EXPOSURE_CAP")
        if toxicity_state == "HIGH_TOXICITY":
            reasons.append("TOXICITY_HALT")

        state = "ALLOW"
        risk_scalar = 1.0
        position_scalar = 1.0
        if "WEEKLY_HALT" in reasons or "DAILY_HALT" in reasons or "LOSS_STREAK_HALT" in reasons:
            state = "HALT"
            risk_scalar = 0.0
            position_scalar = 0.0
        elif "EXPOSURE_CAP" in reasons or toxicity_state in {"RISING_TOXICITY", "HIGH_TOXICITY"}:
            state = "REDUCE_SIZE"
            risk_scalar = 0.5
            position_scalar = 0.5
        if toxicity_state == "HIGH_TOXICITY" and state == "ALLOW":
            state = "PAUSE_SESSION"
            risk_scalar = 0.0
            position_scalar = 0.0
        return RiskStateSnapshot(
            state=state,
            allow=state == "ALLOW",
            risk_scalar=risk_scalar,
            reason_codes=tuple(reasons),
            position_scalar=position_scalar,
        )
