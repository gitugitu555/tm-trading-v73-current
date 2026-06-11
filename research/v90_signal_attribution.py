"""Signal attribution over the verified immutable ledger."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from research.v86_recovery import summarize_trades


def signal_attribution(signals: list[dict[str, Any]], paths: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for signal in signals:
        path = paths.get(signal["signal_id"])
        if path is None:
            continue
        row = {**signal, **path}
        row["year"] = datetime.fromtimestamp(int(signal["signal_ts_ns"]) / 1e9, tz=timezone.utc).strftime("%Y")
        row["month"] = datetime.fromtimestamp(int(signal["signal_ts_ns"]) / 1e9, tz=timezone.utc).strftime("%Y-%m")
        row["session"] = _session_label(int(signal["signal_ts_ns"]))
        row["volatility_regime"] = _quantile_bucket(path["max_favorable_excursion_pct"] + path["max_adverse_excursion_pct"], (0.33, 0.66))
        row["volume_regime"] = _quantile_bucket(float(signal.get("volume", 0.0)), (0.33, 0.66))
        row["trend_regime"] = "trend" if float(path["return_at_bar_exit"]["24"] or 0.0) > 0 else "mean_revert"
        row["bar_duration"] = float(signal["bar_end_ts_ns"] - signal["bar_start_ts_ns"]) / 1e9
        row["bar_return"] = (float(signal["bar_close"]) - float(signal["bar_open"])) / float(signal["bar_open"])
        row["delta_imbalance"] = float(signal.get("delta", 0.0)) / max(float(signal.get("volume", 1.0)), 1e-12)
        rows.append(row)
    dimensions = ["year", "month", "session", "volatility_regime", "volume_regime", "trend_regime", "side", "signal_strength_bin", "divergence_score_bin", "bar_duration_bin", "bar_return_bin", "delta_imbalance_bin"]
    for row in rows:
        row["signal_strength_bin"] = _quantile_bucket(float(row.get("signal_strength", 0.0)), (0.33, 0.66))
        row["divergence_score_bin"] = _quantile_bucket(float(row.get("divergence_score", 0.0)), (0.33, 0.66))
        row["bar_duration_bin"] = _quantile_bucket(float(row["bar_duration"]), (0.33, 0.66))
        row["bar_return_bin"] = _quantile_bucket(float(row["bar_return"]), (0.33, 0.66))
        row["delta_imbalance_bin"] = _quantile_bucket(float(row["delta_imbalance"]), (0.33, 0.66))
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for key in dimensions:
            buckets[f"{key}={row.get(key)}"].append(row)
    reports = {}
    robust = []
    for bucket, bucket_rows in sorted(buckets.items()):
        if len(bucket_rows) < 1:
            continue
        summary = summarize_trades(bucket_rows)
        years = {row["year"] for row in bucket_rows}
        payload = {
            "bucket": bucket,
            "count": len(bucket_rows),
            "gross_expectancy": summary["gross_pnl"] / summary["trade_count"] if summary["trade_count"] else 0.0,
            "net_expectancy": summary["expectancy_per_trade"],
            "profit_factor": summary["profit_factor"],
            "win_rate": summary["win_rate"],
            "avg_mfe": mean(float(row["max_favorable_excursion_pct"]) for row in bucket_rows),
            "avg_mae": mean(float(row["max_adverse_excursion_pct"]) for row in bucket_rows),
            "mfe_capture_potential": mean(float(row["max_favorable_excursion_pct"]) - float(row["return_at_bar_exit"].get("24") or 0.0) for row in bucket_rows),
            "cost_drag": summary["gross_pnl"] - summary["net_pnl"],
            "years": sorted(years),
        }
        reports[bucket] = payload
        if payload["count"] >= 300 and payload["net_expectancy"] > 0 and payload["profit_factor"] > 1.05 and len(years) >= 3:
            robust.append(payload)
    return {"buckets": reports, "robust_buckets": robust}


def _session_label(ts_ns: int) -> str:
    hour = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).hour
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 18:
        return "ny"
    return "overnight"


def _quantile_bucket(value: float, cutpoints: tuple[float, float]) -> str:
    low, high = cutpoints
    if value <= low:
        return "low"
    if value <= high:
        return "mid"
    return "high"

