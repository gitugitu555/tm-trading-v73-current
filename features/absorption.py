"""Simple deterministic absorption detector."""

from __future__ import annotations

from collections import deque

from core.types import SignedTrade
from features.trade_signing import signed_delta


class AbsorptionEngine:
    def __init__(
        self,
        *,
        window: int = 20,
        delta_threshold: float = 100.0,
        max_price_move: float = 1.0,
    ) -> None:
        self.window = window
        self.delta_threshold = float(delta_threshold)
        self.max_price_move = float(max_price_move)
        self._events: deque[tuple[float, float]] = deque(maxlen=window)

    def update(self, trade: SignedTrade) -> str:
        self._events.append((trade.price, signed_delta(trade.size_base, trade.side)))
        if len(self._events) < 2:
            return "NONE"
        prices = [event[0] for event in self._events]
        total_delta = sum(event[1] for event in self._events)
        price_move = prices[-1] - prices[0]
        if total_delta >= self.delta_threshold and abs(price_move) <= self.max_price_move:
            return "ASK_ABSORPTION"
        if total_delta <= -self.delta_threshold and abs(price_move) <= self.max_price_move:
            return "BID_ABSORPTION"
        return "NONE"

    def reset(self) -> None:
        self._events.clear()
