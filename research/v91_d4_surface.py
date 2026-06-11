"""Past-only D4 bar-size and horizon surface diagnostics."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Sequence

import numpy as np

from prime.volume_bar_cvd import divergence_side_at
from prime.volume_bars import VolumeBar
from research.v91_recovered_context import _completed_mtf_biases, market_structure
from research.v91_signal_purity import historical_flat_thresholds, htf_allows, one_hour_cvd_changes


COSTS_BPS = (1, 2, 3, 5, 8, 12)


def rebar_volume_bars(base_bars: Sequence[VolumeBar], threshold_btc: float) -> list[VolumeBar]:
    """Aggregate completed base bars without splitting them."""
    output: list[VolumeBar] = []
    group: list[VolumeBar] = []
    cumulative_delta = 0.0
    for bar in base_bars:
        group.append(bar)
        if sum(item.volume for item in group) < threshold_btc:
            continue
        delta = sum(item.delta for item in group)
        cumulative_delta += delta
        output.append(
            VolumeBar(
                start_ts_ns=group[0].start_ts_ns,
                end_ts_ns=group[-1].end_ts_ns,
                open=group[0].open,
                high=max(item.high for item in group),
                low=min(item.low for item in group),
                close=group[-1].close,
                volume=round(sum(item.volume for item in group), 8),
                buy_volume=round(sum(item.buy_volume for item in group), 8),
                sell_volume=round(sum(item.sell_volume for item in group), 8),
                delta=round(delta, 8),
                cumulative_delta=round(cumulative_delta, 8),
                ticks=sum(item.ticks for item in group),
            )
        )
        group = []
    return output


def build_surface(
    bars_by_threshold: dict[int, Sequence[VolumeBar]],
    *,
    lookback_bars: int = 40,
    horizons: Sequence[int] = (5, 10, 15, 24, 36, 48),
    bootstrap_samples: int = 500,
) -> dict[str, Any]:
    rows = []
    for threshold, bars in sorted(bars_by_threshold.items()):
        rows.extend(
            threshold_surface(
                bars,
                threshold=threshold,
                lookback_bars=lookback_bars,
                horizons=horizons,
                bootstrap_samples=bootstrap_samples,
            )
        )
    return {
        "config": {
            "lookback_bars": lookback_bars,
            "horizons": list(horizons),
            "bar_sizes_btc": sorted(bars_by_threshold),
            "contexts": ["none", "mtf_aligned", "mtf_against", "range", "trend"],
            "costs_bps_roundtrip": list(COSTS_BPS),
            "bootstrap_samples": bootstrap_samples,
            "signal": "D4 past-only rolling HTF threshold",
        },
        "rows": rows,
    }


def threshold_surface(
    bars: Sequence[VolumeBar],
    *,
    threshold: int,
    lookback_bars: int,
    horizons: Sequence[int],
    bootstrap_samples: int,
) -> list[dict[str, Any]]:
    htf_changes = one_hour_cvd_changes(bars)
    flat_thresholds = historical_flat_thresholds(htf_changes)
    mtf = _completed_mtf_biases(bars)
    max_horizon = max(horizons)
    event_indices: list[tuple[int, int, str, str]] = []
    for idx in range(lookback_bars, len(bars) - max_horizon):
        side = divergence_side_at(bars[idx - lookback_bars : idx + 1], lookback_bars, lookback_bars)
        if side is None or not htf_allows(side, htf_changes[idx], flat_thresholds[idx]):
            continue
        alignment = _alignment_filter(side, mtf[idx])
        structure, _ = market_structure(bars[max(0, idx - 100) : idx], bars[idx].close)
        event_indices.append((idx, side, alignment, structure))

    rows = []
    for horizon in horizons:
        buckets: dict[str, list[tuple[int, float]]] = {
            name: [] for name in ("none", "mtf_aligned", "mtf_against", "range", "trend")
        }
        period_buckets: dict[str, dict[str, list[tuple[int, float]]]] = {
            name: {"2020-2023": [], "2024-2026": []} for name in buckets
        }
        for idx, side, alignment, structure in event_indices:
            raw_return = (bars[idx + horizon].close - bars[idx].close) / bars[idx].close
            signed_return = side * raw_return
            period = _period(bars[idx].end_ts_ns)
            selected = ["none"]
            if alignment in {"mtf_aligned", "mtf_against"}:
                selected.append(alignment)
            selected.append("range" if structure == "range" else "trend")
            for context in selected:
                buckets[context].append((side, raw_return))
                period_buckets[context][period].append((side, raw_return))
        for context, values in buckets.items():
            rows.append(
                {
                    "bar_size_btc": threshold,
                    "horizon_bars": horizon,
                    "context": context,
                    "all": surface_metrics(values, bootstrap_samples=bootstrap_samples, seed=_seed(threshold, horizon, context, "all")),
                    "2020-2023": surface_metrics(period_buckets[context]["2020-2023"], bootstrap_samples=bootstrap_samples, seed=_seed(threshold, horizon, context, "old")),
                    "2024-2026": surface_metrics(period_buckets[context]["2024-2026"], bootstrap_samples=bootstrap_samples, seed=_seed(threshold, horizon, context, "recent")),
                }
            )
    return rows


def surface_metrics(
    side_and_raw_returns: Sequence[tuple[int, float]],
    *,
    bootstrap_samples: int = 500,
    seed: int = 0,
) -> dict[str, Any]:
    rows = list(side_and_raw_returns)
    if not rows:
        return {
            "events": 0, "hit_rate": 0.0, "mean_signed_return_bps": 0.0, "median_signed_return_bps": 0.0,
            "ic": 0.0, "t_stat": 0.0, "bootstrap_mean_bps_ci_95": [0.0, 0.0],
            "net_expectancy_bps": {str(cost): 0.0 for cost in COSTS_BPS},
        }
    sides = np.asarray([side for side, _ in rows], dtype=float)
    raw = np.asarray([value for _, value in rows], dtype=float)
    signed = sides * raw
    mean = float(np.mean(signed))
    std = float(np.std(signed, ddof=1)) if len(signed) > 1 else 0.0
    rng = np.random.default_rng(seed)
    bootstrap = np.mean(rng.choice(signed, size=(bootstrap_samples, len(signed)), replace=True), axis=1) * 10_000
    return {
        "events": len(rows),
        "hit_rate": float(np.mean(signed > 0)),
        "mean_signed_return_bps": mean * 10_000,
        "median_signed_return_bps": float(np.median(signed)) * 10_000,
        "ic": _correlation(sides, raw),
        "t_stat": mean / (std / math.sqrt(len(signed))) if std else 0.0,
        "bootstrap_mean_bps_ci_95": [float(np.quantile(bootstrap, 0.025)), float(np.quantile(bootstrap, 0.975))],
        "net_expectancy_bps": {str(cost): mean * 10_000 - cost for cost in COSTS_BPS},
    }


def _alignment_filter(side: int, biases: dict[str, int]) -> str:
    values = list(biases.values())
    if values and all(value == side for value in values):
        return "mtf_aligned"
    if values and all(value == -side for value in values):
        return "mtf_against"
    return "other"


def _correlation(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2 or np.std(left) == 0.0 or np.std(right) == 0.0:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _period(ts_ns: int) -> str:
    year = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).year
    return "2020-2023" if year <= 2023 else "2024-2026"


def _seed(*parts: object) -> int:
    return int(hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:8], 16)
