"""Research-only volume bar sampling for trade-tick streams."""

from __future__ import annotations

from dataclasses import dataclass

from prime.nautilus_compat import AggressorSide, aggressor_name


@dataclass(frozen=True)
class VolumeBar:
    start_ts_ns: int
    end_ts_ns: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_volume: float
    sell_volume: float
    delta: float
    cumulative_delta: float
    ticks: int


class VolumeBarSampler:
    """Accumulates trades into fixed-volume bars without splitting trades."""

    def __init__(self, threshold_volume: float) -> None:
        if threshold_volume <= 0:
            raise ValueError("threshold_volume must be positive")
        self.threshold_volume = float(threshold_volume)
        self._start_ts_ns = 0
        self._end_ts_ns = 0
        self._open = 0.0
        self._high = 0.0
        self._low = 0.0
        self._close = 0.0
        self._volume = 0.0
        self._buy_volume = 0.0
        self._sell_volume = 0.0
        self._ticks = 0
        self._cumulative_delta = 0.0

    def update(self, tick) -> VolumeBar | None:
        ts_ns = int(tick.ts_event)
        price = float(tick.price)
        volume = float(tick.size)
        if volume <= 0:
            return None

        if self._ticks == 0:
            self._start_ts_ns = ts_ns
            self._open = price
            self._high = price
            self._low = price
        else:
            if price > self._high:
                self._high = price
            if price < self._low:
                self._low = price

        self._end_ts_ns = ts_ns
        self._close = price
        self._volume += volume
        if self._is_buyer(tick.aggressor_side):
            self._buy_volume += volume
        elif self._is_seller(tick.aggressor_side):
            self._sell_volume += volume
        self._ticks += 1

        if self._volume < self.threshold_volume:
            return None
        return self._emit()

    @property
    def progress(self) -> float:
        """Fraction of the current volume bar filled, capped at one."""
        return min(1.0, self._volume / self.threshold_volume)

    def partial_snapshot(self) -> VolumeBar | None:
        """Return the observable state of the forming bar without emitting it."""
        if self._ticks == 0:
            return None
        delta = self._buy_volume - self._sell_volume
        return VolumeBar(
            start_ts_ns=self._start_ts_ns,
            end_ts_ns=self._end_ts_ns,
            open=self._open,
            high=self._high,
            low=self._low,
            close=self._close,
            volume=round(self._volume, 8),
            buy_volume=round(self._buy_volume, 8),
            sell_volume=round(self._sell_volume, 8),
            delta=round(delta, 8),
            cumulative_delta=round(self._cumulative_delta + delta, 8),
            ticks=self._ticks,
        )

    def _emit(self) -> VolumeBar:
        delta = self._buy_volume - self._sell_volume
        self._cumulative_delta += delta
        bar = VolumeBar(
            start_ts_ns=self._start_ts_ns,
            end_ts_ns=self._end_ts_ns,
            open=self._open,
            high=self._high,
            low=self._low,
            close=self._close,
            volume=round(self._volume, 8),
            buy_volume=round(self._buy_volume, 8),
            sell_volume=round(self._sell_volume, 8),
            delta=round(delta, 8),
            cumulative_delta=round(self._cumulative_delta, 8),
            ticks=self._ticks,
        )
        self._reset_bar()
        return bar

    def _reset_bar(self) -> None:
        self._start_ts_ns = 0
        self._end_ts_ns = 0
        self._open = 0.0
        self._high = 0.0
        self._low = 0.0
        self._close = 0.0
        self._volume = 0.0
        self._buy_volume = 0.0
        self._sell_volume = 0.0
        self._ticks = 0

    @staticmethod
    def _is_buyer(side: object) -> bool:
        side_name = aggressor_name(side)
        return side == AggressorSide.BUYER or side_name in {"BUYER", "BUY"}

    @staticmethod
    def _is_seller(side: object) -> bool:
        side_name = aggressor_name(side)
        return side == AggressorSide.SELLER or side_name in {"SELLER", "SELL"}
