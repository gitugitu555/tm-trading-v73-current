"""Microprice calculation."""


def microprice(bids: list[tuple[float, float]] | tuple[tuple[float, float], ...],
               asks: list[tuple[float, float]] | tuple[tuple[float, float], ...]) -> float:
    if not bids or not asks:
        raise ValueError("bids and asks are required")
    best_bid, bid_size = bids[0]
    best_ask, ask_size = asks[0]
    denom = bid_size + ask_size
    if denom <= 0:
        return (best_bid + best_ask) / 2.0
    return (best_bid * ask_size + best_ask * bid_size) / denom
