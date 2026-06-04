"""Large print and cluster detector."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import mean, pstdev

from core.types import SignedTrade


@dataclass(frozen=True)
class LargePrintEvent:
    side: str
    notional_quote: float
    z_score: float
    reason_codes: tuple[str, ...]


class LargePrintDetector:
    def __init__(self, *, window: int = 100, z_threshold: float = 3.0) -> None:
        self.window = window
        self.z_threshold = float(z_threshold)
        self._notionals: deque[float] = deque(maxlen=window)

    def update(self, trade: SignedTrade) -> LargePrintEvent | None:
        baseline = list(self._notionals)
        self._notionals.append(trade.notional_quote)
        if len(baseline) < 5:
            return None
        mu = mean(baseline)
        sigma = pstdev(baseline) or 1.0
        z_score = (trade.notional_quote - mu) / sigma
        if z_score >= self.z_threshold:
            return LargePrintEvent(
                side=trade.side,
                notional_quote=trade.notional_quote,
                z_score=z_score,
                reason_codes=("LARGE_PRINT", f"{trade.side}_WHALE_TAPE"),
            )
        return None
