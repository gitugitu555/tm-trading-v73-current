"""Multi-Level Order-Flow Imbalance (MLOFI) — V8.3 Engine.

Upgrade from a single weighted scalar to a true multi-level vector
with distance-decay aggregation, sliding-window z-score normalisation,
near/far book agreement, and book-trap detection.

References:
  Cont, Kukanov, Stoikov (2010) "The Price Impact of Order Book Events".
  Xu & Gould (2019) "Multi-Level Order Flow Imbalance in a Limit Order Book".
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional, Sequence

# Distance-decay weights for L1..L5 (L1 is nearest to mid, highest weight)
_DEFAULT_WEIGHTS = [1.00, 0.80, 0.65, 0.50, 0.40]


@dataclass(frozen=True)
class MLOFISnapshot:
    """Complete MLOFI diagnostic snapshot."""
    mlofi_l1: Optional[float]
    """Level-1 (best bid/ask) imbalance: [-1, +1]."""
    mlofi_l3: Optional[float]
    """Mean imbalance across L1-L3."""
    mlofi_l5: Optional[float]
    """Mean imbalance across L1-L5."""
    mlofi_l10: Optional[float]
    """Mean imbalance across L1-L10 (None if < 10 levels available)."""
    near_book_imbalance: Optional[float]
    """Weighted aggregate of near levels (L1-L3)."""
    far_book_imbalance: Optional[float]
    """Weighted aggregate of far levels (L4-L5+)."""
    mlofi_weighted_aggregate: Optional[float]
    """Distance-decay weighted aggregate of all available levels."""
    mlofi_zscore: Optional[float]
    """Z-score of weighted aggregate relative to rolling window."""
    mlofi_window_mean: Optional[float]
    """Rolling mean of weighted aggregate used for z-score."""
    mlofi_window_std: Optional[float]
    """Rolling std of weighted aggregate used for z-score."""
    book_agreement_score: float
    """Agreement between near and far pressure: +1 agree, -1 disagree, 0 neutral."""
    book_trap_score: float
    """Divergence score: positive = near vs far disagree (potential trap/spoof)."""
    levels_used: int
    """Number of book levels actually used in calculation."""
    aggregation_method: str
    """Aggregation method identifier for manifest logging."""


class MLOFIEngine:
    """Multi-level order-book imbalance engine.

    Accepts bid/ask depth snapshots and computes a true MLOFI vector
    with sliding-window z-score normalisation and near/far book diagnostics.

    Parameters
    ----------
    max_levels : int
        Maximum book levels to read per side (default: 10).
    zscore_window : int
        Lookback window for rolling mean/std normalisation.
    near_levels : int
        Number of levels considered "near" for near/far split (default: 3).
    weights : list[float] or None
        Per-level distance-decay weights (length <= max_levels).
        Defaults to [1.0, 0.8, 0.65, 0.5, 0.4, 0.33, 0.27, 0.22, 0.18, 0.15].
    """

    def __init__(
        self,
        max_levels: int = 10,
        zscore_window: int = 200,
        near_levels: int = 3,
        weights: Optional[list[float]] = None,
    ) -> None:
        if max_levels < 1:
            raise ValueError("max_levels must be >= 1")
        self.max_levels = max_levels
        self.zscore_window = zscore_window
        self.near_levels = min(near_levels, max_levels)

        # Build weight vector padded/truncated to max_levels
        base = weights or [1.00, 0.80, 0.65, 0.50, 0.40, 0.33, 0.27, 0.22, 0.18, 0.15]
        if len(base) < max_levels:
            # Extend with decaying weights
            last = base[-1] if base else 0.1
            base = base + [max(0.05, last * 0.8 ** i) for i in range(1, max_levels - len(base) + 1)]
        self._weights: list[float] = base[:max_levels]

        # Rolling history for z-score normalisation
        self._history: deque[float] = deque(maxlen=zscore_window)

    def update(
        self,
        bids: Sequence[tuple[float, float]],
        asks: Sequence[tuple[float, float]],
    ) -> MLOFISnapshot:
        """Compute MLOFI from an order-book depth snapshot.

        Parameters
        ----------
        bids : sequence of (price, size) sorted best-to-worst (descending price).
        asks : sequence of (price, size) sorted best-to-worst (ascending price).

        Returns
        -------
        MLOFISnapshot with all computed fields.
        """
        if not bids or not asks:
            return self._empty_snapshot()

        n_levels = min(len(bids), len(asks), self.max_levels)
        if n_levels == 0:
            return self._empty_snapshot()

        # Compute per-level imbalance
        imbalances: list[float] = []
        for i in range(n_levels):
            bid_sz = bids[i][1]
            ask_sz = asks[i][1]
            denom = bid_sz + ask_sz
            imb = (bid_sz - ask_sz) / max(denom, 1e-12)
            imbalances.append(imb)

        # Aggregate views
        mlofi_l1 = imbalances[0]
        mlofi_l3 = _mean_n(imbalances, 3) if n_levels >= 3 else None
        mlofi_l5 = _mean_n(imbalances, 5) if n_levels >= 5 else None
        mlofi_l10 = _mean_n(imbalances, 10) if n_levels >= 10 else None

        # Near/far split
        near_n = min(self.near_levels, n_levels)
        near_imb = _weighted_mean(imbalances[:near_n], self._weights[:near_n])
        far_n = n_levels - near_n
        if far_n > 0:
            far_imb = _weighted_mean(
                imbalances[near_n:n_levels],
                self._weights[near_n:n_levels],
            )
        else:
            far_imb = None

        # Weighted aggregate across all levels
        weighted_agg = _weighted_mean(imbalances, self._weights[:n_levels])

        # Update z-score history
        self._history.append(weighted_agg)

        zscore: Optional[float] = None
        roll_mean: Optional[float] = None
        roll_std: Optional[float] = None
        if len(self._history) >= 10:
            roll_mean = sum(self._history) / len(self._history)
            roll_std = _std_deque(self._history, roll_mean)
            zscore = (weighted_agg - roll_mean) / max(roll_std, 1e-12)

        # Agreement and trap scores
        agreement, trap = self._agreement_trap(near_imb, far_imb)

        return MLOFISnapshot(
            mlofi_l1=round(mlofi_l1, 6),
            mlofi_l3=round(mlofi_l3, 6) if mlofi_l3 is not None else None,
            mlofi_l5=round(mlofi_l5, 6) if mlofi_l5 is not None else None,
            mlofi_l10=round(mlofi_l10, 6) if mlofi_l10 is not None else None,
            near_book_imbalance=round(near_imb, 6),
            far_book_imbalance=round(far_imb, 6) if far_imb is not None else None,
            mlofi_weighted_aggregate=round(weighted_agg, 6),
            mlofi_zscore=round(zscore, 4) if zscore is not None else None,
            mlofi_window_mean=round(roll_mean, 6) if roll_mean is not None else None,
            mlofi_window_std=round(roll_std, 6) if roll_std is not None else None,
            book_agreement_score=round(agreement, 4),
            book_trap_score=round(trap, 4),
            levels_used=n_levels,
            aggregation_method="distance_decay",
        )

    def update_from_bar(
        self,
        buy_volume: float,
        sell_volume: float,
    ) -> MLOFISnapshot:
        """Simplified update from volume bar buy/sell split (L1-only proxy).

        Used when full order-book depth is unavailable. Produces a scalar
        imbalance only; L3/L5/L10 and near/far fields remain None.
        """
        total = buy_volume + sell_volume
        imb = (buy_volume - sell_volume) / max(total, 1e-12)
        self._history.append(imb)

        zscore: Optional[float] = None
        roll_mean: Optional[float] = None
        roll_std: Optional[float] = None
        if len(self._history) >= 10:
            roll_mean = sum(self._history) / len(self._history)
            roll_std = _std_deque(self._history, roll_mean)
            zscore = (imb - roll_mean) / max(roll_std, 1e-12)

        return MLOFISnapshot(
            mlofi_l1=round(imb, 6),
            mlofi_l3=None,
            mlofi_l5=None,
            mlofi_l10=None,
            near_book_imbalance=round(imb, 6),
            far_book_imbalance=None,
            mlofi_weighted_aggregate=round(imb, 6),
            mlofi_zscore=round(zscore, 4) if zscore is not None else None,
            mlofi_window_mean=round(roll_mean, 6) if roll_mean is not None else None,
            mlofi_window_std=round(roll_std, 6) if roll_std is not None else None,
            book_agreement_score=0.0,
            book_trap_score=0.0,
            levels_used=1,
            aggregation_method="bar_proxy",
        )

    @staticmethod
    def _agreement_trap(
        near_imb: float,
        far_imb: Optional[float],
    ) -> tuple[float, float]:
        """Compute book agreement and trap scores.

        agreement_score: +1 if near and far agree direction, -1 if disagree.
        trap_score: magnitude of near/far divergence (potential spoof indicator).
        """
        if far_imb is None:
            return 0.0, 0.0
        near_sign = 1.0 if near_imb > 0 else (-1.0 if near_imb < 0 else 0.0)
        far_sign = 1.0 if far_imb > 0 else (-1.0 if far_imb < 0 else 0.0)
        agreement = near_sign * far_sign  # +1, -1, or 0
        trap = abs(near_imb - far_imb)    # larger = more divergence
        return agreement, min(trap, 2.0)  # cap trap at 2.0

    def _empty_snapshot(self) -> MLOFISnapshot:
        return MLOFISnapshot(
            mlofi_l1=None,
            mlofi_l3=None,
            mlofi_l5=None,
            mlofi_l10=None,
            near_book_imbalance=None,
            far_book_imbalance=None,
            mlofi_weighted_aggregate=None,
            mlofi_zscore=None,
            mlofi_window_mean=None,
            mlofi_window_std=None,
            book_agreement_score=0.0,
            book_trap_score=0.0,
            levels_used=0,
            aggregation_method="distance_decay",
        )

    def reset(self) -> None:
        """Clear rolling history — call between sessions or symbols."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Stand-alone convenience function (drop-in upgrade for l2_imbalance.py usage)
# ---------------------------------------------------------------------------

class OrderBookImbalanceEngine:
    """Backward-compatible single-snapshot L2 imbalance (wraps MLOFIEngine L1).

    Kept so existing imports of OrderBookImbalanceEngine do not break.
    For new code use MLOFIEngine.update() directly.
    """

    def __init__(self) -> None:
        self._engine = MLOFIEngine(max_levels=5, zscore_window=200)

    def update(
        self,
        bids: list[tuple[float, float]] | tuple[tuple[float, float], ...],
        asks: list[tuple[float, float]] | tuple[tuple[float, float], ...],
    ) -> float:
        snap = self._engine.update(list(bids), list(asks))
        return snap.mlofi_weighted_aggregate or 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mean_n(values: list[float], n: int) -> float:
    usable = values[:n]
    return sum(usable) / len(usable) if usable else 0.0


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    if not values:
        return 0.0
    total_w = sum(weights[:len(values)])
    if total_w == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_w


def _std_deque(d: deque, mean: float) -> float:
    if len(d) < 2:
        return 0.0
    return (sum((x - mean) ** 2 for x in d) / (len(d) - 1)) ** 0.5
