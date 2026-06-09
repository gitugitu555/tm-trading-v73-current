"""Queue imbalance and microprice diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .microprice import microprice


@dataclass(frozen=True)
class QueueImbalanceSnapshot:
    top1: float | None
    top5: float | None
    top10: float | None
    weighted_imbalance: float | None
    spread_bps: float | None
    microprice: float | None
    microprice_drift_bps: float | None
    depth_top5: float | None
    depth_top10: float | None
    book_agreement_score: float
    book_trap_score: float
    levels_used: int


class QueueImbalanceEngine:
    """Compute queue imbalance across top-of-book and deeper levels."""

    def __init__(self, *, max_levels: int = 10, decay: float = 0.75) -> None:
        if max_levels < 1:
            raise ValueError("max_levels must be >= 1")
        if not 0.0 < decay <= 1.0:
            raise ValueError("decay must be in (0, 1]")
        self.max_levels = max_levels
        self.decay = decay
        self._last_snapshot = self._empty_snapshot()

    def update(
        self,
        bids: Sequence[tuple[float, float]],
        asks: Sequence[tuple[float, float]],
    ) -> QueueImbalanceSnapshot:
        if not bids or not asks:
            self._last_snapshot = self._empty_snapshot()
            return self._last_snapshot

        n_levels = min(len(bids), len(asks), self.max_levels)
        if n_levels <= 0:
            self._last_snapshot = self._empty_snapshot()
            return self._last_snapshot

        imbalance_curve = [_imbalance_for_levels(bids, asks, level) for level in (1, 5, 10)]
        top1, top5, top10 = imbalance_curve

        levels = min(n_levels, 10)
        weighted_values = [_imbalance_for_levels(bids, asks, level) for level in range(1, levels + 1)]
        weights = [self.decay ** idx for idx in range(len(weighted_values))]
        weighted_imbalance = _weighted_mean(weighted_values, weights)

        best_bid, _ = bids[0]
        best_ask, _ = asks[0]
        mid = 0.5 * (best_bid + best_ask)
        spread_bps = 1e4 * (best_ask - best_bid) / max(mid, 1e-12)
        micro = microprice(bids, asks)
        microprice_drift_bps = 1e4 * (micro - mid) / max(mid, 1e-12)

        depth_top5 = _depth_sum(bids, asks, 5)
        depth_top10 = _depth_sum(bids, asks, 10)
        reference = top10 if n_levels >= 10 else (top5 if n_levels >= 5 else top1)
        agreement, trap = _agreement_trap(top1, reference)

        self._last_snapshot = QueueImbalanceSnapshot(
            top1=round(top1, 6),
            top5=round(top5, 6) if n_levels >= 5 else None,
            top10=round(top10, 6) if n_levels >= 10 else None,
            weighted_imbalance=round(weighted_imbalance, 6),
            spread_bps=round(spread_bps, 4),
            microprice=round(micro, 6),
            microprice_drift_bps=round(microprice_drift_bps, 4),
            depth_top5=round(depth_top5, 6),
            depth_top10=round(depth_top10, 6),
            book_agreement_score=round(agreement, 4),
            book_trap_score=round(trap, 4),
            levels_used=n_levels,
        )
        return self._last_snapshot

    @property
    def snapshot(self) -> QueueImbalanceSnapshot:
        return self._last_snapshot

    def _empty_snapshot(self) -> QueueImbalanceSnapshot:
        return QueueImbalanceSnapshot(
            top1=None,
            top5=None,
            top10=None,
            weighted_imbalance=None,
            spread_bps=None,
            microprice=None,
            microprice_drift_bps=None,
            depth_top5=None,
            depth_top10=None,
            book_agreement_score=0.0,
            book_trap_score=0.0,
            levels_used=0,
        )


def _imbalance_for_levels(
    bids: Sequence[tuple[float, float]],
    asks: Sequence[tuple[float, float]],
    levels: int,
) -> float:
    count = min(levels, len(bids), len(asks))
    if count <= 0:
        return 0.0
    bid_depth = sum(float(qty) for _, qty in bids[:count])
    ask_depth = sum(float(qty) for _, qty in asks[:count])
    denom = bid_depth + ask_depth
    return 0.0 if denom <= 0 else (bid_depth - ask_depth) / denom


def _depth_sum(
    bids: Sequence[tuple[float, float]],
    asks: Sequence[tuple[float, float]],
    levels: int,
) -> float:
    count = min(levels, len(bids), len(asks))
    return sum(float(qty) for _, qty in bids[:count]) + sum(float(qty) for _, qty in asks[:count])


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    if not values:
        return 0.0
    denom = sum(weights)
    if denom <= 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights, strict=False)) / denom


def _agreement_trap(left: float, right: float) -> tuple[float, float]:
    left_sign = 1.0 if left > 0 else (-1.0 if left < 0 else 0.0)
    right_sign = 1.0 if right > 0 else (-1.0 if right < 0 else 0.0)
    agreement = left_sign * right_sign
    trap = abs(left - right) if left_sign != right_sign else 0.0
    return agreement, min(trap, 2.0)
