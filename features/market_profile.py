"""Market profile and ATR context helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class MarketProfileSnapshot:
    poc: float | None
    vah: float | None
    val: float | None
    lvn_zones: tuple[float, ...]
    profile_type: str
    current_value_context: str
    atr_current: float
    session_range: float
    atr_used_pct: float
    range_remaining: float
    can_trade_more: bool
    session_tier: str
    value_area_width: float
    profile_target_poc: float | None
    profile_target_vah: float | None
    profile_target_val: float | None
    profile_target_lvn: float | None


class MarketProfileEngine:
    """Build a coarse market profile from completed bars.

    The engine is intentionally simple and deterministic: it distributes each
    bar's volume across the tick grid between low and high, then derives POC,
    value area, LVN zones, and ATR exhaustion context from that histogram.
    """

    def __init__(
        self,
        *,
        tick_size: float = 0.5,
        value_area_pct: float = 0.70,
        atr_period: int = 14,
        exhaustion_threshold_pct: float = 75.0,
    ) -> None:
        if tick_size <= 0:
            raise ValueError("tick_size must be positive")
        if not 0.0 < value_area_pct < 1.0:
            raise ValueError("value_area_pct must be between 0 and 1")
        if atr_period <= 0:
            raise ValueError("atr_period must be positive")
        self.tick_size = tick_size
        self.value_area_pct = value_area_pct
        self.atr_period = atr_period
        self.exhaustion_threshold_pct = exhaustion_threshold_pct
        self._last_snapshot = MarketProfileSnapshot(
            poc=None,
            vah=None,
            val=None,
            lvn_zones=(),
            profile_type="UNKNOWN",
            current_value_context="UNKNOWN",
            atr_current=0.0,
            session_range=0.0,
            atr_used_pct=0.0,
            range_remaining=0.0,
            can_trade_more=True,
            session_tier="SKIP",
            value_area_width=0.0,
            profile_target_poc=None,
            profile_target_vah=None,
            profile_target_val=None,
            profile_target_lvn=None,
        )

    def update(self, bars: Sequence[object], *, current_price: float | None = None) -> MarketProfileSnapshot:
        """Compute a fresh profile snapshot from a sequence of bars."""
        if not bars:
            self._last_snapshot = self._empty()
            return self._last_snapshot

        histogram: dict[float, float] = defaultdict(float)
        highs: list[float] = []
        lows: list[float] = []
        closes: list[float] = []
        for bar in bars:
            low, high, close, volume = _read_bar(bar)
            lows.append(low)
            highs.append(high)
            closes.append(close)
            _fill_histogram(histogram, low, high, volume, self.tick_size)

        if not histogram:
            self._last_snapshot = self._empty()
            return self._last_snapshot

        total_volume = sum(histogram.values())
        ordered = sorted(histogram.items())
        poc, poc_volume = max(ordered, key=lambda item: (item[1], -abs(item[0] - closes[-1])))
        val, vah = _expand_value_area(ordered, poc, total_volume, self.value_area_pct)
        lvn_zones = _detect_lvn_zones(ordered)

        atr_current = _wilder_atr(bars, self.atr_period)
        session_range = max(highs) - min(lows)
        atr_used_pct = 100.0 * session_range / max(atr_current, 1e-12) if atr_current > 0 else 0.0
        range_remaining = max(atr_current - session_range, 0.0)
        can_trade_more = atr_used_pct < self.exhaustion_threshold_pct
        current_px = current_price if current_price is not None else closes[-1]
        current_value_context = _value_context(current_px, val, vah)
        profile_type = _profile_type(ordered, poc, val, vah)
        session_tier = _session_tier(atr_used_pct, current_value_context)
        target_lvn = _nearest_lvn(current_px, lvn_zones)

        self._last_snapshot = MarketProfileSnapshot(
            poc=round(poc, 6),
            vah=round(vah, 6),
            val=round(val, 6),
            lvn_zones=tuple(round(x, 6) for x in lvn_zones),
            profile_type=profile_type,
            current_value_context=current_value_context,
            atr_current=round(atr_current, 6),
            session_range=round(session_range, 6),
            atr_used_pct=round(atr_used_pct, 4),
            range_remaining=round(range_remaining, 6),
            can_trade_more=can_trade_more,
            session_tier=session_tier,
            value_area_width=round(vah - val, 6),
            profile_target_poc=_target_anchor(current_value_context, poc, vah, val, target_lvn)[0],
            profile_target_vah=_target_anchor(current_value_context, poc, vah, val, target_lvn)[1],
            profile_target_val=_target_anchor(current_value_context, poc, vah, val, target_lvn)[2],
            profile_target_lvn=target_lvn,
        )
        return self._last_snapshot

    @property
    def snapshot(self) -> MarketProfileSnapshot:
        return self._last_snapshot

    def _empty(self) -> MarketProfileSnapshot:
        return MarketProfileSnapshot(
            poc=None,
            vah=None,
            val=None,
            lvn_zones=(),
            profile_type="UNKNOWN",
            current_value_context="UNKNOWN",
            atr_current=0.0,
            session_range=0.0,
            atr_used_pct=0.0,
            range_remaining=0.0,
            can_trade_more=True,
            session_tier="SKIP",
            value_area_width=0.0,
            profile_target_poc=None,
            profile_target_vah=None,
            profile_target_val=None,
            profile_target_lvn=None,
        )


def _read_bar(bar: object) -> tuple[float, float, float, float]:
    if hasattr(bar, "low") and hasattr(bar, "high") and hasattr(bar, "close") and hasattr(bar, "volume"):
        return float(bar.low), float(bar.high), float(bar.close), float(bar.volume)
    if isinstance(bar, Sequence) and len(bar) >= 5:
        low = float(bar[2])
        high = float(bar[1])
        close = float(bar[3])
        volume = float(bar[4])
        return low, high, close, volume
    raise TypeError("bar must expose low/high/close/volume fields")


def _fill_histogram(histogram: dict[float, float], low: float, high: float, volume: float, tick_size: float) -> None:
    if volume <= 0:
        return
    if high < low:
        low, high = high, low
    first = round(low / tick_size) * tick_size
    last = round(high / tick_size) * tick_size
    levels = []
    level = first
    while level <= last + 1e-12:
        levels.append(round(level, 10))
        level += tick_size
    if not levels:
        levels = [round((low + high) / 2.0 / tick_size) * tick_size]
    share = volume / len(levels)
    for px in levels:
        histogram[px] += share


def _expand_value_area(
    ordered: list[tuple[float, float]],
    poc: float,
    total_volume: float,
    value_area_pct: float,
) -> tuple[float, float]:
    target = total_volume * value_area_pct
    prices = [px for px, _ in ordered]
    volumes = {px: vol for px, vol in ordered}
    idx = prices.index(poc)
    included = {poc}
    cumulative = volumes[poc]
    left = idx - 1
    right = idx + 1
    while cumulative < target and (left >= 0 or right < len(prices)):
        left_vol = volumes[prices[left]] if left >= 0 else -1.0
        right_vol = volumes[prices[right]] if right < len(prices) else -1.0
        if right_vol >= left_vol:
            included.add(prices[right])
            cumulative += right_vol
            right += 1
        else:
            included.add(prices[left])
            cumulative += left_vol
            left -= 1
    return min(included), max(included)


def _detect_lvn_zones(ordered: list[tuple[float, float]]) -> tuple[float, ...]:
    if len(ordered) < 3:
        return ()
    out: list[float] = []
    for i in range(1, len(ordered) - 1):
        px, vol = ordered[i]
        if vol <= ordered[i - 1][1] and vol <= ordered[i + 1][1]:
            out.append(px)
    return tuple(out)


def _wilder_atr(bars: Sequence[object], period: int) -> float:
    trs: list[float] = []
    prev_close: float | None = None
    for bar in bars:
        low, high, close, _ = _read_bar(bar)
        if prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = close
    if not trs:
        return 0.0
    if len(trs) <= period:
        return sum(trs) / len(trs)
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = ((period - 1) * atr + tr) / period
    return atr


def _value_context(price: float, val: float | None, vah: float | None) -> str:
    if val is None or vah is None:
        return "UNKNOWN"
    if price < val:
        return "BELOW_VALUE"
    if price > vah:
        return "ABOVE_VALUE"
    return "IN_VALUE"


def _profile_type(ordered: list[tuple[float, float]], poc: float, val: float, vah: float) -> str:
    if not ordered:
        return "UNKNOWN"
    total = sum(vol for _, vol in ordered)
    if total <= 0:
        return "UNKNOWN"
    left_mass = sum(vol for px, vol in ordered if px < poc)
    right_mass = sum(vol for px, vol in ordered if px > poc)
    tail_ratio = min(left_mass, right_mass) / max(total, 1e-12)
    width_ratio = (vah - val) / max(ordered[-1][0] - ordered[0][0], 1e-12)
    if tail_ratio > 0.18:
        return "DOUBLE_DISTRIBUTION"
    if width_ratio < 0.35 and left_mass < right_mass:
        return "P_SHAPE"
    if width_ratio < 0.35 and right_mass < left_mass:
        return "B_SHAPE"
    if width_ratio >= 0.60:
        return "TRENDING"
    return "BALANCED"


def _session_tier(atr_used_pct: float, context: str) -> str:
    if atr_used_pct >= 75.0:
        return "SKIP"
    if context == "IN_VALUE" and atr_used_pct < 60.0:
        return "A"
    if atr_used_pct < 70.0:
        return "B"
    return "S"


def _nearest_lvn(price: float, lvn_zones: tuple[float, ...]) -> float | None:
    if not lvn_zones:
        return None
    return min(lvn_zones, key=lambda px: abs(px - price))


def _target_anchor(
    context: str,
    poc: float,
    vah: float,
    val: float,
    lvn: float | None,
) -> tuple[float | None, float | None, float | None]:
    if context == "ABOVE_VALUE":
        return (poc, vah, val)
    if context == "BELOW_VALUE":
        return (poc, val, vah)
    if lvn is not None:
        return (poc, vah, val)
    return (poc, vah, val)
