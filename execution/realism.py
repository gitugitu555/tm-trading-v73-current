"""Execution Realism Layer — V8.4.

Models lagged entries, slippage under adverse selection, and the execution illusion tax.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.types import BookSnapshot

@dataclass(frozen=True)
class ExecutionRealismResult:
    original_price: float
    effective_price: float
    lag_ms: float
    slippage_bps: float
    illusion_tax_bps: float
    effective_latency_ms: float
    fill_status: str  # FILLED, MISSED, DEGRADED


class ExecutionRealismEngine:
    """Computes execution realism metrics based on latency, book state, and queue details."""

    def __init__(
        self,
        base_latency_ms: float = 25.0,
        illusion_tax_multiplier: float = 1.5,
    ) -> None:
        self.base_latency_ms = base_latency_ms
        self.illusion_tax_multiplier = illusion_tax_multiplier

    def estimate_realism(
        self,
        book: BookSnapshot,
        side: int,  # +1 long, -1 short
        original_price: float,
        order_size: float,
        additional_latency_ms: float = 0.0,
    ) -> ExecutionRealismResult:
        """Estimate slippage, queue delay, and fill price adjustments.

        Under lagged execution, the effective entry price moves adversely:
        - Long entry: entry price increases with slippage and adverse book pressure.
        - Short entry: entry price decreases with slippage and adverse book pressure.
        """
        if side not in {-1, 1}:
            raise ValueError("side must be +1 or -1")
        if order_size <= 0:
            raise ValueError("order_size must be positive")

        effective_latency = self.base_latency_ms + additional_latency_ms
        mid = book.mid
        spread = book.best_ask - book.best_bid
        spread_bps = (spread / max(mid, 1e-12)) * 1e4

        # Compute imbalance-based adverse selection pressure
        bid_depth = sum(sz for _, sz in book.bids[:5])
        ask_depth = sum(sz for _, sz in book.asks[:5])
        total_depth = bid_depth + ask_depth
        imbalance = (bid_depth - ask_depth) / max(total_depth, 1e-12)

        # Adverse pressure: if side = +1 and imbalance is positive (more bids), price moves up
        # If side = -1 and imbalance is negative (more asks), price moves down
        adverse_pressure = imbalance if side > 0 else -imbalance
        pressure_factor = max(0.0, adverse_pressure)

        # Slippage: proportional to spread + size relative to depth
        size_slippage_bps = (order_size / max(total_depth, 1e-12)) * 10.0
        slippage_bps = (spread_bps * 0.5) + (effective_latency * 0.05) + (pressure_factor * 5.0) + size_slippage_bps

        # Execution Illusion Tax: extra penalty for assuming passive fill when queue is toxic
        # Higher if toxicity is high (approximated here by adverse pressure and latency)
        illusion_tax_bps = self.illusion_tax_multiplier * (spread_bps * 0.2 + pressure_factor * 8.0)

        # Compute adjusted entry price
        total_slippage_pct = (slippage_bps + illusion_tax_bps) / 1e4
        if side > 0:
            effective_price = original_price * (1.0 + total_slippage_pct)
        else:
            effective_price = original_price * (1.0 - total_slippage_pct)

        # Determine if we fill at all (if slippage exceeds a critical threshold, status is MISSED)
        if total_slippage_pct > 0.015:  # 1.5% max allowable execution slippage
            status = "MISSED"
            effective_price = original_price  # Return original if missed
        elif total_slippage_pct > 0.005:
            status = "DEGRADED"
        else:
            status = "FILLED"

        return ExecutionRealismResult(
            original_price=original_price,
            effective_price=round(effective_price, 6),
            lag_ms=effective_latency,
            slippage_bps=round(slippage_bps, 4),
            illusion_tax_bps=round(illusion_tax_bps, 4),
            effective_latency_ms=effective_latency,
            fill_status=status,
        )
