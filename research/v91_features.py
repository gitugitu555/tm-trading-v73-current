"""Extended feature ledger for V9.1 alpha discovery."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from research.v89_volume_bar_builder import load_verified_catalog


def build_extended_feature_ledger(catalog_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    bars = load_verified_catalog(catalog_path)
    frame = pd.DataFrame([asdict(bar) for bar in bars])
    close = frame["close"].astype(float)
    open_ = frame["open"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float)
    delta = frame["delta"].astype(float)
    cvd = frame["cumulative_delta"].astype(float)
    ret = close.pct_change().fillna(0.0)
    rng = (high - low).replace(0, np.nan)

    frame["return"] = ret
    frame["bar_return"] = ret
    frame["range_pct"] = ((high - low) / close.replace(0, np.nan)).fillna(0.0)
    frame["close_location_in_range"] = ((_safe_div(close - low, high - low))).fillna(0.0)
    frame["body_to_range_ratio"] = (_safe_div((close - open_).abs(), high - low)).fillna(0.0)
    frame["upper_wick_ratio"] = (_safe_div(high - np.maximum(open_, close), high - low)).fillna(0.0)
    frame["lower_wick_ratio"] = (_safe_div(np.minimum(open_, close) - low, high - low)).fillna(0.0)
    frame["delta"] = delta
    frame["cvd"] = cvd
    frame["delta_zscore_20"] = _zscore(delta, 20)
    frame["delta_zscore_50"] = _zscore(delta, 50)
    frame["delta_zscore_100"] = _zscore(delta, 100)
    frame["cvd_slope_3"] = cvd.diff(3).fillna(0.0)
    frame["cvd_slope_5"] = cvd.diff(5).fillna(0.0)
    frame["cvd_slope_10"] = cvd.diff(10).fillna(0.0)
    frame["cvd_accel_3_10"] = frame["cvd_slope_3"] - frame["cvd_slope_10"]
    frame["delta_volume_ratio"] = _safe_div(delta, volume).fillna(0.0)
    frame["signed_volume_ratio"] = _safe_div(delta.abs(), volume).fillna(0.0)
    frame["aggressive_buy_ratio"] = _safe_div(frame["buy_volume"].astype(float), volume).fillna(0.0)
    frame["aggressive_sell_ratio"] = _safe_div(frame["sell_volume"].astype(float), volume).fillna(0.0)
    frame["return_zscore_20"] = _zscore(ret, 20)
    frame["return_zscore_50"] = _zscore(ret, 50)
    frame["realized_vol_20"] = ret.rolling(20, min_periods=5).std().fillna(0.0)
    frame["realized_vol_50"] = ret.rolling(50, min_periods=10).std().fillna(0.0)
    frame["positive_delta_negative_return"] = ((delta > 0) & (ret < 0)).astype(int)
    frame["negative_delta_positive_return"] = ((delta < 0) & (ret > 0)).astype(int)
    frame["large_delta_small_return"] = ((frame["delta_zscore_20"].abs() > 1.5) & (ret.abs() < frame["realized_vol_20"])).astype(int)
    frame["delta_zscore_minus_return_zscore"] = frame["delta_zscore_20"] - frame["return_zscore_20"]
    frame["absorption_score"] = (
        frame["positive_delta_negative_return"]
        + frame["negative_delta_positive_return"]
        + frame["positive_delta_negative_return"] * frame["delta_zscore_20"].abs()
        + frame["negative_delta_positive_return"] * frame["delta_zscore_20"].abs()
        + frame["large_delta_small_return"]
    )
    frame["failed_buy_impulse_score"] = (
        (frame["delta_zscore_20"] > 1.5).astype(float)
        * (1.0 - frame["close_location_in_range"])
        * (frame["bar_return"] <= frame["bar_return"].rolling(5, min_periods=1).median().fillna(0.0)).astype(float)
    )
    frame["failed_sell_impulse_score"] = (
        (frame["delta_zscore_20"] < -1.5).astype(float)
        * frame["close_location_in_range"]
        * (frame["bar_return"] >= frame["bar_return"].rolling(5, min_periods=1).median().fillna(0.0)).astype(float)
    )
    frame["cvd_price_disagreement"] = ((np.sign(frame["cvd_slope_5"]) != np.sign(ret)).astype(int))
    prev_high_20 = close.shift(1).rolling(20, min_periods=5).max().fillna(close)
    prev_high_50 = close.shift(1).rolling(50, min_periods=10).max().fillna(close)
    prev_low_20 = close.shift(1).rolling(20, min_periods=5).min().fillna(close)
    prev_low_50 = close.shift(1).rolling(50, min_periods=10).min().fillna(close)
    frame["price_breakout_20"] = (close > prev_high_20).astype(int)
    frame["price_breakout_50"] = (close > prev_high_50).astype(int)
    frame["cvd_breakout_20"] = (cvd > cvd.shift(1).rolling(20, min_periods=5).max().fillna(cvd)).astype(int)
    frame["cvd_breakout_50"] = (cvd > cvd.shift(1).rolling(50, min_periods=10).max().fillna(cvd)).astype(int)
    frame["price_cvd_alignment"] = (np.sign(ret) == np.sign(frame["cvd_slope_5"])).astype(int)
    frame["price_cvd_alignment_strength"] = frame["price_cvd_alignment"] * (ret.abs() + frame["cvd_slope_5"].abs() / (cvd.abs().rolling(50, min_periods=10).mean().replace(0, np.nan) + 1e-12)).fillna(0.0)
    frame["pullback_after_cvd_impulse"] = ((frame["cvd_slope_5"].abs() > frame["cvd_slope_5"].rolling(20, min_periods=5).median().abs().fillna(0.0)) & (ret.abs() < frame["return"].rolling(5, min_periods=1).median().abs().fillna(0.0))).astype(int)
    frame["continuation_setup_score"] = (
        frame["price_cvd_alignment_strength"]
        + frame["pullback_after_cvd_impulse"]
        + frame["price_breakout_20"]
        + frame["cvd_breakout_20"]
    )
    timestamps = pd.to_datetime(frame["end_ts_ns"], utc=True)
    frame["trend_slope_50"] = close.rolling(50, min_periods=10).apply(_slope, raw=True).fillna(0.0)
    frame["trend_slope_100"] = close.rolling(100, min_periods=20).apply(_slope, raw=True).fillna(0.0)
    frame["trend_strength"] = frame["trend_slope_50"].abs() / (frame["realized_vol_50"] + 1e-12)
    frame["volatility_regime"] = _regime_bucket(frame["realized_vol_50"], (0.33, 0.66))
    frame["volume_regime"] = _regime_bucket(frame["volume"], (0.33, 0.66))
    frame["bar_duration_regime"] = _regime_bucket((frame["end_ts_ns"] - frame["start_ts_ns"]).astype(float), (0.33, 0.66))
    frame["session_label"] = timestamps.dt.hour.map(_session_label)
    frame["year"] = timestamps.dt.year.astype(str)
    frame["month"] = timestamps.dt.strftime("%Y-%m")
    frame["day"] = timestamps.dt.strftime("%Y-%m-%d")
    frame["weekday"] = timestamps.dt.dayofweek.astype(int)
    frame["hour_utc"] = timestamps.dt.hour.astype(int)
    frame["weekend_flag"] = timestamps.dt.dayofweek.isin([5, 6]).astype(int)
    frame["old_divergence_score"] = frame["delta_zscore_20"] - frame["return_zscore_20"]
    frame["old_divergence_signal"] = np.sign(frame["old_divergence_score"]).astype(int)
    frame["old_signal_strength"] = frame["old_divergence_score"].abs()
    frame["old_signal_side"] = frame["old_divergence_signal"]
    frame["old_policy_expected_value_if_available"] = 0.0

    manifest = {
        "catalog_path": str(catalog_path),
        "row_count": len(frame),
        "feature_count": len(frame.columns),
        "feature_hash": _hash_frame(frame),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return frame, manifest


def write_extended_feature_ledger(frame: pd.DataFrame, manifest: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(frame), output_dir / "feature_ledger.parquet", compression="zstd")
    (output_dir / "feature_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _safe_div(a: Any, b: Any) -> pd.Series:
    return pd.Series(a) / pd.Series(b).replace(0, np.nan)


def _zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window, min_periods=max(3, window // 5)).mean()
    std = series.rolling(window, min_periods=max(3, window // 5)).std().replace(0, np.nan)
    return ((series - mean) / std).fillna(0.0)


def _slope(values: Any) -> float:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    x_mean = float(x.mean())
    y_mean = float(values.mean())
    denom = float(((x - x_mean) ** 2).sum())
    return float(((x - x_mean) * (values - y_mean)).sum() / denom) if denom else 0.0


def _regime_bucket(series: pd.Series, cutpoints: tuple[float, float]) -> pd.Series:
    low, high = series.quantile(cutpoints[0]), series.quantile(cutpoints[1])
    out = pd.Series(index=series.index, dtype="object")
    out[series <= low] = "low"
    out[(series > low) & (series <= high)] = "mid"
    out[series > high] = "high"
    return out.fillna("mid")


def _session_label(hour: int) -> str:
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 18:
        return "ny"
    return "overnight"


def _hash_frame(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update(frame.to_json(orient="records", date_unit="ns").encode("utf-8"))
    return digest.hexdigest()
