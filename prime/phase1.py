"""V7.2 Phase 1 microstructure engines."""

from __future__ import annotations

from bisect import bisect_left, insort
from collections import deque
from typing import Optional

from prime.nautilus_compat import AggressorSide, Indicator, TradeTick, aggressor_name


class BaseEngine(Indicator):
    """Base template for deterministic Phase 1 trade-tick engines."""

    def __init__(self, params: list) -> None:
        super().__init__(params)
        self._tick_count = 0
        self._min_ticks = 1

    def handle_trade_tick(self, tick: TradeTick) -> None:
        self._tick_count += 1
        self._update(tick)
        if not self.initialized and self._tick_count >= self._min_ticks:
            self._set_initialized()

    def _update(self, tick: TradeTick) -> None:
        raise NotImplementedError

    @staticmethod
    def _signed_volume(tick: TradeTick) -> float:
        size = float(tick.size)
        side_name = aggressor_name(tick.aggressor_side)
        if tick.aggressor_side == AggressorSide.BUYER or side_name in {"BUYER", "BUY"}:
            return size
        if tick.aggressor_side == AggressorSide.SELLER or side_name in {"SELLER", "SELL"}:
            return -size
        return 0.0

    @staticmethod
    def _prune(buffer: list[tuple[int, float]], cutoff_ns: int) -> list[tuple[int, float]]:
        return [(ts, value) for ts, value in buffer if ts > cutoff_ns]


class CVDEngine(BaseEngine):
    """Cumulative Volume Delta. IC target >= 0.02; warm-up period: 1 tick."""

    WINDOW_1M = 60_000_000_000
    WINDOW_5M = 300_000_000_000
    WINDOW_15M = 900_000_000_000
    WINDOW_1H = 3_600_000_000_000
    WINDOW_4H = 14_400_000_000_000

    def __init__(self, divergence_threshold: float = 100.0, flat_threshold: float = 50.0) -> None:
        super().__init__([divergence_threshold, flat_threshold])
        self._div_thresh = divergence_threshold
        self._flat_thresh = flat_threshold
        self._cvd_session = 0.0
        self._buf_1m: deque[tuple[int, float]] = deque()
        self._buf_5m: deque[tuple[int, float]] = deque()
        self._buf_15m: deque[tuple[int, float]] = deque()
        self._buf_1h: deque[tuple[int, float]] = deque()
        self._buf_4h: deque[tuple[int, float]] = deque()
        self._price_open = 0.0
        self._first_tick = True
        self._cvd_1m = 0.0
        self._cvd_5m = 0.0
        self._cvd_15m = 0.0
        self._cvd_1h = 0.0
        self._cvd_4h = 0.0
        self._rolling_1m = 0.0
        self._rolling_5m = 0.0
        self._rolling_15m = 0.0
        self._rolling_1h = 0.0
        self._rolling_4h = 0.0
        self._divergence = False
        self._trend = "FLAT"

    def reset_session(self) -> None:
        self._buf_1m.clear()
        self._buf_5m.clear()
        self._buf_15m.clear()
        self._buf_1h.clear()
        self._buf_4h.clear()
        self._rolling_1m = 0.0
        self._rolling_5m = 0.0
        self._rolling_15m = 0.0
        self._rolling_1h = 0.0
        self._rolling_4h = 0.0
        self._cvd_1m = 0.0
        self._cvd_5m = 0.0
        self._cvd_15m = 0.0
        self._cvd_1h = 0.0
        self._cvd_4h = 0.0
        self._cvd_session = 0.0
        self._price_open = 0.0
        self._first_tick = True
        self._divergence = False
        self._trend = "FLAT"

    def _update(self, tick: TradeTick) -> None:
        price = float(tick.price)
        ts = int(tick.ts_event)
        signed_vol = self._signed_volume(tick)
        if self._first_tick:
            self._price_open = price
            self._first_tick = False

        self._cvd_session += signed_vol
        self._rolling_1m = self._update_window(self._buf_1m, ts, signed_vol, self.WINDOW_1M, self._rolling_1m)
        self._rolling_5m = self._update_window(self._buf_5m, ts, signed_vol, self.WINDOW_5M, self._rolling_5m)
        self._rolling_15m = self._update_window(self._buf_15m, ts, signed_vol, self.WINDOW_15M, self._rolling_15m)
        self._rolling_1h = self._update_window(self._buf_1h, ts, signed_vol, self.WINDOW_1H, self._rolling_1h)
        self._rolling_4h = self._update_window(self._buf_4h, ts, signed_vol, self.WINDOW_4H, self._rolling_4h)
        self._cvd_1m = self._rolling_1m
        self._cvd_5m = self._rolling_5m
        self._cvd_15m = self._rolling_15m
        self._cvd_1h = self._rolling_1h
        self._cvd_4h = self._rolling_4h

        price_up = price > self._price_open
        price_down = price < self._price_open
        self._divergence = (
            (price_up and self._cvd_5m < -self._div_thresh)
            or (price_down and self._cvd_5m > self._div_thresh)
        )

        if self._cvd_session > self._flat_thresh:
            self._trend = "RISING"
        elif self._cvd_session < -self._flat_thresh:
            self._trend = "FALLING"
        else:
            self._trend = "FLAT"

    @property
    def cvd_session(self) -> float:
        return self._cvd_session

    @property
    def cvd_1m(self) -> float:
        return self._cvd_1m

    @property
    def cvd_5m(self) -> float:
        return self._cvd_5m

    @property
    def cvd_15m(self) -> float:
        return self._cvd_15m

    @property
    def cvd_1h(self) -> float:
        return self._cvd_1h

    @property
    def cvd_4h(self) -> float:
        return self._cvd_4h

    @property
    def divergence(self) -> bool:
        return self._divergence

    @property
    def trend(self) -> str:
        return self._trend

    @staticmethod
    def _update_window(
        buffer: deque[tuple[int, float]],
        ts: int,
        signed_vol: float,
        window_ns: int,
        rolling_sum: float,
    ) -> float:
        buffer.append((ts, signed_vol))
        rolling_sum += signed_vol
        cutoff_ns = ts - window_ns
        while buffer and buffer[0][0] <= cutoff_ns:
            _, value = buffer.popleft()
            rolling_sum -= value
        return rolling_sum


class SwingDivergenceEngine(BaseEngine):
    """Rolling price/CVD extrema for structural divergence checks."""

    def __init__(
        self,
        window_ns: int = 1_800_000_000_000,
        warm_period: int = 20,
    ) -> None:
        super().__init__([window_ns, warm_period])
        self._window_ns = window_ns
        self._warm = warm_period
        self._min_ticks = warm_period
        self._price_high = 0.0
        self._price_low = float("inf")
        self._cvd_high = 0.0
        self._cvd_low = 0.0
        self._buf_price_high: deque[tuple[int, float]] = deque()
        self._buf_price_low: deque[tuple[int, float]] = deque()
        self._buf_cvd_high: deque[tuple[int, float]] = deque()
        self._buf_cvd_low: deque[tuple[int, float]] = deque()

    def update(self, ts: int, price: float, cvd_15m: float) -> None:
        self._tick_count += 1
        self._append_max(self._buf_price_high, ts, price)
        self._append_min(self._buf_price_low, ts, price)
        self._append_max(self._buf_cvd_high, ts, cvd_15m)
        self._append_min(self._buf_cvd_low, ts, cvd_15m)
        cutoff = ts - self._window_ns
        self._prune_extrema_buffer(self._buf_price_high, cutoff)
        self._prune_extrema_buffer(self._buf_price_low, cutoff)
        self._prune_extrema_buffer(self._buf_cvd_high, cutoff)
        self._prune_extrema_buffer(self._buf_cvd_low, cutoff)
        self._price_high = self._buf_price_high[0][1]
        self._price_low = self._buf_price_low[0][1]
        self._cvd_high = self._buf_cvd_high[0][1]
        self._cvd_low = self._buf_cvd_low[0][1]
        if not self.initialized and self._tick_count >= self._warm:
            self._set_initialized()

    def _update(self, tick: TradeTick) -> None:
        raise NotImplementedError("use update(ts, price, cvd_15m)")

    @staticmethod
    def _append_max(buffer: deque[tuple[int, float]], ts: int, value: float) -> None:
        while buffer and buffer[-1][1] <= value:
            buffer.pop()
        buffer.append((ts, value))

    @staticmethod
    def _append_min(buffer: deque[tuple[int, float]], ts: int, value: float) -> None:
        while buffer and buffer[-1][1] >= value:
            buffer.pop()
        buffer.append((ts, value))

    @staticmethod
    def _prune_extrema_buffer(buffer: deque[tuple[int, float]], cutoff_ns: int) -> None:
        while buffer and buffer[0][0] < cutoff_ns:
            buffer.popleft()

    @property
    def price_high(self) -> float:
        return self._price_high

    @property
    def price_low(self) -> float:
        return self._price_low

    @property
    def cvd_high(self) -> float:
        return self._cvd_high

    @property
    def cvd_low(self) -> float:
        return self._cvd_low


class SessionExtremeTracker:
    """Tracks session high/low since midnight UTC."""

    def __init__(self) -> None:
        self._session_high: float = 0.0
        self._session_low: float = float("inf")
        self._session_key: int = -1

    def update(self, ts_ns: int, price: float) -> None:
        day_key = ts_ns // 86_400_000_000_000
        if day_key != self._session_key:
            self._session_high = price
            self._session_low = price
            self._session_key = day_key
        else:
            if price > self._session_high:
                self._session_high = price
            if price < self._session_low:
                self._session_low = price

    @property
    def session_high(self) -> float:
        return self._session_high

    @property
    def session_low(self) -> float:
        return self._session_low

    @property
    def session_range(self) -> float:
        return self._session_high - self._session_low

    def near_high(self, price: float, pct: float) -> bool:
        if self._session_high == 0:
            return False
        return price >= self._session_high * (1 - pct)

    def near_low(self, price: float, pct: float) -> bool:
        if self._session_low == float("inf"):
            return False
        return price <= self._session_low * (1 + pct)


class FootprintEngine(BaseEngine):
    """Delta imbalance by price level. IC target >= 0.02; warm-up: warm_period."""

    def __init__(
        self,
        tick_size: float = 0.5,
        window_ns: int = 300_000_000_000,
        stack_threshold: int = 3,
        warm_period: int = 100,
    ) -> None:
        super().__init__([tick_size, window_ns, stack_threshold])
        self._tick_size = tick_size
        self._window_ns = window_ns
        self._stack_thresh = stack_threshold
        self._warm = warm_period
        self._min_ticks = warm_period
        self._events: deque[tuple[int, float, float]] = deque()
        self._level_counts: dict[float, int] = {}
        self._active_levels: list[float] = []
        self._deltas: dict[float, float] = {}
        self._dominant: float | None = None
        self._bias = 0
        self._stacked = False

    def _update(self, tick: TradeTick) -> None:
        price = float(tick.price)
        ts = int(tick.ts_event)
        signed_vol = self._signed_volume(tick)
        level = round(price / self._tick_size) * self._tick_size

        self._events.append((ts, level, signed_vol))
        self._add_level(level)
        self._deltas[level] = self._deltas.get(level, 0.0) + signed_vol
        cutoff = ts - self._window_ns
        while self._events and self._events[0][0] <= cutoff:
            _, expired_level, value = self._events.popleft()
            self._deltas[expired_level] -= value
            self._remove_level(expired_level)

        if self._active_levels:
            self._dominant = max(self._active_levels, key=lambda lvl: (abs(self._deltas[lvl]), -lvl))
            dom = self._deltas[self._dominant]
            self._bias = +1 if dom > 0 else -1 if dom < 0 else 0
            sides = [
                +1 if self._deltas[lvl] > 0 else -1 if self._deltas[lvl] < 0 else 0
                for lvl in self._active_levels
            ]
            self._stacked = self._check_stacked(sides, self._stack_thresh)
        else:
            self._dominant = None
            self._bias = 0
            self._stacked = False

    def _add_level(self, level: float) -> None:
        count = self._level_counts.get(level, 0)
        if count == 0:
            insort(self._active_levels, level)
        self._level_counts[level] = count + 1

    def _remove_level(self, level: float) -> None:
        count = self._level_counts[level] - 1
        if count > 0:
            self._level_counts[level] = count
            return
        del self._level_counts[level]
        del self._deltas[level]
        idx = bisect_left(self._active_levels, level)
        if idx < len(self._active_levels) and self._active_levels[idx] == level:
            self._active_levels.pop(idx)

    @property
    def dominant_level(self) -> Optional[float]:
        return self._dominant

    @property
    def footprint_bias(self) -> int:
        return self._bias

    @property
    def stacked(self) -> bool:
        return self._stacked

    @staticmethod
    def _check_stacked(sides: list[int], threshold: int) -> bool:
        if len(sides) < threshold:
            return False
        count = 1
        for idx in range(1, len(sides)):
            if sides[idx] == sides[idx - 1] and sides[idx] != 0:
                count += 1
                if count >= threshold:
                    return True
            else:
                count = 1
        return False


class DeltaVelocityEngine(BaseEngine):
    """EMA signed-volume velocity. Warm-up: warm_period ticks."""

    def __init__(
        self,
        ema_alpha: float = 0.1,
        exhaustion_threshold: float = 500.0,
        warm_period: int = 50,
    ) -> None:
        super().__init__([ema_alpha, exhaustion_threshold, warm_period])
        self._alpha = ema_alpha
        self._thresh = exhaustion_threshold
        self._min_ticks = warm_period
        self._ema_velocity = 0.0
        self._ema_acceleration = 0.0
        self._peak_velocity = 0.0
        self._exhaustion = "NONE"

    def _update(self, tick: TradeTick) -> None:
        signed_vol = self._signed_volume(tick)
        prev = self._ema_velocity
        self._ema_velocity = self._alpha * signed_vol + (1 - self._alpha) * self._ema_velocity
        self._ema_acceleration = self._ema_velocity - prev
        if abs(self._ema_velocity) > abs(self._peak_velocity):
            self._peak_velocity = self._ema_velocity

        if self._peak_velocity > self._thresh and self._ema_velocity < 0:
            self._exhaustion = "BUY_EXHAUSTION"
        elif self._peak_velocity < -self._thresh and self._ema_velocity > 0:
            self._exhaustion = "SELL_EXHAUSTION"
        else:
            self._exhaustion = "NONE"

    @property
    def velocity(self) -> float:
        return self._ema_velocity

    @property
    def acceleration(self) -> float:
        return self._ema_acceleration

    @property
    def exhaustion(self) -> str:
        return self._exhaustion


class VWAPEngine(BaseEngine):
    """Session VWAP structure gate. Warm-up: warm_period ticks."""

    def __init__(self, warm_period: int = 50) -> None:
        super().__init__([warm_period])
        self._min_ticks = warm_period
        self._cum_pv = 0.0
        self._cum_vol = 0.0
        self._vwap = 0.0
        self._deviation = 0.0

    def _update(self, tick: TradeTick) -> None:
        price = float(tick.price)
        size = float(tick.size)
        self._cum_pv += price * size
        self._cum_vol += size
        if self._cum_vol > 0:
            self._vwap = self._cum_pv / self._cum_vol
            self._deviation = (price - self._vwap) / self._vwap if self._vwap > 0 else 0.0

    def reset_session(self) -> None:
        self._cum_pv = 0.0
        self._cum_vol = 0.0
        self._vwap = 0.0
        self._deviation = 0.0
        self._tick_count = 0
        self._initialized = False

    @property
    def vwap(self) -> float:
        return self._vwap

    @property
    def deviation(self) -> float:
        return self._deviation


class VolumeProfileEngine(BaseEngine):
    """Session volume profile. Warm-up: warm_period ticks."""

    def __init__(
        self,
        tick_size: float = 0.5,
        value_area_pct: float = 0.70,
        warm_period: int = 200,
    ) -> None:
        super().__init__([tick_size, value_area_pct])
        self._tick_size = tick_size
        self._va_pct = value_area_pct
        self._min_ticks = warm_period
        self._vol_at: dict[float, float] = {}
        self._total_vol = 0.0
        self._poc: Optional[float] = None
        self._vah: Optional[float] = None
        self._val: Optional[float] = None
        self._vp_pos = 0.0

    def _update(self, tick: TradeTick) -> None:
        price = float(tick.price)
        size = float(tick.size)
        level = round(price / self._tick_size) * self._tick_size
        self._vol_at[level] = self._vol_at.get(level, 0.0) + size
        self._total_vol += size

        sorted_levels = sorted(self._vol_at.keys())
        if sorted_levels:
            self._poc = max(sorted_levels, key=lambda lvl: (self._vol_at[lvl], -lvl))
            self._vah, self._val = self._value_area(sorted_levels)
            self._vp_pos = self._position(price)

    def _value_area(self, levels: list[float]) -> tuple[Optional[float], Optional[float]]:
        if self._poc is None:
            return None, None
        target = self._total_vol * self._va_pct
        acc = self._vol_at.get(self._poc, 0.0)
        poc_i = levels.index(self._poc)
        lo = hi = poc_i
        while acc < target:
            can_up = hi + 1 < len(levels)
            can_dn = lo - 1 >= 0
            if not can_up and not can_dn:
                break
            up_v = self._vol_at.get(levels[hi + 1], 0.0) if can_up else -1.0
            dn_v = self._vol_at.get(levels[lo - 1], 0.0) if can_dn else -1.0
            if can_up and up_v >= dn_v:
                hi += 1
                acc += up_v
            elif can_dn:
                lo -= 1
                acc += dn_v
            else:
                break
        return levels[hi], levels[lo]

    def _position(self, price: float) -> float:
        if self._vah is None or self._val is None:
            return 0.0
        if price > self._vah:
            return 2.0
        if price < self._val:
            return -1.0
        span = self._vah - self._val
        return (price - self._val) / span if span > 0 else 0.5

    @property
    def poc(self) -> Optional[float]:
        return self._poc

    @property
    def vah(self) -> Optional[float]:
        return self._vah

    @property
    def val(self) -> Optional[float]:
        return self._val

    @property
    def vp_position(self) -> float:
        return self._vp_pos
