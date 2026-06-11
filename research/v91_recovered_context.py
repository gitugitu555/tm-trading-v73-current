"""Past-only recovered-context diagnostics for the verified D4 signal."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Sequence

import numpy as np
import pandas as pd

from prime.performance import max_drawdown, sharpe_ratio, sortino_ratio
from prime.volume_bar_cvd import divergence_side_at
from prime.volume_bars import VolumeBar
from research.v91_signal_purity import historical_flat_thresholds, htf_allows, one_hour_cvd_changes


COST_ROUNDTRIP = 0.0012


def build_context_events(
    bars: Sequence[VolumeBar],
    *,
    lookback_bars: int = 40,
    horizon_bars: int = 5,
) -> list[dict[str, Any]]:
    """Build D4 events and context using information observable at signal close."""
    htf_changes = one_hour_cvd_changes(bars)
    thresholds = historical_flat_thresholds(htf_changes)
    mtf = _completed_mtf_biases(bars)
    events = []
    for idx in range(lookback_bars, len(bars) - max(horizon_bars, 49)):
        side = divergence_side_at(bars[idx - lookback_bars : idx + 1], lookback_bars, lookback_bars)
        if side is None or not htf_allows(side, htf_changes[idx], thresholds[idx]):
            continue
        bar = bars[idx]
        profile = coarse_profile(bars[max(0, idx - 100) : idx])
        structure, key_level = market_structure(bars[max(0, idx - 100) : idx], bar.close)
        alignment = mtf_alignment(side, mtf[idx])
        raw_return = side * (bars[idx + horizon_bars].close - bar.close) / bar.close
        forward_raw_return = (bars[idx + horizon_bars].close - bar.close) / bar.close
        events.append(
            {
                "signal_id": f"V91_CTX_{bar.end_ts_ns}_{side}",
                "bar_id": idx,
                "signal_ts_ns": bar.end_ts_ns,
                "year": datetime.fromtimestamp(bar.end_ts_ns / 1e9, tz=timezone.utc).year,
                "period": "2020-2023" if bar.end_ts_ns < 1704067200_000_000_000 else "2024-2026",
                "side": side,
                "raw_return": raw_return,
                "forward_raw_return": forward_raw_return,
                "market_structure": structure,
                "key_level": key_level,
                "mtf_alignment": alignment,
                "mtf_biases": mtf[idx],
                **profile_context(bar.close, profile),
                "profile": profile,
            }
        )
    return events


def market_structure(prior: Sequence[VolumeBar], current_price: float) -> tuple[str, str]:
    """Past-only structure and nearest-level context, without future-confirmed swings."""
    if len(prior) < 40:
        return "range", "no_key_level"
    closes = np.asarray([bar.close for bar in prior], dtype=float)
    x = np.arange(40, dtype=float)
    slope = np.polyfit(x, closes[-40:], 1)[0] / max(closes[-1], 1e-12)
    threshold = np.std(np.diff(closes[-40:]) / closes[-40:-1]) * 0.25
    structure = "uptrend" if slope > threshold else "downtrend" if slope < -threshold else "range"
    support = min(bar.low for bar in prior[-100:])
    resistance = max(bar.high for bar in prior[-100:])
    near_support = abs(current_price - support) / current_price < 0.003
    near_resistance = abs(current_price - resistance) / current_price < 0.003
    if near_support and not near_resistance:
        return structure, "near_support"
    if near_resistance and not near_support:
        return structure, "near_resistance"
    return structure, "no_key_level"


def coarse_profile(prior: Sequence[VolumeBar], bins: int = 50) -> dict[str, float | None]:
    """Guide-style 50-bin profile from completed prior bars only."""
    if not prior:
        return {"poc": None, "vah": None, "val": None}
    low = min(bar.low for bar in prior)
    high = max(bar.high for bar in prior)
    if high <= low:
        return {"poc": prior[-1].close, "vah": high, "val": low}
    histogram = np.zeros(bins, dtype=float)
    width = (high - low) / bins
    for bar in prior:
        midpoint = (bar.high + bar.low) / 2
        index = min(bins - 1, max(0, int((midpoint - low) / width)))
        histogram[index] += bar.volume
    poc_idx = int(np.argmax(histogram))
    included = {poc_idx}
    volume = histogram[poc_idx]
    target = histogram.sum() * 0.70
    left, right = poc_idx - 1, poc_idx + 1
    while volume < target and (left >= 0 or right < bins):
        left_volume = histogram[left] if left >= 0 else -1
        right_volume = histogram[right] if right < bins else -1
        chosen = right if right_volume >= left_volume else left
        included.add(chosen)
        volume += histogram[chosen]
        if chosen == right:
            right += 1
        else:
            left -= 1
    price = lambda index: low + (index + 0.5) * width
    return {"poc": price(poc_idx), "vah": price(max(included)), "val": price(min(included))}


def profile_context(price: float, profile: dict[str, float | None]) -> dict[str, str]:
    poc, vah, val = profile["poc"], profile["vah"], profile["val"]
    if poc is None or vah is None or val is None:
        return {"poc_context": "unknown", "value_context": "unknown"}
    distance = abs(price - poc) / price
    poc_context = "near_poc" if distance < 0.003 else "above_poc" if price > poc else "below_poc"
    value_context = "above_vah" if price > vah else "below_val" if price < val else "inside_value_area"
    return {"poc_context": poc_context, "value_context": value_context}


def mtf_alignment(side: int, biases: dict[str, int]) -> str:
    values = list(biases.values())
    aligned = sum(value == side for value in values)
    against = sum(value == -side for value in values)
    neutral = sum(value == 0 for value in values)
    if aligned == 4:
        return "aligned_with_d4"
    if against == 4:
        return "against_d4"
    if aligned >= 2 and against == 0:
        return "partially_aligned"
    if against >= 2 and aligned == 0:
        return "against_d4"
    return "mixed" if neutral < 4 else "mixed"


def _completed_mtf_biases(bars: Sequence[VolumeBar]) -> list[dict[str, int]]:
    frame = pd.DataFrame(
        {"ts": pd.to_datetime([bar.end_ts_ns for bar in bars], utc=True), "close": [bar.close for bar in bars]}
    ).set_index("ts")
    output = pd.DataFrame(index=frame.index)
    for label, rule in {"15m": "15min", "1h": "1h", "4h": "4h", "daily": "1D"}.items():
        completed = frame["close"].resample(rule, label="right", closed="right").last().dropna()
        ema = completed.ewm(span=20, adjust=False).mean()
        bias = pd.Series(np.where(completed > ema * 1.002, 1, np.where(completed < ema * 0.998, -1, 0)), index=completed.index)
        # A bucket becomes observable only after its close.
        output[label] = bias.reindex(output.index, method="ffill").fillna(0).astype(int)
    return output.to_dict(orient="records")


def context_report(events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    dimensions = {
        "market_structure": ["uptrend", "downtrend", "range"],
        "key_level": ["near_support", "near_resistance", "no_key_level"],
        "mtf_alignment": ["aligned_with_d4", "partially_aligned", "against_d4", "mixed"],
        "poc_context": ["above_poc", "below_poc", "near_poc"],
        "value_context": ["inside_value_area", "above_vah", "below_val"],
    }
    return {
        dimension: {
            bucket: {
                period: event_metrics([event for event in events if event[dimension] == bucket and (period == "all" or event["period"] == period)])
                for period in ("all", "2020-2023", "2024-2026")
            }
            for bucket in buckets
        }
        for dimension, buckets in dimensions.items()
    }


def signal_metrics(returns: Sequence[float]) -> dict[str, Any]:
    values = list(returns)
    if not values:
        return _empty_metrics()
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    t_stat = mean / (std / math.sqrt(len(values))) if std else 0.0
    equity = list(np.cumprod(1 + np.asarray(values) * 0.01))
    return {
        "events": len(values),
        "hit_rate": sum(value > 0 for value in values) / len(values),
        "mean_signed_return_bps": mean * 10_000,
        "ic": 0.0,
        "t_stat": t_stat,
        "sharpe": sharpe_ratio(values),
        "sortino": sortino_ratio(values),
        "max_drawdown": max_drawdown(equity),
        "cost_adjusted_expectancy_bps": (mean - COST_ROUNDTRIP) * 10_000,
    }


def event_metrics(events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result = signal_metrics([float(event["raw_return"]) for event in events])
    result["ic"] = _correlation(
        [float(event["side"]) for event in events],
        [float(event["forward_raw_return"]) for event in events],
    )
    return result


def replay_exits(events: Sequence[dict[str, Any]], bars: Sequence[VolumeBar]) -> dict[str, Any]:
    policies = ("fixed_tpsl", "cvd_reversal", "time_exit", "profile_exit", "trailing", "partial_dynamic")
    returns: dict[str, list[tuple[str, int, float]]] = defaultdict(list)
    for event in events:
        idx, side = int(event["bar_id"]), int(event["side"])
        if idx + 49 >= len(bars):
            continue
        entry = bars[idx + 1].open  # Explicitly no same-bar entry.
        path = bars[idx + 1 : idx + 49]
        for policy in policies:
            gross = _exit_return(policy, entry, side, path, event["profile"])
            returns[policy].append((event["period"], side, gross))
    return {
        policy: {
            period: trade_metrics(
                [(side, value) for row_period, side, value in rows if period == "all" or row_period == period]
            )
            for period in ("all", "2020-2023", "2024-2026")
        }
        for policy, rows in returns.items()
    }


def _exit_return(policy: str, entry: float, side: int, path: Sequence[VolumeBar], profile: dict[str, float | None]) -> float:
    target, stop = 0.006, 0.003
    max_favorable = 0.0
    partial_taken = False
    partial_return = 0.0
    for offset, bar in enumerate(path, start=1):
        favorable = (bar.high - entry) / entry if side > 0 else (entry - bar.low) / entry
        adverse = (entry - bar.low) / entry if side > 0 else (bar.high - entry) / entry
        close_return = side * (bar.close - entry) / entry
        max_favorable = max(max_favorable, favorable)
        if adverse >= stop:
            return partial_return + (-stop * (0.5 if partial_taken else 1.0))
        if policy == "fixed_tpsl" and favorable >= target:
            return target
        if policy == "cvd_reversal" and offset >= 2 and side * bar.delta < 0:
            return close_return
        if policy == "time_exit" and offset == 24:
            return close_return
        if policy == "profile_exit" and _profile_level_hit(side, bar, profile):
            return close_return
        if policy == "trailing" and max_favorable >= 0.005 and close_return <= max_favorable - 0.004:
            return close_return
        if policy == "partial_dynamic":
            if not partial_taken and favorable >= 0.003:
                partial_taken, partial_return = True, 0.0015
            if partial_taken and (close_return <= 0.0 or max_favorable >= 0.006 and close_return <= max_favorable - 0.003):
                return partial_return + close_return * 0.5
        if offset == 48:
            return partial_return + close_return * (0.5 if partial_taken else 1.0)
    return 0.0


def _profile_level_hit(side: int, bar: VolumeBar, profile: dict[str, float | None]) -> bool:
    levels = [value for value in profile.values() if value is not None]
    return any(bar.low <= level <= bar.high for level in levels) and side * (bar.close - bar.open) > 0


def trade_metrics(side_and_gross_returns: Sequence[tuple[int, float]]) -> dict[str, Any]:
    rows = list(side_and_gross_returns)
    gross = [value for _, value in rows]
    if not gross:
        return _empty_metrics()
    net = [value - COST_ROUNDTRIP for value in gross]
    result = signal_metrics(net)
    result["ic"] = _correlation([side for side, _ in rows], [side * value for side, value in rows])
    result["gross_expectancy_bps"] = float(np.mean(gross)) * 10_000
    result["cost_adjusted_expectancy_bps"] = float(np.mean(net)) * 10_000
    return result


def _correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 2 or len(right) != len(left):
        return 0.0
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    if np.std(left_array) == 0.0 or np.std(right_array) == 0.0:
        return 0.0
    value = np.corrcoef(left_array, right_array)[0, 1]
    return float(value) if np.isfinite(value) else 0.0


def _empty_metrics() -> dict[str, Any]:
    return {
        "events": 0, "hit_rate": 0.0, "mean_signed_return_bps": 0.0, "ic": 0.0, "t_stat": 0.0,
        "sharpe": 0.0, "sortino": 0.0, "max_drawdown": 0.0, "cost_adjusted_expectancy_bps": 0.0,
    }
