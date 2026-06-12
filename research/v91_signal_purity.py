"""Signal-only CVD divergence scoring on a fixed volume-bar catalog."""

from __future__ import annotations

import bisect
import math
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Sequence

from prime.volume_bar_cvd import divergence_side_at
from prime.volume_bars import VolumeBar


class SignalMetrics:
    def __init__(self) -> None:
        self.events = 0
        self.hits = 0
        self.sum_sfr = 0.0
        self.sum_sfr_sq = 0.0
        self.sum_side = 0.0
        self.sum_return = 0.0
        self.sum_side_sq = 0.0
        self.sum_return_sq = 0.0
        self.sum_side_return = 0.0

    def add(self, side: int, raw_return: float) -> None:
        self.events += 1
        self.hits += int(side * raw_return > 0.0)
        signed_forward_return = side * raw_return
        self.sum_sfr += signed_forward_return
        self.sum_sfr_sq += signed_forward_return * signed_forward_return
        self.sum_side += side
        self.sum_return += raw_return
        self.sum_side_sq += side * side
        self.sum_return_sq += raw_return * raw_return
        self.sum_side_return += side * raw_return

    def summary(self) -> dict[str, Any]:
        mean_sfr = self.sum_sfr / self.events if self.events else 0.0
        variance = (
            (self.sum_sfr_sq - self.events * mean_sfr * mean_sfr) / (self.events - 1)
            if self.events > 1
            else 0.0
        )
        standard_error = math.sqrt(max(variance, 0.0) / self.events) if self.events else 0.0
        return {
            "events": self.events,
            "hits": self.hits,
            "hit_rate": self.hits / self.events if self.events else 0.0,
            "mean_signed_forward_return": mean_sfr,
            "mean_signed_forward_return_bps": mean_sfr * 10_000,
            "mean_sfr_t_stat": mean_sfr / standard_error if standard_error else 0.0,
            "ic": self._ic(),
        }

    def _ic(self) -> float:
        if self.events < 2:
            return 0.0
        covariance = self.sum_side_return - self.sum_side * self.sum_return / self.events
        side_variance = self.sum_side_sq - self.sum_side * self.sum_side / self.events
        return_variance = self.sum_return_sq - self.sum_return * self.sum_return / self.events
        if side_variance <= 0.0 or return_variance <= 0.0:
            return 0.0
        return covariance / math.sqrt(side_variance * return_variance)


def one_hour_cvd_changes(bars: Sequence[VolumeBar]) -> list[float]:
    timestamps = [bar.end_ts_ns for bar in bars]
    changes = []
    for idx, bar in enumerate(bars):
        prior_idx = bisect.bisect_left(
            timestamps,
            bar.end_ts_ns - 3_600_000_000_000,
            0,
            idx + 1,
        )
        changes.append(bar.cumulative_delta - bars[prior_idx].cumulative_delta)
    return changes


def historical_flat_thresholds(
    htf_changes: Sequence[float],
    *,
    quantile: float = 0.25,
    window: int = 2000,
    min_samples: int = 10,
) -> list[float]:
    """Return thresholds calculated before observing each current HTF change."""
    history: deque[float] = deque(maxlen=window)
    sorted_history: list[float] = []
    thresholds: list[float] = []
    for change in htf_changes:
        if len(sorted_history) >= min_samples:
            thresholds.append(sorted_history[int((len(sorted_history) - 1) * quantile)])
        else:
            thresholds.append(0.0)
        value = abs(change)
        if len(history) == history.maxlen:
            old = history.popleft()
            sorted_history.pop(bisect.bisect_left(sorted_history, old))
        history.append(value)
        bisect.insort(sorted_history, value)
    return thresholds


def quantile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[int((len(ordered) - 1) * min(max(q, 0.0), 1.0))]


def htf_allows(side: int, change: float, threshold: float) -> bool:
    return change <= threshold if side < 0 else change >= -threshold


def score_signal_purity(
    bars: Sequence[VolumeBar],
    *,
    lookback_bars: int = 40,
    horizon_bars: int = 5,
    htf_flat_quantile: float = 0.25,
    rolling_window: int = 2000,
) -> dict[str, Any]:
    """Score immutable signals without trade selection or execution semantics."""
    htf_changes = one_hour_cvd_changes(bars)
    legacy_threshold = quantile([abs(value) for value in htf_changes], htf_flat_quantile)
    honest_thresholds = historical_flat_thresholds(
        htf_changes,
        quantile=htf_flat_quantile,
        window=rolling_window,
    )
    modes = ("divergence_unfiltered", "d4_legacy_global_quantile", "d4_past_only_rolling")
    metrics: dict[str, dict[str, SignalMetrics]] = {
        mode: defaultdict(SignalMetrics) for mode in modes
    }

    for idx in range(lookback_bars, len(bars) - horizon_bars):
        window = bars[idx - lookback_bars : idx + 1]
        side = divergence_side_at(window, lookback_bars, lookback_bars)
        if side is None or bars[idx].close == 0.0:
            continue
        raw_return = (bars[idx + horizon_bars].close - bars[idx].close) / bars[idx].close
        year = str(datetime.fromtimestamp(bars[idx].end_ts_ns / 1e9, tz=timezone.utc).year)
        side_label = "long" if side > 0 else "short"
        selected_modes = ["divergence_unfiltered"]
        if htf_allows(side, htf_changes[idx], legacy_threshold):
            selected_modes.append("d4_legacy_global_quantile")
        if htf_allows(side, htf_changes[idx], honest_thresholds[idx]):
            selected_modes.append("d4_past_only_rolling")
        for mode in selected_modes:
            metrics[mode]["overall"].add(side, raw_return)
            metrics[mode][f"year:{year}"].add(side, raw_return)
            metrics[mode][f"side:{side_label}"].add(side, raw_return)

    return {
        "config": {
            "lookback_bars": lookback_bars,
            "horizon_bars": horizon_bars,
            "htf_flat_quantile": htf_flat_quantile,
            "past_only_rolling_window": rolling_window,
            "entry_reference": "signal_bar_close",
            "exit_reference": f"close_{horizon_bars}_bars_later",
            "position_occupancy": False,
            "trade_exit_logic": False,
        },
        "legacy_global_flat_abs_threshold": legacy_threshold,
        "modes": {
            mode: {
                "overall": buckets["overall"].summary(),
                "by_year": {
                    key.removeprefix("year:"): value.summary()
                    for key, value in sorted(buckets.items())
                    if key.startswith("year:")
                },
                "by_side": {
                    key.removeprefix("side:"): value.summary()
                    for key, value in sorted(buckets.items())
                    if key.startswith("side:")
                },
            }
            for mode, buckets in metrics.items()
        },
    }
