"""Weighted L2 order book imbalance."""


class OrderBookImbalanceEngine:
    def update(
        self,
        bids: list[tuple[float, float]] | tuple[tuple[float, float], ...],
        asks: list[tuple[float, float]] | tuple[tuple[float, float], ...],
    ) -> float:
        if not bids or not asks:
            raise ValueError("bids and asks are required")
        mid = (bids[0][0] + asks[0][0]) / 2.0
        bid_depth = sum(qty / max(mid - price, 1e-9) for price, qty in bids)
        ask_depth = sum(qty / max(price - mid, 1e-9) for price, qty in asks)
        denom = bid_depth + ask_depth
        return 0.0 if denom == 0 else (bid_depth - ask_depth) / denom
