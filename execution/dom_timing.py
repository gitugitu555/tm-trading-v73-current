"""Execution-quality heuristics for order-book timing."""

from __future__ import annotations

from dataclasses import dataclass
import math

from core.types import BookSnapshot
from features.microprice import microprice


@dataclass(frozen=True)
class DOMTimingSnapshot:
    spread_bps: float
    mid_price: float
    microprice: float
    top5_bid_depth: float
    top5_ask_depth: float
    top10_bid_depth: float
    top10_ask_depth: float
    depth_imbalance_top5: float
    depth_imbalance_top10: float
    queue_ahead: float
    fill_probability: float
    slippage_bps: float
    queue_penalty_bps: float
    effective_entry_price: float
    execution_quality_score: float
    large_wall_added: bool
    large_wall_removed: bool
    wall_lifetime_ms: float


def analyze_dom_timing(
    book: BookSnapshot,
    *,
    side: int,
    order_size: float,
    latency_ms: float = 25.0,
    queue_ahead: float | None = None,
) -> DOMTimingSnapshot:
    """Estimate timing quality for a prospective entry.

    side: +1 long, -1 short.
    """
    if side not in {-1, 1}:
        raise ValueError("side must be +1 or -1")
    if order_size <= 0:
        raise ValueError("order_size must be positive")

    mid = book.mid
    spread_bps = (book.best_ask - book.best_bid) / max(mid, 1e-12) * 1e4
    micro = microprice(book.bids, book.asks)
    top5_bid = sum(size for _, size in book.bids[:5])
    top5_ask = sum(size for _, size in book.asks[:5])
    top10_bid = sum(size for _, size in book.bids[:10])
    top10_ask = sum(size for _, size in book.asks[:10])
    depth_imb_top5 = (top5_bid - top5_ask) / max(top5_bid + top5_ask, 1e-12)
    depth_imb_top10 = (top10_bid - top10_ask) / max(top10_bid + top10_ask, 1e-12)

    q_ahead = queue_ahead if queue_ahead is not None else (top5_ask if side > 0 else top5_bid)
    horizon = max(latency_ms, 1.0)
    lambda_hit = 0.02 + abs(depth_imb_top5) * 0.08 + abs(depth_imb_top10) * 0.05
    lambda_cancel = 0.01 + max(0.0, depth_imb_top5) * 0.04
    fill_probability = 1.0 - math.exp(-(lambda_hit + lambda_cancel) * horizon / max(q_ahead + order_size, 1e-12))
    fill_probability = min(max(fill_probability, 0.0), 1.0)

    adverse_drift_bps = max(0.0, (micro - mid) / max(mid, 1e-12) * 1e4) if side > 0 else max(0.0, (mid - micro) / max(mid, 1e-12) * 1e4)
    slippage_bps = max(0.0, spread_bps * 0.5 + order_size / max(top10_bid + top10_ask, 1e-12) * 8.0)
    queue_penalty_bps = (1.0 - fill_probability) * (0.5 * spread_bps + adverse_drift_bps)
    total_bps = slippage_bps + queue_penalty_bps
    effective_entry_price = book.best_ask if side > 0 else book.best_bid
    effective_entry_price *= 1.0 + total_bps / 1e4 if side > 0 else 1.0 - total_bps / 1e4
    execution_quality_score = math.exp(-total_bps / 50.0)

    return DOMTimingSnapshot(
        spread_bps=round(spread_bps, 6),
        mid_price=round(mid, 6),
        microprice=round(micro, 6),
        top5_bid_depth=round(top5_bid, 6),
        top5_ask_depth=round(top5_ask, 6),
        top10_bid_depth=round(top10_bid, 6),
        top10_ask_depth=round(top10_ask, 6),
        depth_imbalance_top5=round(depth_imb_top5, 6),
        depth_imbalance_top10=round(depth_imb_top10, 6),
        queue_ahead=round(q_ahead, 6),
        fill_probability=round(fill_probability, 6),
        slippage_bps=round(slippage_bps, 6),
        queue_penalty_bps=round(queue_penalty_bps, 6),
        effective_entry_price=round(effective_entry_price, 6),
        execution_quality_score=round(execution_quality_score, 6),
        large_wall_added=False,
        large_wall_removed=False,
        wall_lifetime_ms=0.0,
    )
