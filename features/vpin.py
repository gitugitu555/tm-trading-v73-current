"""Volume-synchronized probability of informed trading approximation."""

from __future__ import annotations

from collections import deque

from core.types import SignedTrade


class VPINEngine:
    def __init__(self, window: int = 50) -> None:
        if window <= 0:
            raise ValueError("window must be positive")
        self.window = window
        self._flows: deque[tuple[float, float]] = deque(maxlen=window)

    def update(self, trade: SignedTrade) -> float:
        if trade.side == "BUY":
            buy, sell = trade.size_base, 0.0
        elif trade.side == "SELL":
            buy, sell = 0.0, trade.size_base
        else:
            buy = sell = trade.size_base * 0.5
        self._flows.append((buy, sell))
        total_buy = sum(item[0] for item in self._flows)
        total_sell = sum(item[1] for item in self._flows)
        total = total_buy + total_sell
        return 0.0 if total == 0 else abs(total_buy - total_sell) / total

    def reset(self) -> None:
        self._flows.clear()
