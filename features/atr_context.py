"""ATR, volatility, and trend-stack context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev
from typing import Sequence


@dataclass(frozen=True)
class ATRContextSnapshot:
    atr_current: float
    atr_percentile: float
    atr_used_pct: float
    session_range: float
    range_remaining: float
    realized_volatility: float
    trend_stack: str
    trend_alignment: float
    can_trade_more: bool
    bar_count: int


class ATRContextEngine:
    """Derive ATR exhaustion and trend-stack context from bars."""

    def __init__(
        self,
        *,
        atr_period: int = 14,
        exhaustion_threshold_pct: float = 75.0,
    ) -> None:
        if atr_period <= 0:
            raise ValueError("atr_period must be positive")
        self.atr_period = atr_period
        self.exhaustion_threshold_pct = exhaustion_threshold_pct
        self._last_snapshot = self._empty_snapshot()

    def update(
        self,
        bars: Sequence[object],
        *,
        current_price: float | None = None,
    ) -> ATRContextSnapshot:
        if not bars:
            self._last_snapshot = self._empty_snapshot()
            return self._last_snapshot

        highs: list[float] = []
        lows: list[float] = []
        closes: list[float] = []
        true_ranges: list[float] = []

        prev_close: float | None = None
        for bar in bars:
            low, high, close = _read_bar(bar)
            highs.append(high)
            lows.append(low)
            closes.append(close)
            if prev_close is not None:
                true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
            prev_close = close

        atr_series = _wilder_series(true_ranges, self.atr_period)
        atr_current = atr_series[-1] if atr_series else 0.0
        atr_percentile = _percentile_rank(atr_series, atr_current) if atr_series else 0.0
        session_range = max(highs) - min(lows)
        atr_used_pct = 100.0 * session_range / max(atr_current, 1e-12) if atr_current > 0 else 0.0
        range_remaining = max(atr_current - session_range, 0.0)
        realized_volatility = _realized_volatility(closes)
        trend_stack, trend_alignment = _trend_stack(closes)
        can_trade_more = atr_used_pct < self.exhaustion_threshold_pct

        self._last_snapshot = ATRContextSnapshot(
            atr_current=round(atr_current, 6),
            atr_percentile=round(atr_percentile, 4),
            atr_used_pct=round(atr_used_pct, 4),
            session_range=round(session_range, 6),
            range_remaining=round(range_remaining, 6),
            realized_volatility=round(realized_volatility, 6),
            trend_stack=trend_stack,
            trend_alignment=round(trend_alignment, 4),
            can_trade_more=can_trade_more,
            bar_count=len(bars),
        )
        return self._last_snapshot

    @property
    def snapshot(self) -> ATRContextSnapshot:
        return self._last_snapshot

    def _empty_snapshot(self) -> ATRContextSnapshot:
        return ATRContextSnapshot(
            atr_current=0.0,
            atr_percentile=0.0,
            atr_used_pct=0.0,
            session_range=0.0,
            range_remaining=0.0,
            realized_volatility=0.0,
            trend_stack="UNKNOWN",
            trend_alignment=0.0,
            can_trade_more=True,
            bar_count=0,
        )


def _read_bar(bar: object) -> tuple[float, float, float]:
    if hasattr(bar, "low") and hasattr(bar, "high") and hasattr(bar, "close"):
        return float(bar.low), float(bar.high), float(bar.close)
    if isinstance(bar, Sequence) and len(bar) >= 4:
        low = float(bar[2])
        high = float(bar[1])
        close = float(bar[3])
        return low, high, close
    raise TypeError("bar must expose low/high/close fields")


def _wilder_series(true_ranges: list[float], period: int) -> list[float]:
    if not true_ranges:
        return []
    if len(true_ranges) < period:
        return [sum(true_ranges) / len(true_ranges)]
    atr = sum(true_ranges[:period]) / period
    series = [atr]
    for tr in true_ranges[period:]:
        atr = ((period - 1) * atr + tr) / period
        series.append(atr)
    return series


def _percentile_rank(values: list[float], target: float) -> float:
    if not values:
        return 0.0
    below = sum(1 for value in values if value <= target)
    return below / len(values)


def _realized_volatility(closes: list[float]) -> float:
    if len(closes) < 3:
        return 0.0
    returns = []
    for prev, cur in zip(closes, closes[1:], strict=False):
        if prev > 0:
            returns.append((cur - prev) / prev)
    return pstdev(returns) if len(returns) >= 2 else 0.0


def _trend_stack(closes: list[float]) -> tuple[str, float]:
    if len(closes) < 10:
        return "UNKNOWN", 0.0

    fast = _sma(closes, 20)
    mid = _sma(closes, 50)
    slow = _sma(closes, 100)
    if fast > mid > slow:
        return "BULL_STACK", 1.0
    if fast < mid < slow:
        return "BEAR_STACK", -1.0
    if fast > mid and closes[-1] > fast:
        return "BULLISH_MIXED", 0.5
    if fast < mid and closes[-1] < fast:
        return "BEARISH_MIXED", -0.5
    return "MIXED", 0.0


def _sma(values: list[float], window: int) -> float:
    if not values:
        return 0.0
    window = min(window, len(values))
    if window <= 0:
        return 0.0
    return sum(values[-window:]) / window
