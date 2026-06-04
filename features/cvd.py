"""Cumulative volume delta engine."""

from __future__ import annotations

from core.types import SignedTrade
from features.trade_signing import signed_delta


class CVDEngine:
    def __init__(self, initial_cvd: float = 0.0) -> None:
        self.cvd = float(initial_cvd)

    def update(self, signed_trade: SignedTrade) -> dict[str, float]:
        delta = signed_delta(signed_trade.size_base, signed_trade.side)
        self.cvd += delta
        return {"delta": delta, "cvd": self.cvd}

    def reset(self) -> None:
        self.cvd = 0.0
