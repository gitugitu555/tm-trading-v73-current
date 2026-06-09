"""Volume-Synchronized Probability of Informed Trading (VPIN) — V8.3 Engine.

Upgrade from simplified trade-window approximation to a stateful volume-bucket
VPIN with fast/slow spread, slope, session percentile, and toxicity state.

References:
  Easley, Lopez de Prado, O'Hara (2012) "Flow Toxicity and Liquidity in a
  High-frequency World", Review of Financial Studies.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.types import SignedTrade


class ToxicityState(Enum):
    BENIGN = "BENIGN"
    RISING_TOXICITY = "RISING_TOXICITY"
    HIGH_TOXICITY = "HIGH_TOXICITY"
    FALLING_TOXICITY = "FALLING_TOXICITY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class VPINSnapshot:
    """Complete VPIN diagnostic snapshot for one bar/update."""
    vpin_level: float
    """Current VPIN (volume-bucket imbalance probability)."""
    vpin_fast: float
    """Short-window VPIN average."""
    vpin_slow: float
    """Long-window VPIN baseline."""
    vpin_slope: float
    """Rate of VPIN change (fast - prev_fast)."""
    vpin_fast_minus_slow: float
    """Spread between fast and slow VPIN."""
    vpin_zscore: Optional[float]
    """Z-score of current VPIN relative to rolling window."""
    vpin_rolling_mean: Optional[float]
    """Rolling mean used for z-score."""
    vpin_rolling_std: Optional[float]
    """Rolling std used for z-score."""
    toxicity_state: ToxicityState
    """Classified toxicity regime."""
    toxicity_score: float
    """Normalised 0-1 composite score (higher = more toxic)."""
    buckets_filled: int
    """Number of volume buckets completed so far."""


class VPINEngine:
    """Volume-bucket VPIN engine with fast/slow/slope/zscore/state.

    Algorithm:
      1. Accumulate trades into equal-volume buckets of size `bucket_volume`.
      2. Per bucket, compute |buy_vol - sell_vol| / bucket_volume = VPIN_bucket.
      3. Maintain a rolling window of `n_buckets` buckets for the VPIN estimate.
      4. Compute fast average over `fast_window` buckets.
      5. Compute slow average over `slow_window` buckets.
      6. Track rolling z-score over `zscore_window` VPIN observations.
      7. Classify toxicity state from z-score + slope.
    """

    def __init__(
        self,
        window: int | None = None,
        bucket_volume: float = 300.0,
        n_buckets: int = 50,
        fast_window: int = 10,
        slow_window: int = 50,
        zscore_window: int = 200,
        high_zscore_threshold: float = 2.0,
    ) -> None:
        if window is not None and window <= 0:
            raise ValueError("window must be positive")
        if bucket_volume <= 0:
            raise ValueError("bucket_volume must be positive")
        if fast_window >= slow_window:
            raise ValueError("fast_window must be less than slow_window")
        self.window = window
        self.bucket_volume = bucket_volume
        self.n_buckets = n_buckets
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.zscore_window = zscore_window
        self.high_zscore_threshold = high_zscore_threshold

        # Legacy compatibility path used by older callers and tests.
        self._legacy_flows: deque[tuple[float, float]] | None = (
            deque(maxlen=window) if window is not None else None
        )

        # Current bucket accumulation
        self._bucket_buy: float = 0.0
        self._bucket_sell: float = 0.0
        self._bucket_total: float = 0.0

        # Rolling VPIN bucket history (FIFO)
        self._buckets: deque[float] = deque(maxlen=slow_window)
        # Fast and slow sums for incremental averaging
        self._fast_buckets: deque[float] = deque(maxlen=fast_window)
        self._slow_buckets: deque[float] = deque(maxlen=slow_window)

        # Z-score rolling history
        self._zscore_history: deque[float] = deque(maxlen=zscore_window)

        # Previous fast VPIN for slope
        self._prev_fast: float = 0.0

        # Snapshot state
        self._last_snapshot: VPINSnapshot = VPINSnapshot(
            vpin_level=0.0,
            vpin_fast=0.0,
            vpin_slow=0.0,
            vpin_slope=0.0,
            vpin_fast_minus_slow=0.0,
            vpin_zscore=None,
            vpin_rolling_mean=None,
            vpin_rolling_std=None,
            toxicity_state=ToxicityState.UNKNOWN,
            toxicity_score=0.0,
            buckets_filled=0,
        )

    def update(self, trade: SignedTrade) -> float:
        """Process one signed trade and return the current VPIN level.

        The detailed diagnostics stay available via ``snapshot`` and
        ``update_volume_bar``.
        """
        if self._legacy_flows is not None:
            if trade.side == "BUY":
                buy, sell = trade.size_base, 0.0
            elif trade.side == "SELL":
                buy, sell = 0.0, trade.size_base
            else:
                buy = sell = trade.size_base * 0.5
            self._legacy_flows.append((buy, sell))
            total_buy = sum(item[0] for item in self._legacy_flows)
            total_sell = sum(item[1] for item in self._legacy_flows)
            total = total_buy + total_sell
            value = 0.0 if total == 0 else abs(total_buy - total_sell) / total
            self._last_snapshot = VPINSnapshot(
                vpin_level=round(value, 6),
                vpin_fast=round(value, 6),
                vpin_slow=round(value, 6),
                vpin_slope=0.0,
                vpin_fast_minus_slow=0.0,
                vpin_zscore=None,
                vpin_rolling_mean=None,
                vpin_rolling_std=None,
                toxicity_state=ToxicityState.UNKNOWN,
                toxicity_score=0.0,
                buckets_filled=len(self._legacy_flows),
            )
            return value

        if trade.side == "BUY":
            buy, sell = trade.size_base, 0.0
        elif trade.side == "SELL":
            buy, sell = 0.0, trade.size_base
        else:
            buy = sell = trade.size_base * 0.5

        remaining = trade.size_base
        while remaining > 0:
            space = self.bucket_volume - self._bucket_total
            fill = min(remaining, space)
            frac = fill / trade.size_base if trade.size_base > 0 else 0.0
            self._bucket_buy += buy * frac
            self._bucket_sell += sell * frac
            self._bucket_total += fill
            remaining -= fill

            if self._bucket_total >= self.bucket_volume:
                # Bucket complete — compute VPIN for this bucket
                total = self._bucket_buy + self._bucket_sell
                bucket_vpin = abs(self._bucket_buy - self._bucket_sell) / max(total, 1e-12)
                self._buckets.append(bucket_vpin)
                self._fast_buckets.append(bucket_vpin)
                self._slow_buckets.append(bucket_vpin)
                # Compute fast and slow averages
                vpin_fast = _mean(self._fast_buckets)
                vpin_slow = _mean(self._slow_buckets)
                vpin_level = vpin_slow  # canonical VPIN = slow-window estimate

                # Reset bucket
                self._bucket_buy = 0.0
                self._bucket_sell = 0.0
                self._bucket_total = 0.0

                self._zscore_history.append(vpin_level)

                slope = vpin_fast - self._prev_fast
                spread = vpin_fast - vpin_slow
                self._prev_fast = vpin_fast

                # Z-score
                zscore: Optional[float] = None
                roll_mean: Optional[float] = None
                roll_std: Optional[float] = None
                if len(self._zscore_history) >= 10:
                    roll_mean = _mean(self._zscore_history)
                    roll_std = _std(self._zscore_history, roll_mean)
                    zscore = (vpin_level - roll_mean) / max(roll_std, 1e-12)

                state = self._classify(zscore, slope, vpin_fast, vpin_slow)
                score = self._toxicity_score(zscore, slope, spread)

                self._last_snapshot = VPINSnapshot(
                    vpin_level=round(vpin_level, 6),
                    vpin_fast=round(vpin_fast, 6),
                    vpin_slow=round(vpin_slow, 6),
                    vpin_slope=round(slope, 6),
                    vpin_fast_minus_slow=round(spread, 6),
                    vpin_zscore=round(zscore, 4) if zscore is not None else None,
                    vpin_rolling_mean=round(roll_mean, 6) if roll_mean is not None else None,
                    vpin_rolling_std=round(roll_std, 6) if roll_std is not None else None,
                    toxicity_state=state,
                    toxicity_score=round(score, 4),
                    buckets_filled=len(self._buckets),
                )

        return self._last_snapshot.vpin_level

    def update_volume_bar(
        self,
        buy_volume: float,
        sell_volume: float,
    ) -> VPINSnapshot:
        """Lighter integration point: update directly from a completed volume bar.

        Use this when you have pre-computed buy/sell volumes from the VolumeBar
        dataclass instead of raw trade ticks.
        """
        total = buy_volume + sell_volume
        bucket_vpin = abs(buy_volume - sell_volume) / max(total, 1e-12)

        self._buckets.append(bucket_vpin)
        self._fast_buckets.append(bucket_vpin)
        self._slow_buckets.append(bucket_vpin)

        vpin_fast = _mean(self._fast_buckets)
        vpin_slow = _mean(self._slow_buckets)
        vpin_level = vpin_slow

        self._zscore_history.append(vpin_level)

        slope = vpin_fast - self._prev_fast
        spread = vpin_fast - vpin_slow
        self._prev_fast = vpin_fast

        zscore: Optional[float] = None
        roll_mean: Optional[float] = None
        roll_std: Optional[float] = None
        if len(self._zscore_history) >= 10:
            roll_mean = _mean(self._zscore_history)
            roll_std = _std(self._zscore_history, roll_mean)
            zscore = (vpin_level - roll_mean) / max(roll_std, 1e-12)

        state = self._classify(zscore, slope, vpin_fast, vpin_slow)
        score = self._toxicity_score(zscore, slope, spread)

        self._last_snapshot = VPINSnapshot(
            vpin_level=round(vpin_level, 6),
            vpin_fast=round(vpin_fast, 6),
            vpin_slow=round(vpin_slow, 6),
            vpin_slope=round(slope, 6),
            vpin_fast_minus_slow=round(spread, 6),
            vpin_zscore=round(zscore, 4) if zscore is not None else None,
            vpin_rolling_mean=round(roll_mean, 6) if roll_mean is not None else None,
            vpin_rolling_std=round(roll_std, 6) if roll_std is not None else None,
            toxicity_state=state,
            toxicity_score=round(score, 4),
            buckets_filled=len(self._buckets),
        )
        return self._last_snapshot

    def _classify(
        self,
        zscore: Optional[float],
        slope: float,
        vpin_fast: float,
        vpin_slow: float,
    ) -> ToxicityState:
        if zscore is None:
            return ToxicityState.UNKNOWN
        if zscore >= self.high_zscore_threshold and slope > 0:
            return ToxicityState.HIGH_TOXICITY
        if slope > 0 and vpin_fast > vpin_slow:
            return ToxicityState.RISING_TOXICITY
        if slope < 0 and vpin_fast < vpin_slow:
            return ToxicityState.FALLING_TOXICITY
        return ToxicityState.BENIGN

    def _toxicity_score(self, zscore: Optional[float], slope: float, spread: float) -> float:
        """Composite 0-1 toxicity score from z-score, slope, and fast/slow spread."""
        if zscore is None:
            return 0.0
        # Normalise z-score contribution (cap at ±3 sigma)
        z_contrib = min(1.0, max(0.0, zscore / 3.0))
        # Slope contribution (normalise to ±0.1 typical range)
        s_contrib = min(1.0, max(0.0, slope / 0.1))
        # Spread contribution (normalise to ±0.2 typical range)
        sp_contrib = min(1.0, max(0.0, spread / 0.2))
        return round(0.5 * z_contrib + 0.3 * s_contrib + 0.2 * sp_contrib, 4)

    @property
    def snapshot(self) -> VPINSnapshot:
        """Return the most recent VPIN snapshot without processing new data."""
        return self._last_snapshot

    def reset(self) -> None:
        """Reset all state — call between sessions or symbols."""
        if self._legacy_flows is not None:
            self._legacy_flows.clear()
        self._bucket_buy = 0.0
        self._bucket_sell = 0.0
        self._bucket_total = 0.0
        self._buckets.clear()
        self._fast_buckets.clear()
        self._slow_buckets.clear()
        self._zscore_history.clear()
        self._prev_fast = 0.0
        self._last_snapshot = VPINSnapshot(
            vpin_level=0.0,
            vpin_fast=0.0,
            vpin_slow=0.0,
            vpin_slope=0.0,
            vpin_fast_minus_slow=0.0,
            vpin_zscore=None,
            vpin_rolling_mean=None,
            vpin_rolling_std=None,
            toxicity_state=ToxicityState.UNKNOWN,
            toxicity_score=0.0,
            buckets_filled=0,
        )


def _mean(d: deque) -> float:
    if not d:
        return 0.0
    return sum(d) / len(d)


def _std(d: deque, mean: float) -> float:
    if len(d) < 2:
        return 0.0
    return (sum((x - mean) ** 2 for x in d) / (len(d) - 1)) ** 0.5
