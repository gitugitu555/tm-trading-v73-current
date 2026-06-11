"""Feature ledger construction on the verified six-year catalog."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from research.v89_volume_bar_builder import load_verified_catalog


def build_feature_ledger(catalog_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    bars = load_verified_catalog(catalog_path)
    rows = [asdict(bar) for bar in bars]
    frame = pd.DataFrame(rows)
    frame["return"] = frame["close"].pct_change().fillna(0.0)
    frame["duration_ns"] = frame["end_ts_ns"] - frame["start_ts_ns"]
    frame["cvd"] = frame["cumulative_delta"]
    frame["cvd_slope"] = frame["cvd"].diff().fillna(0.0)
    frame["cvd_accel"] = frame["cvd_slope"].diff().fillna(0.0)
    frame["rolling_cvd_z"] = _zscore(frame["cvd"].rolling(50, min_periods=10).mean())
    frame["rolling_delta_z"] = _zscore(frame["delta"].rolling(50, min_periods=10).mean())
    frame["rolling_volatility"] = frame["return"].rolling(50, min_periods=10).std().fillna(0.0)
    frame["rolling_volume_z"] = _zscore(frame["volume"].rolling(50, min_periods=10).mean())
    frame["trend_slope"] = frame["close"].rolling(20, min_periods=5).apply(_slope, raw=True).fillna(0.0)
    frame["vwap_distance"] = _rolling_vwap_distance(frame)
    frame["range_expansion"] = (frame["high"] - frame["low"]) / frame["close"].replace(0, pd.NA)
    frame["absorption_proxy"] = (frame["volume"] - frame["delta"].abs()).fillna(0.0)
    frame["failed_impulse_proxy"] = frame["range_expansion"].fillna(0.0) - frame["return"].abs()
    frame["divergence_score"] = frame["cvd_slope"] - frame["return"]
    frame["signal_strength"] = frame["divergence_score"].abs()
    timestamps = pd.to_datetime(frame["end_ts_ns"], utc=True)
    frame["session_label"] = timestamps.dt.hour.map(_session_label)
    frame["year"] = timestamps.dt.year.astype(str)
    frame["month"] = timestamps.dt.strftime("%Y-%m")
    frame["day"] = timestamps.dt.strftime("%Y-%m-%d")
    frame["hour"] = timestamps.dt.hour.astype(int)
    manifest = {
        "catalog_path": str(catalog_path),
        "catalog_hash": _hash_frame(frame),
        "feature_count": len(frame.columns),
        "row_count": len(frame),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return frame, manifest


def write_feature_ledger(frame: pd.DataFrame, manifest: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(frame), output_dir / "feature_ledger.parquet", compression="zstd")
    (output_dir / "feature_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _hash_frame(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update(frame.to_json(orient="records", date_unit="ns").encode("utf-8"))
    return digest.hexdigest()


def _rolling_vwap_distance(frame: pd.DataFrame) -> pd.Series:
    cum_pv = (frame["close"] * frame["volume"]).cumsum()
    cum_vol = frame["volume"].cumsum().replace(0, pd.NA)
    return (frame["close"] - cum_pv / cum_vol).fillna(0.0)


def _slope(values: Any) -> float:
    values = list(values)
    if len(values) < 2:
        return 0.0
    x = list(range(len(values)))
    x_mean = sum(x) / len(x)
    y_mean = sum(values) / len(values)
    denom = sum((value - x_mean) ** 2 for value in x)
    return sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(len(values))) / denom if denom else 0.0


def _zscore(series: pd.Series) -> pd.Series:
    mean = series.expanding(min_periods=10).mean()
    std = series.expanding(min_periods=10).std().replace(0, pd.NA)
    return ((series - mean) / std).fillna(0.0)


def _session_label(hour: int) -> str:
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 18:
        return "ny"
    return "overnight"
