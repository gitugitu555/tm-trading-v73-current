"""Shared volume-bar CVD divergence signal (diagnostic ≡ backtest)."""

from __future__ import annotations

from collections.abc import Sequence

from prime.volume_bars import VolumeBar


def htf_change_at(bars: Sequence[VolumeBar], current_ts: int, current_cvd: float) -> float:
    hour_ns = 3_600_000_000_000
    target_ts = current_ts - hour_ns
    for bar in bars:
        if bar.end_ts_ns >= target_ts:
            return current_cvd - bar.cumulative_delta
    return 0.0


def htf_flat_abs_threshold(
    htf_abs_changes: Sequence[float],
    *,
    quantile: float = 0.25,
    min_samples: int = 10,
) -> float:
    if len(htf_abs_changes) < min_samples:
        return 0.0
    sorted_values = sorted(htf_abs_changes)
    idx = int((len(sorted_values) - 1) * quantile)
    return sorted_values[idx]


def volume_bar_cvd_signal(
    bars: Sequence[VolumeBar],
    *,
    lookback_bars: int,
    htf_change: float,
    flat_abs: float,
    timestamp_ns: int,
    price: float,
    invert_signal_side: bool = False,
) -> dict | None:
    """D4-style fade: divergence on bar close + 1h flat-CVD HTF filter."""
    if len(bars) <= lookback_bars:
        return None

    prior_bars = list(bars)[-lookback_bars - 1 : -1]
    current_bar = bars[-1]

    prior_high = max(b.high for b in prior_bars)
    prior_low = min(b.low for b in prior_bars)
    prior_cvd_high = max(b.cumulative_delta for b in prior_bars)
    prior_cvd_low = min(b.cumulative_delta for b in prior_bars)

    bearish = current_bar.high >= prior_high and current_bar.cumulative_delta < prior_cvd_high
    bullish = current_bar.low <= prior_low and current_bar.cumulative_delta > prior_cvd_low

    if bearish == bullish:
        return None

    side = -1 if bearish else +1
    if side == -1:
        allowed = htf_change <= flat_abs
    else:
        allowed = htf_change >= -flat_abs
    if not allowed:
        return None

    strength = min(1.0, abs(current_bar.cumulative_delta) / 100.0)
    if invert_signal_side:
        side = -side

    return {
        "id": f"VOLBARCVD_{timestamp_ns}_{side}",
        "side": side,
        "strength": round(strength, 6),
        "price": price,
    }